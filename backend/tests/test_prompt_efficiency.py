"""Wire projections must save tokens without weakening canonical evidence validation."""
from copy import deepcopy
import json

import pytest


def test_review_projection_keeps_all_quotes_and_deduplicates_draft_provenance():
    from app.prompt_context import review_context
    draft = {'index': 0, 'start': 0, 'end': 12, 'text': 'HbA1c通常无需空腹。'}
    packet = {'question': '检查准备？', 'claims': [
        {'index': i, 'text': draft['text'], 'start': 0, 'end': 12, 'original_draft_spans': [draft]}
        for i in range(3)], 'evidence': [{'id': 'e0', 'quote': 'No fasting is required for this test.',
        'document_id': 'doc', 'source_id': 's0', 'source_sha256': 'x'*64, 'start': 3, 'end': 40, 'url': 'https://example.test'}],
        'policy_rules': {'educational_scope': '科普'}, 'corpus_scope': '固定快照'}
    original = deepcopy(packet)
    wire = review_context(packet)
    assert len(wire['draft_spans']) == 1
    assert all(c['draft_ids'] == [0] for c in wire['claims'])
    assert [(e['id'], e['quote'], e['document_id']) for e in wire['evidence']] == [('e0', packet['evidence'][0]['quote'], 'doc')]
    assert packet == original
    assert len(json.dumps(wire)) < len(json.dumps(packet))


def test_dependency_projection_deduplicates_sources_without_forwarding_tool_transcripts():
    from app.prompt_context import dependency_context
    source = {'id': 's0', 'content': '原文摘述', 'source_spans': [{'quote': 'Original text', 'start': 0, 'end': 13}],
        'title': 'title', 'source_sha256': 'x'*64, 'license': 'long attribution', 'url': 'https://example.test'}
    rows = [{'task_id': str(i), 'agent_id': 'research_agent', 'answer': '结果', 'sources': [source],
        'retrieved_sources': [source], 'model_calls': 2} for i in range(2)]
    original = deepcopy(rows)
    wire = dependency_context(rows)
    assert len(wire['sources']) == 1
    assert all(t['source_ids'] == ['s0'] for t in wire['tasks'])
    assert wire['sources'][0]['source_spans'][0]['quote'] == 'Original text'
    assert 'retrieved_sources' not in json.dumps(wire) and 'source_sha256' not in json.dumps(wire)
    assert rows == original


@pytest.mark.parametrize('draft,atom', [
    ('HbA1c通常无需空腹，具体按医护指示。', 'HbA1c无需空腹。'),
    ('这种情况可能影响结果。', '这种情况影响结果。'),
])
def test_atomizer_cannot_silently_drop_qualifier_from_same_proposition(draft, atom):
    from app.medical_reviewer import build_packet, validate_atoms
    from app.contracts import ContractViolation
    packet = build_packet('准备？', draft, [])
    with pytest.raises(ContractViolation, match='ATOM_QUALIFIER_LOST'):
        validate_atoms({'claims': [{'text': atom, 'draft_indices': [0]}]}, packet)
    with pytest.raises(ContractViolation, match='ATOM_QUALIFIER_LOST'):
        validate_atoms({'claims': [{'text': atom, 'draft_indices': [0]}]}, packet, complete=False)


def test_qualifier_guard_does_not_transfer_qualifier_between_unrelated_clauses():
    from app.medical_reviewer import build_packet, validate_atoms
    packet = build_packet('问题', 'HbA1c反映平均血糖，通常无需空腹。', [])
    validate_atoms({'claims': [{'text': 'HbA1c反映平均血糖。', 'draft_indices': [0]},
        {'text': 'HbA1c通常无需空腹。', 'draft_indices': [0]}]}, packet)


def test_real_adapter_rewrite_requests_only_failed_claims_and_keeps_original_evidence():
    from app.providers import DeepSeekModel
    from app.medical_reviewer import build_packet
    from test_realtime_reviewer import source, verdict
    packet = build_packet('检查准备？', 'HbA1c通常不需空腹。未证实的扩展。', [source()])
    model = object.__new__(DeepSeekModel)
    captured = {}
    def capture(operation, name, schema, system, payload, state):
        captured.update(schema=schema, payload=payload)
        return {}
    model._structured = capture
    model.rewrite_review({'review_packet': packet, 'review_feedback': {'claims': [
        verdict(0, evidence_ids=['e0']), verdict(1, status='unsupported')]}})
    wire = captured['payload']['packet']
    assert [c['index'] for c in wire['claims']] == [1]
    assert [c['index'] for c in wire['retained_supported']] == [0]
    assert captured['schema']['$defs']['AtomicClaim']['properties']['draft_indices']['items']['enum'] == [1]
    assert [e['quote'] for e in wire['evidence']] == [e['quote'] for e in packet['evidence']]


def test_tool_result_projection_keeps_call_pairing_and_failure_status():
    from app.prompt_context import tool_context
    message = {'role': 'tool', 'tool_call_id': 'tool-1', 'content': json.dumps({
        'success': False, 'status': 'failed', 'safe_error_code': 'TOOL_FAILED', 'documents': []})}
    projected = tool_context(message)
    assert projected['tool_call_id'] == 'tool-1'
    assert json.loads(projected['content']) == json.loads(message['content'])


def test_internal_atomic_expansion_does_not_discard_a_concise_reviewable_answer():
    from app.medical_reviewer import build_packet, validate_atoms
    packet = build_packet('不超过20字', '收缩压看搏动，舒张压看间歇。', [])
    # Internal atomic facts repeat subjects; final answer length is a separate check.
    validate_atoms({'claims': [
        {'text': '收缩压是心脏搏动时的压力。', 'draft_indices': [0]},
        {'text': '舒张压是心脏在两次搏动之间休息时的压力。', 'draft_indices': [0]}]}, packet)


def test_native_source_parameter_leak_triggers_format_repair_instead_of_evidence_loss():
    from app.providers import DeepSeekModel, ProviderError
    from app.config import Settings
    model = object.__new__(DeepSeekModel)
    model.settings = Settings(jwt_secret='x'*40, knowledge_profile='medical')
    model._chat = lambda *a, **k: {'tool_calls': [{'id': 'final', 'function': {'name': 'final_response',
        'arguments': json.dumps({'answer': '回答。</answer>\n<parameter name="source_ids">["s0"]', 'source_ids': []})}}]}
    state = {'agent_id': 'research_agent', 'question': '问题', 'messages': [], 'allowed_tools': [],
        'observations': [{'result': {'documents': [{'id': 's0', 'content': '证据'}]}}]}
    with pytest.raises(ProviderError, match='MODEL_DECISION_INVALID'):
        model.decide(state)
    # Plain explicit lack of evidence still follows the normal partial-evidence path.
    model._chat = lambda *a, **k: {'content': json.dumps({'answer': '现有资料不足以回答。', 'source_ids': []})}
    assert model.decide(state)['source_ids'] == []
