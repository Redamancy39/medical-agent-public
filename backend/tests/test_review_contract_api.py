"""Fake-provider API/SQLite acceptance for batch 1, without cloud calls."""
from copy import deepcopy

from fastapi.testclient import TestClient

from app.main import create_app
from app.config import Settings
from test_api import login, session
from test_graph import ask, call
from test_multitask import task
from test_review_contract_integrity import synthetic_source, verdict


def application(tmp_path, source, review):
    config = Settings(database_path=tmp_path / 'isolated.db', jwt_secret='synthetic-signing-key-' + 'x' * 40,
        knowledge_profile='medical', maintenance_enabled=False, medical_reviewer_enabled=True,
        schema_repair_limit=1, max_model_calls=10)
    app = create_app(config)
    app.state.model.plan = lambda s: {'tasks': [task('one', require_sources=True)]}
    app.state.model.decide = lambda s: ({'answer': '这是合成断言。另一条合成断言。', 'source_ids': ['s0']}
        if s['observations'] else {'tool_calls': [call(query='synthetic source')]})
    app.state.model.review = review
    return app


def test_rejected_snapshot_diagnostics_survive_sql_and_api(tmp_path, synthetic_source):
    _, source = synthetic_source
    source['source_sha256'] = 'b' * 64
    before = deepcopy(source)
    seen = []

    def review(state):
        packet = state['review_packet']
        seen.append(packet)
        assert packet['evidence'] == []
        return {'claims': [verdict(i, status='unsupported') for i in range(len(packet['claims']))]}

    app = application(tmp_path, source, review)
    with TestClient(app) as client:
        app.state.flow.tools.execute = lambda *args: {'success': True, 'documents': [source]}
        headers = login(client)
        result = ask(client, headers, session(client, headers), '合成医学问题').json()
        assert seen and source == before
        assert result['result_status'] == 'partial' and result['omitted_claim_count'] == 2
        assert result['sources'] == [] and '合成断言' not in result['answer']
        diagnostic = next(d for d in result['evidence_diagnostics'] if d['stage'] == 'review_source_binding')
        assert diagnostic['code'] == 'REVIEW_SOURCE_VERSION_INVALID'
        assert diagnostic['received_sha256'] == 'b' * 64
        assert client.get('/runs/' + result['run_id'], headers=headers).json() == result


def test_atom_contract_repairs_once_then_reviews_originals_and_exposes_status(tmp_path, synthetic_source):
    _, source = synthetic_source
    seen, atom_calls = [], []

    def review(state):
        packet = state['review_packet']
        seen.append([c['text'] for c in packet['claims']])
        return {'claims': [verdict(i, evidence_ids=['e0']) for i in range(len(packet['claims']))]}

    app = application(tmp_path, source, review)

    def invalid_atoms(state):
        atom_calls.append(state.get('contract_repair'))
        return {'claims': [{'text': '不能进入回答的无效原子句。', 'draft_indices': [999]}]}

    app.state.model.atomize = invalid_atoms
    with TestClient(app) as client:
        app.state.flow.tools.execute = lambda *args: {'success': True, 'documents': [source]}
        headers = login(client)
        result = ask(client, headers, session(client, headers), '合成医学问题').json()
        assert len(atom_calls) == 2 and atom_calls[0] is None and atom_calls[1]
        assert seen == [['这是合成断言。', '另一条合成断言。']]
        assert result['result_status'] == 'completed' and '无效原子句' not in result['answer']
        assert result['atomization_status'] == 'fallback_raw_claims'
        assert result['atomization_error_code'] == 'ATOM_INVALID'
        assert result['contract_repair_counts'] == {'atomize': 1}
        assert result['model_calls'] == 6 and result['reviewer_status'] == 'completed'
        assert client.get('/runs/' + result['run_id'], headers=headers).json() == result


def test_pure_policy_refusal_skips_medical_review_without_dropping_response(tmp_path, synthetic_source):
    _, source = synthetic_source

    def no_medical_review(state):
        raise AssertionError('A pure non-medical refusal does not assert medical facts.')

    app = application(tmp_path, source, no_medical_review)
    app.state.model.decide = lambda s: {'answer': '无法提供未授权的HIS爆破脚本。', 'source_ids': []}
    with TestClient(app) as client:
        headers = login(client)
        result = ask(client, headers, session(client, headers), '合成安全边界问题').json()
        assert result['result_status'] == 'completed'
        assert result['answer'] == '无法提供未授权的HIS爆破脚本。'
        assert result['reviewer_status'] == 'skipped_policy'
        assert result['citation_support_status'] == 'policy_exempt'
        assert result['clinical_review_status'] == 'not_run' and result['model_calls'] == 2


def test_scope_exclusion_is_persisted_without_rewrite_or_false_evidence_failure(tmp_path, synthetic_source):
    _, source = synthetic_source
    app = application(tmp_path, source, lambda state: {'claims': [verdict(0, ['e0']),
        {**verdict(1, ['e0']), 'scope_status': 'out_of_scope', 'scope_note': '独立题外知识。'}]})
    app.state.model.rewrite_review = lambda state: (_ for _ in ()).throw(AssertionError('No support repair needed.'))
    with TestClient(app) as client:
        app.state.flow.tools.execute = lambda *args: {'success': True, 'documents': [source]}
        headers = login(client)
        result = ask(client, headers, session(client, headers), '合成核心问题').json()
        assert result['result_status'] == 'completed' and result['omitted_claim_count'] == 0
        assert result['scope_omitted_claim_count'] == result['retained_claim_count'] == 1
        assert result['review_rewrite_count'] == 0 and '另一条合成断言' not in result['answer']
        assert result['claim_reviews'][1]['exclusion_reason'] == 'outside_question'
        assert client.get('/runs/'+result['run_id'], headers=headers).json() == result


def test_scope_cannot_turn_an_empty_answer_into_completed(tmp_path, synthetic_source):
    _, source = synthetic_source
    app = application(tmp_path, source, lambda state: {'claims': [
        {**verdict(i, ['e0']), 'scope_status': 'out_of_scope', 'scope_note': '合成题外判定。'}
        for i in range(len(state['review_packet']['claims']))]})
    with TestClient(app) as client:
        app.state.flow.tools.execute = lambda *args: {'success': True, 'documents': [source]}
        headers = login(client)
        result = ask(client, headers, session(client, headers), '合成核心问题').json()
        assert result['result_status'] == 'partial' and result['safe_error_code'] == 'ANSWER_SCOPE_INCOMPLETE'
        assert result['retained_claim_count'] == 0 and result['scope_omitted_claim_count'] == 2
        assert '证据不足' not in result['answer']


def test_false_gap_can_be_replaced_from_evidence_while_supported_core_survives(tmp_path, synthetic_source):
    _, source = synthetic_source
    seen = []
    def review(state):
        seen.append(state['review_packet'])
        return {'claims': [verdict(i, ['e0'], status='contradicted' if len(seen) == 1 and i == 0 else 'supported')
            for i in range(len(state['review_packet']['claims']))]}
    app = application(tmp_path, source, review)
    app.state.model.decide = lambda state: ({'answer': '原文没有合成分级。另一个核心回答。', 'source_ids': ['s0']}
        if state['observations'] else {'tool_calls': [call(query='synthetic source')]})
    app.state.model.rewrite_review = lambda state: {'claims': [
        {'text': '合成甲级为A。', 'draft_indices': [0]}, {'text': '合成乙级为B。', 'draft_indices': [0]}]}
    with TestClient(app) as client:
        app.state.flow.tools.execute = lambda *args: {'success': True, 'documents': [source]}
        headers = login(client)
        result = ask(client, headers, session(client, headers), '合成分级及另一个核心问题？').json()
        assert result['result_status'] == 'completed' and result['review_rewrite_count'] == 1
        assert '合成甲级为A。合成乙级为B。另一个核心回答。' in result['answer']
        assert '原文没有' not in result['answer'] and len(seen) == 2
        assert all(result['answer'][c['final_start']:c['final_end']] == c['text']
            for c in result['claim_reviews'] if c['final_start'] is not None)


def test_exhausted_quote_repair_keeps_valid_core_and_records_local_rejection(tmp_path, synthetic_source):
    _, source = synthetic_source
    def review(state):
        e = state['review_packet']['evidence'][0]
        return {'claims': [{**verdict(i, [e['id']]), 'support_quotes': [
            {'evidence_id': e['id'], 'quote': e['quote'] if i == 0 else 'Invalid copied quotation.'}]}
            for i in range(len(state['review_packet']['claims']))]}
    app = application(tmp_path, source, review)
    with TestClient(app) as client:
        app.state.flow.tools.execute = lambda *args: {'success': True, 'documents': [source]}
        headers = login(client)
        result = ask(client, headers, session(client, headers), '合成问题').json()
        assert result['result_status'] == 'partial' and result['safe_error_code'] == 'REVIEW_SUPPORT_INCOMPLETE'
        assert '这是合成断言。' in result['answer'] and '另一条合成断言。' not in result['answer']
        assert result['reviewer_status'] == 'completed' and result['omitted_claim_count'] == 1
        attempts = result['review_trace'][0]['attempts']
        assert [a['status'] for a in attempts] == ['failed', 'completed_with_rejections']
        assert attempts[-1]['rejected_claims'] == [{'claim_index': 1,
            'global_claim_index': 1, 'code': 'REVIEW_WITNESS_INVALID'}]
        assert client.get('/runs/'+result['run_id'],headers=headers).json() == result
