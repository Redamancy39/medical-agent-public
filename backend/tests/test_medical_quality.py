from copy import deepcopy
import pytest
from app.medical_quality import (context, anchor, review_reference_points, answer_template,
    review_answers, claim_spans)


def reference():
    cases, catalog, _, expected = context()
    case = cases['basic-03']
    return {**expected, 'items': [{'case_id': case['id'], 'point_index': 1,
        'text': case['reference_points'][1], 'kind': 'medical_fact', 'support_status': 'supported',
        'evidence': [anchor('nlm-bp-medicines', 'This allows the blood vessels to relax.', catalog)],
        'note': '全文有支持，但原绑定片段没有此句。', 'professional_review': 'pending'}]}


def report():
    return {'rows': [{'case_id': 'basic-03', 'result': {'run_id': 'synthetic',
        'answer': '合成测试：数值6.5%不是切句位置。', 'result_status': 'completed', 'sources': []}}]}


def test_real_quote_gap_not_medical_contradiction():
    output = review_reference_points(reference())
    first = output['items'][0]
    assert first['support_status'] == 'supported' and first['citation_status'] == 'citation_gap'
    assert output['summary']['items'] == 60 and output['summary']['support_status_counts']['pending'] == 59
    assert output['summary']['clinical_accuracy'] is None


def test_fake_anchor_or_fake_professional_review_rejected():
    bundle = reference()
    bundle['items'][0]['evidence'][0]['quote'] = 'forged'
    with pytest.raises(ValueError, match='ANCHOR_INVALID'): review_reference_points(bundle)
    bundle = reference(); bundle['items'][0]['professional_review'] = 'passed'
    with pytest.raises(ValueError, match='PROFESSIONAL_REVIEW'): review_reference_points(bundle)


def test_stale_baseline_and_test_case_rejected():
    bundle = reference(); bundle['corpus_sha256'] = 'stale'
    with pytest.raises(ValueError, match='BASELINE_CHANGED'): review_reference_points(bundle)
    bundle = reference(); bundle['items'][0]['case_id'] = 'basic-02'
    with pytest.raises(ValueError, match='DEV_ONLY'): review_reference_points(bundle)


def test_unreviewed_answers_stay_pending_and_decimals_preserved():
    raw = report(); template = answer_template(raw)
    assert len(claim_spans(raw['rows'][0]['result']['answer'])) == 1
    output = review_answers(raw, template)
    assert output['summary']['support_status_counts'] == {'pending': 1}
    assert output['summary']['supported_fraction_among_reviewed_medical_items'] is None
    assert output['summary']['unobserved_dev_cases'] == 19


@pytest.mark.parametrize('mutation,error', [('text', 'SPAN_INVALID'), ('gap', 'REVIEW_GAP'),
    ('overlap', 'CLAIM_OVERLAP'), ('answer', 'ANSWER_CHANGED')])
def test_claim_coverage_is_bound_to_the_actual_answer(mutation, error):
    raw = report(); bundle = answer_template(raw)
    if mutation == 'text': bundle['rows'][0]['claims'][0]['text'] = 'replacement'
    if mutation == 'gap': bundle['rows'][0]['claims'] = []
    if mutation == 'overlap': bundle['rows'][0]['claims'] *= 2
    if mutation == 'answer': raw['rows'][0]['result']['answer'] += 'changed'
    with pytest.raises(ValueError, match=error): review_answers(raw, bundle)


def test_policy_cannot_be_used_as_medical_evidence():
    bundle = reference(); item = bundle['items'][0]
    item['evidence'] = []; item['policy_rules'] = ['urgent']
    with pytest.raises(ValueError, match='MEDICAL_EVIDENCE_REQUIRED'): review_reference_points(bundle)


def test_forged_cited_source_content_is_rejected():
    from app.medical_corpus import load_documents
    d = load_documents()[0]; section = d['sections'][0]
    raw = report()
    raw['rows'][0]['result']['sources'] = [{'id': 'synthetic-source', 'document_id': d['id'],
        'version': d['version'], 'source_sha256': d['source_sha256'], 'start': section['start'],
        'end': section['end'], 'content': 'forged', 'source_spans': section['source_spans']}]
    with pytest.raises(ValueError, match='CITED_SOURCE_CONTENT_INVALID'):
        review_answers(raw, answer_template(raw))
