"""Scoped regressions: preserve supported cores, never release an unchecked rewrite."""
import pytest
from fastapi.testclient import TestClient
from test_api import settings, login, session
from test_graph import ask, call
from test_realtime_reviewer import application, verdict


def run(app):
    with TestClient(app) as client:
        app.state.flow.tools.execute = app.state.test_tools_execute
        headers = login(client)
        result = ask(client, headers, session(client, headers), '研究血压').json()
        assert client.get('/runs/' + result['run_id'], headers=headers).json() == result
        return result


def refinement_app(settings, second_status='supported', budget=10):
    counts = {'reviews': 0, 'rewrites': 0}
    def review(s):
        counts['reviews'] += 1
        p = s['review_packet']
        return {'claims': [verdict(i, status=('partially_supported' if counts['reviews'] == 1 else second_status),
            evidence_ids=[p['evidence'][0]['id']]) for i in range(len(p['claims']))]}
    app = application(settings, review, budget=budget)
    app.state.model.atomize = lambda s: {'claims': [
        {'text': c['text'], 'draft_indices': [c['index']]} for c in s['review_packet']['claims']]}
    def rewrite(s):
        counts['rewrites'] += 1
        return {'claims': [{'text': '收缩压是心脏搏动时的压力。', 'draft_indices': [0]}]}
    app.state.model.rewrite_review = rewrite
    return app, counts


def test_supported_core_restored_by_exactly_one_rewrite_and_second_review(settings):
    app, counts = refinement_app(settings)
    result = run(app)
    assert counts == {'reviews': 2, 'rewrites': 1}
    assert result['review_rewrite_count'] == 1 and result['review_rewrite_status'] == 'completed'
    assert len(result['review_rounds']) == 2 and result['atomization_status'] == 'completed'
    assert result['model_calls'] == 7 and '收缩压是心脏搏动时的压力' in result['answer']
    assert '未证实的治疗' not in result['answer']


def test_still_unsupported_after_rewrite_is_removed_without_third_round(settings):
    app, counts = refinement_app(settings, second_status='unsupported')
    result = run(app)
    assert counts == {'reviews': 2, 'rewrites': 1}
    # One rejected replacement plus the unreplaced second original claim.
    assert result['result_status'] == 'partial' and result['omitted_claim_count'] == 2
    assert '收缩压是心脏搏动时的压力' not in result['answer']


def test_budget_exhaustion_before_second_review_does_not_leak_rewrite(settings):
    app, counts = refinement_app(settings, budget=6)
    result = run(app)
    assert counts == {'reviews': 1, 'rewrites': 1}
    assert result['model_calls'] == 6 and result['safe_error_code'] == 'MODEL_BUDGET_EXCEEDED'
    assert '收缩压是心脏搏动时的压力' not in result['answer']


def test_atomic_provenance_requires_complete_original_coverage():
    from app.medical_reviewer import validate_atoms, build_packet
    from app.contracts import ContractViolation
    packet = build_packet('问题', '核心。附加条件。', [])
    with pytest.raises(ContractViolation, match='COVERAGE'):
        validate_atoms({'claims': [{'text': '核心。', 'draft_indices': [0]}]}, packet)
    atoms = validate_atoms({'claims': [{'text': '核心一。', 'draft_indices': [0]},
        {'text': '核心二。', 'draft_indices': [0]}, {'text': '附加条件。', 'draft_indices': [1]}]}, packet)
    assert len(atoms.claims) == 3


def test_initial_supported_output_does_not_trigger_rewrite(settings):
    app, counts = refinement_app(settings)
    def review(s):
        counts['reviews'] += 1
        p = s['review_packet']
        return {'claims': [verdict(i, evidence_ids=[p['evidence'][0]['id']]) for i in range(len(p['claims']))]}
    app.state.model.review = review
    result = run(app)
    assert counts == {'reviews': 1, 'rewrites': 0}
    assert result['review_rewrite_count'] == 0 and result['model_calls'] == 5


def test_invalid_rewrite_can_only_format_repair_once_then_closes(settings):
    app, counts = refinement_app(settings.model_copy(update={'schema_repair_limit': 1}))
    attempts = []
    def invalid(s):
        attempts.append(s.get('contract_repair'))
        return {'claims': [{'text': '不准泄漏的改写。', 'draft_indices': [999]}]}
    app.state.model.rewrite_review = invalid
    result = run(app)
    assert len(attempts) == 2 and attempts[0] is None and attempts[1]
    assert result['review_rewrite_count'] == 1 and result['review_rewrite_status'] == 'failed'
    assert result['contract_repair_counts']['review_rewrite'] == 1
    assert counts['reviews'] == 1 and result['model_calls'] == 7
    assert '不准泄漏' not in result['answer']


def test_atomic_provenance_preserves_condition_and_decimal_for_reviewer():
    from app.medical_reviewer import validate_atoms, atomic_packet, build_packet
    draft = '若处于条件A且数值为4.5 mmol/L，需要核对。'
    packet = build_packet('问题', draft, [])
    atoms = validate_atoms({'claims': [{'text': draft, 'draft_indices': [0]}]}, packet)
    rewritten = atomic_packet(atoms, packet)
    assert rewritten['claims'][0]['original_draft_spans'][0]['text'] == draft
    assert rewritten['claims'][0]['text'] == draft and len(packet['claims']) == 1


def test_all_sources_anchor_paragraphs_precede_long_first_document(monkeypatch):
    from app.medical_reviewer import build_packet
    paragraphs = '\n\n'.join('First paragraph '+str(i) for i in range(100))
    originals = {'one': {'raw': paragraphs, 'source_sha256': 'h1', 'editorial_version': 'v', 'editorial_text': '编辑', 'url': 'u1'},
        'two': {'raw': 'Second retrieved anchor', 'source_sha256': 'h2', 'editorial_version': 'v', 'editorial_text': '编辑', 'url': 'u2'}}
    monkeypatch.setattr('app.medical_reviewer.source_catalog', lambda: originals)
    sources = [{'id': key, 'document_id': key, 'source_sha256': doc['source_sha256'], 'version': 'v',
        'start': 0, 'end': 2, 'content': '编辑', 'source_spans': []} for key, doc in originals.items()]
    sources[1]['source_spans'] = [{'start': 0, 'end': len(originals['two']['raw']), 'quote': originals['two']['raw']}]
    packet = build_packet('问题', '答案。', sources)
    assert packet['evidence'][0]['document_id'] == 'two' and len(packet['evidence']) == 80
    sources[1]['source_spans'] = []
    packet = build_packet('问题', '答案。', sources)
    assert any(e['document_id'] == 'two' for e in packet['evidence'])


def test_calibration_gold_never_in_provider_packet():
    import json
    from pathlib import Path
    from scripts.calibrate_medical_reviewer import calibration_packet
    fixtures_path = Path(__file__).resolve().parents[1] / 'evaluation/reviewer-calibration-v1/fixtures.json'
    fixtures = json.loads(fixtures_path.read_text(encoding='utf-8'))
    packet = calibration_packet(fixtures)
    assert len(packet['claims']) == 10
    assert all('accept' not in c and 'kind' not in c for c in packet['claims'])


def test_review_batches_fit_output_budget_and_rebase_indices(settings):
    calls = []
    def review(s):
        packet = s['review_packet']; calls.append(len(packet['claims']))
        assert len(packet['claims']) <= 10
        return {'claims': [verdict(i, evidence_ids=[packet['evidence'][0]['id']]) for i in range(len(packet['claims']))]}
    app = application(settings, review)
    app.state.model.atomize = lambda s: {'claims': [
        {'text': '收缩压是心脏搏动时的压力。', 'draft_indices': [0 if i < 13 else 1]} for i in range(14)]}
    result = run(app)
    assert calls == [10, 4] and result['reviewer_status'] == 'completed'
    assert result['model_calls'] == 6 and result['review_packet_summary']['claims'] == 14
    assert [c['index'] for c in result['claim_reviews'][:-1]] == list(range(14))


def test_rewrite_cannot_silently_discard_previously_supported_fact(settings):
    calls = []
    def review(s):
        p = s['review_packet']; calls.append(1)
        return {'claims': [verdict(i, status=('unsupported' if len(calls) == 1 and i == 1 else 'supported'),
            evidence_ids=[p['evidence'][0]['id']]) for i in range(len(p['claims']))]}
    app = application(settings, review)
    app.state.model.rewrite_review = lambda s: {'claims': [
        {'text': '重述后通过的第二条事实。', 'draft_indices': [1]}]}
    result = run(app)
    assert len(calls) == 2
    assert '收缩压是心脏搏动时的压力。' in result['answer']
    retained = next(c for c in result['claim_reviews'] if c['text'] == '收缩压是心脏搏动时的压力。')
    assert retained['review_round'] == 1 and retained['evidence']
    assert retained['final_start'] is not None


def test_discarded_unreviewed_fact_remains_an_omission_not_completed(settings):
    calls = []
    def review(s):
        p = s['review_packet']; calls.append(1)
        return {'claims': [verdict(i, status=('unsupported' if len(calls) == 1 and i == 1 else 'supported'),
            evidence_ids=[p['evidence'][0]['id']]) for i in range(len(p['claims']))]}
    app = application(settings, review)
    app.state.model.rewrite_review = lambda s: {'claims': [
        {'text': '收缩压是心脏搏动时的压力。', 'draft_indices': [0]}]}
    result = run(app)
    assert result['result_status'] == 'partial' and result['omitted_claim_count'] == 1
    assert '未证实的治疗。' not in result['answer']
    rejected = next(c for c in result['claim_reviews'] if c['text'] == '未证实的治疗。')
    assert rejected['review_round'] == 1 and rejected['final_start'] is None


def test_composed_review_keeps_large_approved_core_without_expanding_external_batch_limit():
    from pydantic import ValidationError
    from app.medical_reviewer import build_packet, validate_review, validate_atoms, atomic_packet, merge_rewrite, ReviewSubmission
    from test_realtime_reviewer import source
    packet = build_packet('合成结构测试', ''.join(f'合成事实{i}。' for i in range(80)), [source()])
    raw = {'claims': [verdict(i, status='unsupported' if i == 79 else 'supported',
        evidence_ids=[packet['evidence'][0]['id']]) for i in range(80)]}
    first = validate_review(raw, packet)
    atoms = validate_atoms({'claims': [{'text': f'复审事实{i}。', 'draft_indices': [79]} for i in range(80)]},
                           packet, complete=False)
    revised = atomic_packet(atoms, packet)
    second = validate_review({'claims': [verdict(i, evidence_ids=[packet['evidence'][0]['id']]) for i in range(80)]}, revised)
    merged, output = merge_rewrite(packet, first, revised, second, atoms)
    assert len(merged['claims']) == len(output.claims) == 159
    assert merged['claims'][0]['review_round'] == 1 and merged['claims'][-1]['review_round'] == 2
    with pytest.raises(ValidationError):
        ReviewSubmission(claims=output.claims)  # External model output still has the 80-claim limit.


def test_failed_rewrite_cannot_replace_an_already_supported_fasting_answer():
    from app.medical_reviewer import build_packet, validate_review, validate_atoms, atomic_packet, merge_rewrite, apply_review
    from test_realtime_reviewer import source
    packet = build_packet('检查准备？', 'HbA1c通常不需空腹。未证实的扩展。', [source()])
    first = validate_review({'claims': [verdict(0, evidence_ids=[packet['evidence'][0]['id']]),
        verdict(1, status='unsupported')]}, packet)
    # Reproduce the recorded failure: a rewrite unnecessarily touches an approved core,
    # and the second reviewer rejects that replacement. Keep the approved original.
    atoms = validate_atoms({'claims': [{'text': 'HbA1c检测无需空腹。', 'draft_indices': [0]}]}, packet, complete=False)
    rewritten = atomic_packet(atoms, packet)
    second = validate_review({'claims': [verdict(0, status='partially_supported',
        evidence_ids=[packet['evidence'][0]['id']])]}, rewritten)
    combined, output = merge_rewrite(packet, first, rewritten, second, atoms)
    result = apply_review(output, combined, [source()])
    assert 'HbA1c通常不需空腹。' in result['answer']
    assert 'HbA1c检测无需空腹。' not in result['answer']
    assert result['omitted_claim_count'] == 1
    assert result['claim_reviews'][0]['review_round'] == 1


def test_no_supported_replacement_keeps_core_and_omission_without_inventing_a_second_review(settings):
    calls = []
    def review(s):
        calls.append(1)
        return {'claims': [verdict(i, status='supported' if i == 0 else 'unsupported',
            evidence_ids=[s['review_packet']['evidence'][0]['id']] if i == 0 else [])
            for i in range(len(s['review_packet']['claims']))]}
    app = application(settings, review)
    app.state.model.rewrite_review = lambda s: {'claims': []}
    result = run(app)
    assert calls == [1] and result['omitted_claim_count'] == 1 and result['result_status'] == 'partial'
    assert result['review_rewrite_status'] == 'no_supported_replacement'
    assert result['reviewer_status'] == 'completed' and len(result['review_rounds']) == 1
    assert '收缩压是心脏搏动时的压力。' in result['answer']
    assert result['answer_body_chars'] == len('收缩压是心脏搏动时的压力。')
    assert result['answer_max_chars'] is None and result['answer_length_status'] == 'not_requested'


@pytest.mark.parametrize('limit,expected_status', [(20, 'passed'), (5, 'exceeded')])
def test_final_length_is_visible_through_api_without_truncating_supported_facts(settings, limit, expected_status):
    def review(s):
        return {'claims': [verdict(i, evidence_ids=[s['review_packet']['evidence'][0]['id']])
            for i in range(len(s['review_packet']['claims']))]}
    app = application(settings, review)
    app.state.model.decide = lambda s: ({'answer': '收缩压是心脏搏动时的压力。', 'source_ids': ['citation-1']}
        if s['observations'] else {'tool_calls': [call(query='source')]})
    with TestClient(app) as client:
        app.state.flow.tools.execute = app.state.test_tools_execute
        headers = login(client)
        result = ask(client, headers, session(client, headers), f'研究血压，最多{limit}字').json()
        assert result['answer_body_chars'] == len('收缩压是心脏搏动时的压力。')
        assert result['answer_max_chars'] == limit and result['answer_length_status'] == expected_status
        assert '收缩压是心脏搏动时的压力。' in result['answer']
        assert (result['result_status'] == 'completed') == (expected_status == 'passed')
        assert client.get('/runs/'+result['run_id'], headers=headers).json() == result


@pytest.mark.parametrize('failure', [None, 'missing_fact', 'rejected', 'budget'])
def test_overlong_supported_answer_compacts_once_with_coverage_and_review_or_retains_original(settings, failure):
    original = '收缩压是心脏搏动时的压力。心脏搏动时的压力称为收缩压。'
    calls = {'reviews': 0, 'rewrites': 0}
    def review(s):
        calls['reviews'] += 1
        if calls['reviews'] == 2:
            assert len(s['review_packet']['claims'][0]['preserved_facts']) == 2
        return {'claims': [verdict(i, status='unsupported' if failure == 'rejected' and calls['reviews'] == 2 else 'supported',
            evidence_ids=[s['review_packet']['evidence'][0]['id']]) for i in range(len(s['review_packet']['claims']))]}
    app = application(settings, review, budget=5 if failure == 'budget' else 10)
    app.state.model.decide = lambda s: ({'answer': original, 'source_ids': ['citation-1']}
        if s['observations'] else {'tool_calls': [call(query='source')]})
    def rewrite(s):
        calls['rewrites'] += 1
        assert s['review_rewrite_mode'] == 'compact'
        return {'claims': [{'text': '收缩压是心脏搏动时的压力。',
            'draft_indices': [0] if failure == 'missing_fact' else [0, 1]}]}
    app.state.model.rewrite_review = rewrite
    with TestClient(app) as client:
        app.state.flow.tools.execute = app.state.test_tools_execute
        headers = login(client)
        result = ask(client, headers, session(client, headers), '研究血压，不超过18字').json()
        # One rewrite cycle permits one counted contract-format repair.
        assert calls['rewrites'] == (2 if failure == 'missing_fact' else 1)
        assert result['review_rewrite_count'] == 1
        if failure == 'missing_fact':
            assert result['contract_repair_counts']['review_rewrite'] == 1
        if failure is None:
            assert result['result_status'] == 'completed' and result['answer_body_chars'] <= 18
            assert original not in result['answer'] and result['review_rewrite_status'] == 'compact_completed'
        else:
            assert original in result['answer'] and result['result_status'] == 'partial'
            assert result['safe_error_code'] == 'ANSWER_LENGTH_EXCEEDED'
        assert result['omitted_claim_count'] == 0


@pytest.mark.parametrize('replace_missing', [True, False])
def test_support_repair_and_length_share_one_reviewed_rewrite_without_hiding_unrepaired_claims(settings, replace_missing):
    calls = {'reviews': 0, 'rewrites': 0}
    def review(s):
        calls['reviews'] += 1
        if calls['reviews'] == 2 and replace_missing:
            assert s['review_packet']['claims'][1]['repair_targets'][0]['index'] == 1
            assert s['review_packet']['claims'][0]['preserved_facts'][0]['index'] == 0
        return {'claims': [verdict(i, status='partially_supported' if calls['reviews'] == 1 and i == 1 else 'supported',
            evidence_ids=[s['review_packet']['evidence'][0]['id']]) for i in range(len(s['review_packet']['claims']))]}
    app = application(settings, review)
    def rewrite(s):
        calls['rewrites'] += 1
        assert s['review_rewrite_mode'] == 'compact'
        claims = [{'text': '收缩压是心脏搏动时的压力。', 'draft_indices': [0]}]
        if replace_missing: claims.append({'text': '舒张压是心脏休息时的压力。', 'draft_indices': [1]})
        return {'claims': claims}
    app.state.model.rewrite_review = rewrite
    with TestClient(app) as client:
        app.state.flow.tools.execute = app.state.test_tools_execute
        headers = login(client)
        result = ask(client, headers, session(client, headers), '研究血压，最多30字').json()
        assert calls == {'reviews': 2, 'rewrites': 1} and result['review_rewrite_count'] == 1
        assert result['answer_length_status'] == 'passed'
        assert result['omitted_claim_count'] == (0 if replace_missing else 1)
        assert result['result_status'] == ('completed' if replace_missing else 'partial')
