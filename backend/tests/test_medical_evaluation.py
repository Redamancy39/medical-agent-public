import hashlib
import json
import shutil

import pytest

from app.medical_evaluation import DATASET_ROOT, validate_dataset, retrieval_score


def test_frozen_dataset_and_exact_support():
    cases = validate_dataset()
    assert len(cases) == 60
    case = next(c for c in cases if c['id'] == 'basic-01')
    gold = case['gold_evidence'][0]
    hit = {'document_id': gold['document_id'], 'version': gold['document_version'],
        'source_sha256': gold['source_sha256'], 'start': gold['editorial_start'],
        'end': gold['editorial_end'], 'source_spans': gold['source_spans']}
    assert retrieval_score(case, [hit])['hit_at_5'] == 1
    assert retrieval_score(case, [{**hit, 'source_spans': []}])['hit_at_5'] == 0
    assert retrieval_score(case, [{**hit, 'end': 1}])['hit_at_5'] == 0
    unknown = next(c for c in cases if not c['gold_evidence'])
    assert retrieval_score(unknown, [])['hit_at_5'] is None


@pytest.mark.parametrize('mutation,error', [
    ('hash', 'DATASET_FILE_CHANGED'), ('span', 'DATASET_GOLD_SPAN'),
    ('version', 'DATASET_GOLD_VERSION'), ('family', 'DATASET_FAMILY_LEAKAGE'),
    ('override', 'DATASET_ROUTING_OVERRIDE'), ('count', 'DATASET_SPLIT_COUNT'),
])
def test_tampered_dataset_rejected(tmp_path, mutation, error):
    root = tmp_path / 'dataset'
    root.mkdir()
    for name in ('manifest.json', 'policy.json', 'dev.jsonl', 'test.jsonl'):
        shutil.copyfile(DATASET_ROOT / name, root / name)
    path = root / 'test.jsonl'
    rows = [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines()]
    if mutation == 'hash': rows[0]['question'] += 'tampered'
    if mutation == 'span': rows[0]['gold_evidence'][0]['source_spans'][0]['start'] += 1
    if mutation == 'version': rows[0]['gold_evidence'][0]['document_version'] = 'fake'
    if mutation == 'family': rows[0]['family_id'] = 'basic-01'
    if mutation == 'override': rows[0]['force_topology'] = True
    if mutation == 'count': rows.pop()
    path.write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n', encoding='utf-8')
    if mutation != 'hash':
        manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
        manifest['files_sha256']['test.jsonl'] = hashlib.sha256(path.read_bytes()).hexdigest()
        (root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError, match=error): validate_dataset(root)
