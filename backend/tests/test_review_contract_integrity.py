"""Offline regressions for evidence integrity; synthetic text is not medical gold."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.contracts import ContractViolation
from app.medical_quality import is_policy_or_refusal
from app.medical_reviewer import (
    AtomicSubmission, ComposedReview, MedicalReviewerMixin, apply_review,
    atomic_packet, build_packet, merge_rewrite, validate_atoms, validate_review,
)
from app.multitask import MultiTaskMixin
from app.workflow import SingleAgentFlow, StopFlow


@pytest.fixture
def synthetic_source(monkeypatch):
    original = {'raw': 'Synthetic original paragraph.', 'editorial_text': '合成摘述。',
        'source_sha256': 'a' * 64, 'editorial_version': 'v1', 'url': 'https://example.test/source'}
    monkeypatch.setattr('app.medical_reviewer.source_catalog', lambda: {'doc': original})
    source = {'id': 's0', 'source': 'synthetic', 'document_id': 'doc', 'source_sha256': 'a' * 64,
        'version': 'v1', 'start': 0, 'end': len(original['editorial_text']),
        'content': original['editorial_text'], 'source_spans': []}
    return original, source


def verdict(index=0, evidence_ids=None, status='supported'):
    return {'index': index, 'kind': 'medical_fact', 'support_status': status,
        'evidence_ids': evidence_ids or [], 'policy_rules': [], 'note': 'Synthetic contract test.'}


@pytest.mark.parametrize('answer', [
    '免责声明：这是合成测试。药物甲可降低血压。',
    '无法提供个人处方，但药物甲可降低血压。',
    '严格遵守医嘱，药物甲可降低血压。',
    '无法提供未授权的HIS爆破脚本。药物甲可降低血压。',
    '隐私合规要求：血压超过合成阈值应自行加倍用药。',
])
def test_refusal_words_do_not_exempt_medical_content(answer):
    assert not is_policy_or_refusal(answer)


def test_pure_policy_refusal_does_not_need_medical_evidence():
    assert is_policy_or_refusal('无法提供未授权的HIS爆破脚本。')


def test_mixed_refusal_cannot_bypass_required_single_task_evidence():
    flow = object.__new__(SingleAgentFlow)
    flow._evidence_diagnostic = lambda *args: None
    state = {'answer': '免责声明：这是合成测试。药物甲可降低血压。', 'question': '合成问题',
        'source_ids': [], 'observations': [], 'plan': {'tasks': [{'require_sources': True}]}}
    with pytest.raises(StopFlow) as error:
        flow._validate(state)
    assert error.value.code == 'EVIDENCE_MISSING'


class ReviewHarness(MedicalReviewerMixin):
    def __init__(self, atom_error=None):
        self.settings = SimpleNamespace(knowledge_profile='medical', medical_reviewer_enabled=True,
            deepseek_enabled=False)
        self.model = SimpleNamespace(review=lambda s: None)
        if atom_error is not None:
            self.model.atomize = lambda s: None
        self.atom_error = atom_error
        self.metadata, self.diagnostics, self.review_calls = {}, [], 0

    def _save_review(self, state, update):
        self.metadata.update(update(self.metadata) if callable(update) else deepcopy(update))

    def _evidence_diagnostic(self, state, diagnostic):
        self.diagnostics.append(deepcopy(diagnostic))

    def _contract_call(self, *args):
        raise self.atom_error

    def _review_claims(self, state, packet, stage, round_number):
        self.review_calls += 1
        return validate_review({'claims': [verdict(i, status='unsupported')
            for i in range(len(packet['claims']))]}, packet)


def review_state(answer='药物甲可降低血压。'):
    return {'question': '合成问题', 'answer': answer, 'sources': [], 'context': {},
        'outcome': 'completed', 'error_code': None}


def test_mixed_refusal_still_enters_claim_reviewer():
    flow = ReviewHarness()
    result = flow._review_output(review_state('免责声明：这是合成测试。药物甲可降低血压。'))
    assert flow.review_calls == 1
    assert result['outcome'] == 'partial' and '药物甲' not in result['answer']
    assert flow.metadata['citation_support_status'] == 'model_reviewed'


@pytest.mark.parametrize('code,outcome', [
    ('LEASE_LOST', 'failed'), ('CANCELLED', 'cancelled'), ('STEP_TIMEOUT', 'timed_out'),
    ('MODEL_BUDGET_EXCEEDED', 'failed'), ('WORKER_MODEL_BUDGET_EXCEEDED', 'failed'),
])
def test_atom_fallback_never_swallows_execution_controls(code, outcome):
    flow = ReviewHarness(StopFlow(code, outcome))
    if code == 'LEASE_LOST' or outcome != 'failed':
        with pytest.raises(StopFlow) as error:
            flow._review_output(review_state())
        assert error.value.code == code
    else:
        result = flow._review_output(review_state())
        assert result['error_code'] == code
        assert flow.metadata['reviewer_status'] == 'failed'
    assert flow.review_calls == 0
    assert flow.metadata['atomization_status'] != 'fallback_raw_claims'


def test_exhausted_atom_contract_can_review_originals_with_explicit_fallback():
    flow = ReviewHarness(StopFlow('ATOM_INVALID'))
    result = flow._review_output(review_state())
    assert flow.review_calls == 1 and result['outcome'] == 'partial'
    assert flow.metadata['atomization_status'] == 'fallback_raw_claims'
    assert flow.metadata['atomization_error_code'] == 'ATOM_INVALID'


@pytest.mark.parametrize('field,value', [('source_sha256', 'b' * 64), ('version', 'different-v1')])
def test_different_source_snapshot_is_not_relabelled(synthetic_source, field, value):
    _, source = synthetic_source
    source[field] = value
    before = deepcopy(source)
    packet = build_packet('合成问题', '合成断言。', [source])
    assert source == before
    assert packet['evidence'] == []
    assert packet['source_diagnostics'][0]['code'] == 'REVIEW_SOURCE_VERSION_INVALID'


def test_invalid_old_anchor_is_removed_from_final_source(synthetic_source):
    _, source = synthetic_source
    source['source_spans'] = [{'start': 999, 'end': 1000, 'quote': 'Invalid anchor'}]
    before = deepcopy(source)
    packet = build_packet('合成问题', '合成断言。', [source])
    output = validate_review({'claims': [verdict(evidence_ids=['e0'])]}, packet)
    applied = apply_review(output, packet, [source])
    assert source == before
    assert applied['sources'][0]['source_spans'] == [
        {k: packet['evidence'][0][k] for k in ('start', 'end', 'quote')}]
    assert packet['source_diagnostics'][0]['code'] == 'REVIEW_SOURCE_ANCHOR_INVALID'


def test_unique_offset_relocation_is_copied_and_recorded(synthetic_source):
    _, source = synthetic_source
    source.update(start=1, end=2)
    before = deepcopy(source)
    packet = build_packet('合成问题', '合成断言。', [source])
    assert source == before and packet['evidence']
    assert packet['validated_sources'][0]['start'] == 0
    diagnostic = packet['source_diagnostics'][0]
    assert diagnostic['code'] == 'REVIEW_SOURCE_OFFSET_RELOCATED'
    assert diagnostic['original_start'] == 1 and diagnostic['resolved_start'] == 0


def test_ambiguous_offset_is_rejected(synthetic_source):
    original, source = synthetic_source
    original['editorial_text'] *= 2
    source.update(start=1, end=2)
    packet = build_packet('合成问题', '合成断言。', [source])
    assert not packet['evidence']
    assert packet['source_diagnostics'][0]['code'] == 'REVIEW_SOURCE_CONTENT_INVALID'


def test_all_sources_rejected_returns_honest_omission_without_key_error(synthetic_source):
    _, source = synthetic_source
    source['document_id'] = 'unknown'
    packet = build_packet('合成问题', '合成断言。', [source])
    output = validate_review({'claims': [verdict(status='unsupported')]}, packet)
    applied = apply_review(output, packet, [source])
    assert applied['sources'] == [] and applied['omitted_claim_count'] == 1
    assert '合成断言' not in applied['answer']
    assert packet['source_diagnostics'][0]['code'] == 'REVIEW_SOURCE_UNKNOWN'


@pytest.mark.parametrize('indices', [[99], [-1], [0, 99], [0, 0]])
def test_invalid_atom_provenance_is_rejected_before_packet_indexing(indices):
    packet = build_packet('合成问题', '原句。', [])
    raw = {'claims': [{'text': '改写句。', 'draft_indices': indices}]}
    before = deepcopy(raw)
    with pytest.raises((ContractViolation, ValueError)):
        atoms = validate_atoms(raw, packet)
        atomic_packet(atoms, packet)
    assert raw == before


def test_missing_coverage_never_expands_80_atoms_to_159():
    packet = build_packet('合成问题', ''.join(f'原句{i}。' for i in range(80)), [])
    raw = {'claims': [{'text': f'原子{i}。', 'draft_indices': [0]} for i in range(80)]}
    with pytest.raises(ContractViolation, match='COVERAGE'):
        validate_atoms(raw, packet)


def test_invalid_atoms_cannot_cause_index_error_even_if_validator_is_bypassed():
    packet = build_packet('合成问题', '原句。', [])
    atoms = AtomicSubmission(claims=[{'text': '改写句。', 'draft_indices': [99]}])
    with pytest.raises(ContractViolation, match='PROVENANCE'):
        atomic_packet(atoms, packet)


def test_two_80_claim_rounds_fit_bounded_internal_composition():
    packet = build_packet('合成问题', ''.join(f'原句{i}。' for i in range(80)), [])
    first = validate_review({'claims': [verdict(i, status='unsupported') for i in range(80)]}, packet)
    atoms = validate_atoms({'claims': [{'text': f'改写{i}。', 'draft_indices': [0]}
        for i in range(80)]}, packet, complete=False)
    rewritten = atomic_packet(atoms, packet)
    second = validate_review({'claims': [verdict(i, status='unsupported') for i in range(80)]}, rewritten)
    combined, output = merge_rewrite(packet, first, rewritten, second, atoms)
    assert isinstance(output, ComposedReview) and len(output.claims) == len(combined['claims']) == 159


class SynthesisHarness(MultiTaskMixin):
    def __init__(self, raw):
        self.raw = raw
        self.model = SimpleNamespace(synthesize=lambda s: None)

    def _contract_call(self, state, stage, function, validate, invalid_code):
        try:
            return validate(self.raw)
        except ContractViolation:
            raise StopFlow(invalid_code) from None


def synthesis_state():
    return {'question': '合成问题', 'task_results': [
        {'task_id': key, 'status': 'completed', 'answer': f'任务{key}的输出',
         'sources': [{'id': f's{key}', 'content': f'资料{key}', 'source': 'synthetic'}]}
        for key in ('a', 'b')]}


@pytest.mark.parametrize('tasks,sources', [
    (['a'], ['sa', 'sb']), (['a', 'a', 'b'], ['sa', 'sb']),
    (['a', 'b'], ['invented']), (['a', 'b'], ['sa']), (['a', 'b'], ['sa', 'sa', 'sb']),
])
def test_synthesis_does_not_fabricate_missing_or_invalid_coverage(tasks, sources):
    state = synthesis_state()
    result = SynthesisHarness({'answer': '未经覆盖校验的汇总', 'task_ids': tasks,
        'source_ids': sources})._synthesize(state)
    assert result['outcome'] == 'partial' and result['error_code'] == 'SYNTHESIS_INVALID'
    assert '未经覆盖校验的汇总' not in result['answer']
    assert all(f'任务{key}的输出' in result['answer'] for key in ('a', 'b'))


def test_synthesized_sources_do_not_alias_worker_evidence():
    state = synthesis_state()
    before = deepcopy(state)
    result = SynthesisHarness({'answer': '两项任务的汇总', 'task_ids': ['a', 'b'],
        'source_ids': ['sa', 'sb']})._synthesize(state)
    assert result['outcome'] == 'completed'
    result['sources'][0]['content'] = '外部修改'
    assert state == before


def test_same_chunk_with_different_snapshot_hash_is_a_source_conflict():
    from app.agent import source_identity
    source = {'id': 's0', 'source': 'synthetic', 'content': '合成资料', 'source_sha256': 'a' * 64}
    assert source_identity(source) != source_identity({**source, 'source_sha256': 'b' * 64})


def test_medical_fact_cannot_hide_in_a_referral_sentence():
    packet = build_packet('合成问题', '药物甲可降低血压并损伤肝脏，建议就医。', [])
    raw = {'claims': [
        {**verdict(), 'kind': 'project_behavior', 'policy_rules': ['urgent']}]}
    with pytest.raises(ContractViolation, match='FACT_CLASSIFICATION'):
        validate_review(raw, packet)
