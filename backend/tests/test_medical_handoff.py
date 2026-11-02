from copy import deepcopy
import hashlib

import pytest
from pydantic import ValidationError
from app.medical_evaluation import DATASET_ROOT
from app.medical_handoff import stage_handoff


def payload():
    return {'schema_version': 'medical-handoff-v1', 'batch_id': 'dev-round-1', 'created_at': '2026-10-14T09:00:00+08:00',
        'sources': [], 'audits': [{'case_id': 'basic-01', 'reference_point': '收缩压定义',
            'issue_type': 'citation_gap', 'support_status': 'supported',
            'evidence': [{'url': 'https://medlineplus.gov/highbloodpressure.html', 'locator': 'Summary',
                'quote': 'This is called systolic pressure.', 'access_status': 'opened'}],
            'suggested_change': '补原文支持位置'}]}


def test_valid_proposal_is_staged_not_applied_and_deduplicated(tmp_path):
    before = {n: hashlib.sha256((DATASET_ROOT / n).read_bytes()).hexdigest() for n in ('dev.jsonl', 'test.jsonl', 'manifest.json')}
    first = stage_handoff(payload(), tmp_path)
    assert first['replayed'] is False and first['dataset_update'] == 'not_applied'
    assert stage_handoff(payload(), tmp_path)['replayed'] is True
    changed = payload(); changed['audits'][0]['suggested_change'] = '改为新建议'
    with pytest.raises(ValueError, match='BATCH_ID_CONTENT_CHANGED'): stage_handoff(changed, tmp_path)
    assert all(hashlib.sha256((DATASET_ROOT / n).read_bytes()).hexdigest() == h for n, h in before.items())


@pytest.mark.parametrize('mutation,error', [('no_evidence', 'POINT_EVIDENCE_REQUIRED'),
    ('test_case', 'TEST_AUDIT_PAUSED'), ('unknown_case', 'UNKNOWN_CASE_ID'),
    ('naive_time', 'TIMEZONE_REQUIRED'), ('bad_url', 'PUBLIC_HTTPS_URL_REQUIRED')])
def test_invalid_or_out_of_scope_handoff_is_rejected(tmp_path, mutation, error):
    p = payload()
    if mutation == 'no_evidence': p['audits'][0]['evidence'] = []
    if mutation == 'test_case': p['audits'][0]['case_id'] = 'basic-02'
    if mutation == 'unknown_case': p['audits'][0]['case_id'] = 'invented-99'
    if mutation == 'naive_time': p['created_at'] = '2026-10-14T09:00:00'
    if mutation == 'bad_url': p['audits'][0]['evidence'][0]['url'] = 'https://secret@medlineplus.gov/highbloodpressure.html'
    with pytest.raises((ValueError, ValidationError), match=error): stage_handoff(p, tmp_path)
    assert not list(tmp_path.glob('*.json'))


def test_same_source_in_new_batch_is_not_counted_as_new(tmp_path):
    p = {'schema_version': 'medical-handoff-v1', 'batch_id': 'sources-one', 'created_at': '2026-10-14T09:00:00+08:00',
        'sources': [{'id': 'nlm-bp', 'title': '血压来源', 'url': 'https://medlineplus.gov/highbloodpressure.html',
                     'access_status': 'opened', 'notes': 'Dot报告，待本地核查'}], 'audits': []}
    assert stage_handoff(p, tmp_path)['new_source_candidates'] == 1
    p['batch_id'] = 'sources-two'
    assert stage_handoff(p, tmp_path)['unchanged_source_candidates'] == 1
    p['batch_id'] = 'sources-three'
    p['sources'][0]['notes'] = '新增复用条件待核查备注'
    result = stage_handoff(p, tmp_path)
    assert result['new_source_candidates'] == 0 and result['updated_source_candidates'] == 1
