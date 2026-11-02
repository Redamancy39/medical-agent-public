import hashlib
import json

import pytest

from app.medical_ingestion import TxtIngestion, IngestionError, read_txt, section_blocks, candidate_documents
from app.knowledge import HashEmbedding, KnowledgeStore
from app.agent import Source


def test_txt_keeps_raw_hash_and_explicit_normalized_offsets(tmp_path):
    raw = '高血压\r\n\r\n一、检查条件\r\n- 不可自行停药；≥140 mmHg须结合条件。\r\n'.encode('utf-8-sig')
    path = tmp_path / 'input.txt'
    path.write_bytes(raw)
    parsed = read_txt(path)
    assert parsed['raw_source_sha256'] == hashlib.sha256(raw).hexdigest()
    assert parsed['encoding'] == 'utf-8-sig' and '\r' not in parsed['text']
    blocks = section_blocks(parsed['text'])
    assert '不可自行停药；≥140 mmHg' in ''.join(b['text'] for b in blocks)
    assert all(b['text'] == parsed['text'][b['start']:b['end']] for b in blocks)
    assert path.read_bytes() == raw


def test_gb18030_strict_decode_and_corrupt_text_fails(tmp_path):
    path = tmp_path / 'input.txt'
    path.write_bytes('血糖单位 mmol/L，未确诊。'.encode('gb18030'))
    assert read_txt(path)['encoding'] == 'gb18030'
    path.write_bytes(b'\xff')
    with pytest.raises(IngestionError, match='TEXT_DECODE_FAILED'): read_txt(path)
    path.write_bytes(b'text\x00corrupt')
    with pytest.raises(IngestionError, match='TEXT_CONTROL_CHARACTERS'): read_txt(path)


def test_long_atomic_paragraph_is_not_silently_cut():
    with pytest.raises(IngestionError, match='ATOMIC_BLOCK_TOO_LONG'):
        section_blocks('条件和数值不可拆开' * 150)


def test_staging_dedup_versions_and_pending_admission(tmp_path):
    source = tmp_path / 'source.txt'
    source.write_text('知识说明\n\n一、条件\n\n只提供一般知识，不可自行调整药量。', encoding='utf-8')
    intake = TxtIngestion(tmp_path / 'intake')
    first = intake.stage([source])
    assert first['summary']['documents'] == 1 and first['summary']['admitted'] == 0
    assert first['records'][0]['admission_status'] == 'pending_source_review'
    assert first['records'][0]['stages'][-1]['stage'] == 'source_admission'
    second = intake.stage([source])
    assert second['summary']['unchanged'] == 1
    assert second['records'][0]['document']['version'] == first['records'][0]['document']['version']
    original_snapshot = first['records'][0]['raw_snapshot']
    source.write_text('知识说明\n\n一、条件\n\n新版本仍需核对出处。', encoding='utf-8')
    third = intake.stage([source])
    assert third['records'][0]['document']['version'] != first['records'][0]['document']['version']
    assert (tmp_path / 'intake' / original_snapshot).is_file()
    assert candidate_documents(third)[0]['provenance_status'] == 'pending_source_review'
    assert json.loads((tmp_path / 'intake/manifest.json').read_text(encoding='utf-8'))['records']


def test_same_bytes_in_one_batch_are_not_independent_documents(tmp_path):
    a, b = tmp_path / 'a.txt', tmp_path / 'b.txt'
    a.write_text('来源不明的同一份医学文本。', encoding='utf-8')
    b.write_bytes(a.read_bytes())
    result = TxtIngestion(tmp_path / 'intake').stage([a, b])
    assert result['summary']['documents'] == 1 and result['summary']['duplicates'] == 1


def test_newline_variants_are_one_source_family(tmp_path):
    a, b = tmp_path / 'a.txt', tmp_path / 'b.txt'
    a.write_bytes('医学资料\r\n\r\n不可自行确诊。'.encode('utf-8'))
    b.write_bytes('医学资料\n\n不可自行确诊。'.encode('utf-8-sig'))
    result = TxtIngestion(tmp_path / 'intake').stage([a, b])
    assert result['summary']['documents'] == 1 and result['summary']['duplicates'] == 1


def test_corrupt_file_is_reported_without_losing_good_file(tmp_path):
    good, bad = tmp_path / 'good.txt', tmp_path / 'bad.txt'
    good.write_text('健康知识来源仍需核对。', encoding='utf-8')
    bad.write_bytes(b'\xff')
    result = TxtIngestion(tmp_path / 'intake').stage([bad, good])
    assert result['summary']['failed'] == 1 and result['summary']['documents'] == 1
    assert result['records'][0]['safe_error_code'] == 'TEXT_DECODE_FAILED'


def test_candidate_index_keeps_exact_quotes_and_uncertainty(tmp_path):
    path = tmp_path / 'source.txt'
    path.write_text('检查说明\n\n一、单位\n\n确认单位和空腹状态，不得凭一次数字确诊。', encoding='utf-8')
    staged = TxtIngestion(tmp_path / 'intake').stage([path])
    docs = candidate_documents(staged)
    with KnowledgeStore(tmp_path / 'candidate.db', HashEmbedding()) as store:
        ids = store.import_documents(docs)['chunk_ids']
        original_embed = store.embedding.embed
        store.embedding.embed = lambda _: (_ for _ in ()).throw(AssertionError('must skip unchanged embedding'))
        skipped = store.import_documents(docs, skip_unchanged=True)
        assert skipped['chunk_ids'] == ids and skipped['skipped_documents'] == 1
        store.embedding.embed = original_embed
        changed_metadata = [{**docs[0], 'attribution': '出处核对备注更新；仍为候选'}]
        assert store.import_documents(changed_metadata, skip_unchanged=True)['skipped_documents'] == 0
        hits = store.search('单位空腹状态', 5, threshold=-1)
        for hit in hits:
            Source.model_validate(hit)
            assert hit['verified'] is False and hit['content_kind'] == 'medical_candidate_excerpt'
            assert hit['raw_source_sha256'] and hit['offset_basis'] == 'decoded_text_lf_unicode'
            assert hit['content'] == docs[0]['text'][hit['start']:hit['end']]
            assert hit['source_spans'][0]['quote'] == hit['content']
