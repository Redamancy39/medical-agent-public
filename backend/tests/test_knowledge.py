import pytest

from app.knowledge import KnowledgeStore, HashEmbedding, split_text


def test_split_reaches_end_without_repeating_tail():
    text = 'abcdefghijklmnopqrstuvwxyz' * 70
    chunks = split_text(text, size=300, overlap=50)
    assert len(chunks) == 8
    assert chunks[-1]['end'] == len(text)
    assert all(c['text'] == text[c['start']:c['end']] for c in chunks)
    assert ''.join(c['text'] if i == 0 else c['text'][50:] for i, c in enumerate(chunks)) == text


@pytest.mark.parametrize('size,overlap', [(0, 0), (10, 10), (10, -1), (10, 11)])
def test_invalid_split_bounds(size, overlap):
    with pytest.raises(ValueError):
        split_text('x', size, overlap)


def test_import_search_no_match_versions_and_restart(tmp_path):
    path = tmp_path / 'owned-kb.db'
    document = {'id': 'synthetic-sop', 'version': '1', 'title': '合成登记', 'url': 'local://synthetic/sop',
                'text': '合成样本登记需要编辑草稿并明确确认，不确认不能写入。', 'synthetic': True}
    kb = KnowledgeStore(path, HashEmbedding())
    try:
        first = kb.import_documents([document])
        second = kb.import_documents([document])
        assert first['chunk_ids'] == second['chunk_ids']
        assert kb.count() == 1
        results = kb.search('样本登记确认', 3)
        assert results and results[0]['score_kind'] == 'cosine_similarity'
        assert results[0]['document_id'] == document['id'] and results[0]['verified'] is False
        assert kb.search('ZZZZZZZZZZ', 3, threshold=0.99) == []
        kb.import_documents([{**document, 'version': '2', 'text': '新版合成样本登记规则。'}])
        assert kb.count() == 1 and kb.search('样本登记', 1)[0]['version'] == '2'
    finally:
        kb.close()
    with KnowledgeStore(path, HashEmbedding()) as restarted:
        assert restarted.count() == 1 and restarted.search('样本登记', 1)


def test_existing_released_collection_is_loaded_after_reopen(tmp_path):
    path = tmp_path / 'released.db'
    with KnowledgeStore(path, HashEmbedding()) as first:
        first.import_documents([{'id': 'sop', 'version': '1', 'title': '登记', 'url': 'local://sop',
                                 'text': '样本登记确认流程', 'synthetic': True}])
        first.client.release_collection(first.collection)
    with KnowledgeStore(path, HashEmbedding()) as restarted:
        assert restarted.search('样本登记', 1)


def test_reference_database_path_is_rejected_before_opening():
    from pathlib import Path
    target = Path(__file__).resolve().parents[2] / 'medix-agent-swarm/knowledge/data/milvus_lite.db'
    with pytest.raises(ValueError, match='参考'):
        KnowledgeStore(target, HashEmbedding())
