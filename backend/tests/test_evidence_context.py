"""Regression: authors must see the original context that the reviewer can verify."""
from copy import deepcopy
import hashlib

import pytest


def fixture():
    raw = ('What is it?\n\nAverage over months.\n\nWhat is it used for?\n\n'
        'Home monitoring measures glucose at that time.\n\n'
        'This test is also used for monitoring.\n\nOther topic?\n\nUnrelated details.')
    quote = 'also used for monitoring'
    start = raw.index(quote)
    sha = hashlib.sha256(raw.encode()).hexdigest()
    original = {'raw': raw, 'source_sha256': sha, 'editorial_version': 'v1', 'editorial_text': '编辑摘述'}
    document = {'id': 'chunk1', 'document_id': 'nlm-example', 'version': 'v1', 'source_sha256': sha,
        'content': '编辑摘述', 'start': 0, 'end': 4,
        'source_spans': [{'start': start, 'end': start+len(quote), 'quote': quote}]}
    return document, original


def test_section_intro_is_available_without_loading_unrelated_sections_or_mutating_source():
    from app.evidence_context import expand_medical_evidence
    document, original = fixture()
    before = deepcopy(document)
    result = expand_medical_evidence([document], catalog={'nlm-example': original})[0]
    quotes = [s['quote'] for s in result['source_spans']]
    assert 'Home monitoring measures glucose at that time.' in quotes
    assert not any('Unrelated details.' in q for q in quotes)
    assert document == before and result['content'] == document['content']
    assert len(result['source_spans']) <= 10
    for span in result['source_spans']:
        assert original['raw'][span['start']:span['end']] == span['quote']


def test_untrusted_hash_or_invalid_original_anchor_is_not_expanded():
    from app.evidence_context import expand_medical_evidence
    document, original = fixture()
    with pytest.raises(ValueError):
        expand_medical_evidence([{**document, 'source_sha256': 'wrong'}], catalog={'nlm-example': original})
    document['source_spans'][0]['quote'] = 'invented'
    with pytest.raises(ValueError):
        expand_medical_evidence([document], catalog={'nlm-example': original})


def test_source_projection_avoids_repeating_short_quotes_already_inside_full_paragraph():
    from app.prompt_context import document_context
    doc = {'id': 'one', 'content': '编辑', 'source_spans': [
        {'start': 7, 'end': 11, 'quote': 'text'},
        {'start': 0, 'end': 16, 'quote': 'Longer text here'}]}
    assert document_context(doc)['source_spans'] == [doc['source_spans'][1]]


def test_empty_evidence_based_rewrite_is_valid_but_initial_atomization_cannot_be_empty():
    from app.medical_reviewer import build_packet, validate_atoms
    from pydantic import ValidationError
    packet = build_packet('问题', '没有依据的范围声明。', [])
    assert not validate_atoms({'claims': []}, packet, complete=False).claims
    with pytest.raises(ValidationError):
        validate_atoms({}, packet, complete=False)
    with pytest.raises(ValidationError):
        validate_atoms({'claims': []}, packet)


def test_lead_receives_exact_original_context_as_well_as_editorial_text():
    from app.providers import DeepSeekModel
    document, original = fixture()
    from app.evidence_context import expand_medical_evidence
    document = expand_medical_evidence([document], catalog={'nlm-example': original})[0]
    model = object.__new__(DeepSeekModel)
    captured = {}
    def capture(*args):
        captured.update(payload=args[-2])
    model._structured = capture
    model.synthesize({'question': '不超过180字', 'context': {'memories': []}, 'task_results': [
        {'task_id': 'research', 'agent_id': 'research_agent', 'answer': '资料未说明时间尺度。', 'sources': [document]}]})
    payload = captured['payload']
    assert payload['answer_target_chars'] < payload['answer_max_chars'] == 180
    assert any(s['quote'] == 'Home monitoring measures glucose at that time.'
        for s in payload['sources'][0]['source_spans'])


def test_compaction_cannot_reclassify_preserved_medical_facts_as_editorial():
    from app.medical_reviewer import build_packet, validate_review
    from app.contracts import ContractViolation
    packet = build_packet('问题', '精简表述。', [])
    packet['claims'][0]['preserved_facts'] = [{'index': 0, 'text': '原已核对的医学事实。', 'kind': 'medical_fact'}]
    with pytest.raises(ContractViolation, match='FACT_CLASSIFICATION'):
        validate_review({'claims': [{'index': 0, 'kind': 'editorial', 'support_status': 'supported',
            'evidence_ids': [], 'policy_rules': [], 'note': '试图绕过证据审核'}]}, packet)


def test_compaction_length_failure_reports_actual_total_without_exposing_prose():
    from app.medical_reviewer import build_packet, validate_compaction, ReviewSubmission
    from app.contracts import ContractViolation
    packet = build_packet('最多5字', '事实一。事实二。', [])
    first = ReviewSubmission(claims=[{'index': i, 'kind': 'editorial', 'support_status': 'supported',
        'note': '合成结构测试'} for i in range(2)])
    with pytest.raises(ContractViolation) as caught:
        validate_compaction({'claims': [{'text': '事实一。事实二。', 'draft_indices': [0, 1]}]}, packet, first)
    assert caught.value.counts == {'max_chars': 5, 'actual_chars': 8}


def test_compaction_provider_receives_headroom_and_per_claim_limit():
    from app.providers import DeepSeekModel
    from app.medical_reviewer import build_packet
    model, captured = object.__new__(DeepSeekModel), {}
    model._structured = lambda *args: captured.update(schema=args[2], payload=args[-2])
    model.rewrite_review({'review_rewrite_mode': 'compact',
        'review_packet': build_packet('最多180字', '合成事实。', []),
        'review_feedback': {'claims': [{'index': 0, 'support_status': 'supported'}]}})
    assert captured['schema']['$defs']['AtomicClaim']['properties']['text']['maxLength'] == 180
    packet = captured['payload']['packet']
    assert packet['answer_target_chars'] == 144 and packet['answer_max_chars'] == 180


def test_chinese_sources_receive_query_focused_original_context_too(monkeypatch):
    from app.evidence_context import expand_medical_evidence
    raw = '合成测量步骤。\n\n合成分级标准：甲级区间为10至20，乙级为21至30。\n\n合成随访清单。'
    original = {'raw': raw, 'source_sha256': hashlib.sha256(raw.encode()).hexdigest(),
        'editorial_text': '测量摘要', 'editorial_version': 'v1'}
    doc = {'id': 'chunk-cn', 'document_id': 'cn-synthetic', 'version': 'v1',
        'source_sha256': original['source_sha256'], 'content': '测量摘要', 'start': 0, 'end': 4,
        'source_spans': [{'start': 0, 'end': 7, 'quote': '合成测量步骤。'}]}
    monkeypatch.setattr('app.evidence_context.source_catalog', lambda: {'cn-synthetic': original})
    before = deepcopy(doc)
    result = expand_medical_evidence([doc], query='合成分级标准中的甲级和乙级区间？')[0]
    assert any('甲级区间' in s['quote'] for s in result['source_spans'])
    assert not any('随访清单' in s['quote'] for s in result['source_spans'])
    assert result['content'] == doc['content'] and doc == before
    for span in result['source_spans']:
        assert raw[span['start']:span['end']] == span['quote']


def test_non_nlm_snapshot_is_not_exempt_from_hash_validation(monkeypatch):
    from app.evidence_context import expand_medical_evidence
    doc, original = fixture()
    doc['document_id'] = 'cn-synthetic'
    doc['source_sha256'] = 'wrong'
    monkeypatch.setattr('app.evidence_context.source_catalog', lambda: {'cn-synthetic': original})
    with pytest.raises(ValueError, match='VERSION_INVALID'):
        expand_medical_evidence([doc])


def test_core_gap_rewrite_may_use_already_provided_original_evidence():
    from app.providers import DeepSeekModel
    from app.medical_reviewer import build_packet
    model, captured = object.__new__(DeepSeekModel), {}
    model._structured = lambda *args: captured.update(system=args[3], payload=args[-2])
    model.rewrite_review({'review_packet': build_packet('合成分级区间是什么？', '本次未取得分级区间。', []),
        'review_feedback': {'claims': [{'index': 0, 'support_status': 'contradicted'}]}})
    assert '错误的资料不足声明' in captured['system']
    assert '用户明确询问' in captured['system']
