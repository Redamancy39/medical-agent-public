"""Failure packets remain traceable without retaining arbitrary provider payloads."""
import json
import pytest
from fastapi.testclient import TestClient
from test_api import settings, login, session
from test_graph import ask
from test_realtime_reviewer import application, verdict, source
from app.medical_reviewer import build_packet, validate_review
from app.contracts import ContractViolation


def test_failed_second_batch_keeps_claims_attempts_and_global_index(settings):
    attempts = []
    def review(s):
        p = s['review_packet']; attempts.append(1)
        claims = [verdict(i, evidence_ids=[p['evidence'][0]['id']]) for i in range(len(p['claims']))]
        if len(attempts) > 1: claims[1] = verdict(1, kind='corpus_scope')
        return {'claims': claims}
    app = application(settings.model_copy(update={'schema_repair_limit': 1}), review)
    app.state.model.atomize = lambda s: {'claims': [
        {'text': '血糖升高。', 'draft_indices': [0 if i < 13 else 1]} for i in range(14)]}
    with TestClient(app) as client:
        app.state.flow.tools.execute = app.state.test_tools_execute
        headers = login(client)
        result = ask(client, headers, session(client, headers), '合成溯源测试').json()
        assert result['reviewer_status'] == 'failed' and result['model_calls'] == 7
        trace = result['review_trace'][0]
        assert len(trace['claims']) == 14 and trace['claims'][11]['text'] == '血糖升高。'
        assert [a['status'] for a in trace['attempts']] == ['completed', 'failed', 'failed']
        for attempt in trace['attempts'][1:]:
            assert attempt['diagnostic']['claim_index'] == 1
            assert attempt['diagnostic']['global_claim_index'] == 11
            assert attempt['judgments'][1]['kind'] == 'corpus_scope'
        assert client.get('/runs/'+result['run_id'], headers=headers).json()['review_trace'] == result['review_trace']
        other = login(client, 'other-user')
        assert client.get('/runs/'+result['run_id'], headers=other).status_code == 404


def test_malformed_provider_output_is_not_copied_into_trace(settings):
    app = application(settings, lambda s: {'private_key': 'arbitrary-provider-secret'})
    with TestClient(app) as client:
        app.state.flow.tools.execute = app.state.test_tools_execute
        headers = login(client)
        result = ask(client, headers, session(client, headers), '合成失败测试').json()
        encoded = json.dumps(result['review_trace'])
        assert 'private_key' not in encoded and 'arbitrary-provider-secret' not in encoded
        assert result['review_trace'][0]['attempts'][0]['status'] == 'failed'


def test_unknown_evidence_values_are_counted_without_copying_them(settings):
    app = application(settings, lambda s: {'claims': [
        verdict(evidence_ids=['arbitrary-provider-token']), verdict(1, status='unsupported')]})
    with TestClient(app) as client:
        app.state.flow.tools.execute = app.state.test_tools_execute
        headers = login(client)
        result = ask(client, headers, session(client, headers), '合成ID测试').json()
        attempt = result['review_trace'][0]['attempts'][0]
        assert attempt['judgments'][0]['evidence_ids'] == []
        assert attempt['judgments'][0]['unknown_evidence_count'] == 1
        assert attempt['diagnostic']['global_claim_index'] == 0
        assert 'arbitrary-provider-token' not in json.dumps(result['review_trace'])


def test_policy_boundary_represent_word_is_not_a_medical_assertion():
    packet = build_packet('test', '本内容不代表个体诊断或处方建议。', [])
    v = verdict(kind='project_behavior'); v['policy_rules'] = ['educational_scope']
    assert validate_review({'claims': [v]}, packet).claims[0].kind == 'project_behavior'


def test_mixed_policy_boundary_cannot_hide_medical_fact():
    packet = build_packet('test', '本内容不代表个人诊断建议，高血压通常无症状。', [source()])
    v = verdict(kind='project_behavior'); v['policy_rules'] = ['educational_scope']
    with pytest.raises(ContractViolation, match='CLASSIFICATION'):
        validate_review({'claims': [v]}, packet)


def test_risk_caution_from_m_draft_is_bound_to_real_policy():
    packet = build_packet('test', '有风险因素不等于已患病，也不代表已确诊。', [])
    v = verdict(kind='project_behavior'); v['policy_rules'] = ['educational_scope']
    assert validate_review({'claims': [v]}, packet).claims[0].support_status == 'supported'
    v['policy_rules'] = []
    with pytest.raises(ContractViolation, match='POLICY_REQUIRED'): validate_review({'claims': [v]}, packet)
    v['kind'] = 'corpus_scope'
    with pytest.raises(ContractViolation, match='POLICY_CLASSIFICATION'): validate_review({'claims': [v]}, packet)


def test_risk_assertion_does_not_get_policy_exception():
    packet = build_packet('test', '有风险因素代表一定患病。', [source()])
    v = verdict(kind='project_behavior'); v['policy_rules'] = ['educational_scope']
    with pytest.raises(ContractViolation, match='CLASSIFICATION'): validate_review({'claims': [v]}, packet)


def test_native_schema_prescribes_class_but_never_grants_support(settings):
    import httpx
    from pydantic import SecretStr
    from jsonschema import Draft202012Validator
    from app.providers import DeepSeekModel
    from test_providers import gateway
    packet = build_packet('test', '有风险因素不代表已确诊。血糖升高。', [source()])
    def handler(request):
        body = json.loads(request.content)
        schema = body['tools'][0]['function']['parameters']
        good = {'claims': [verdict(0, kind='project_behavior'), verdict(1, status='unsupported')]}
        good['claims'][0]['policy_rules'] = ['educational_scope']
        assert Draft202012Validator(schema).is_valid(good)
        bad = json.loads(json.dumps(good)); bad['claims'][1]['kind'] = 'corpus_scope'
        assert not Draft202012Validator(schema).is_valid(bad)
        assert 'accept' not in json.loads(body['messages'][1]['content'])
        return httpx.Response(200, json={'choices': [{'finish_reason':'tool_calls', 'message': {'tool_calls': [
            {'function': {'name': 'submit_review', 'arguments': json.dumps(good)}}]}}]})
    gw = gateway(settings, handler)
    try:
        raw = DeepSeekModel(gw, settings.model_copy(update={'deepseek_api_key': SecretStr('synthetic-key')})).review({'review_packet':packet})
        assert validate_review(raw,packet).claims[1].support_status == 'unsupported'
    finally: gw.close()


def test_native_schema_is_valid_when_batch_has_no_marker_requirements(settings):
    import httpx
    from pydantic import SecretStr
    from jsonschema import Draft202012Validator
    from app.providers import DeepSeekModel
    from test_providers import gateway
    packet = build_packet('test', 'UACR是一种检查。', [])
    def handler(request):
        schema = json.loads(request.content)['tools'][0]['function']['parameters']
        Draft202012Validator.check_schema(schema)
        raw = {'claims':[verdict(status='unsupported')]}
        return httpx.Response(200,json={'choices':[{'finish_reason':'tool_calls','message':{'tool_calls':[
            {'function':{'name':'submit_review','arguments':json.dumps(raw)}}]}}]})
    gw = gateway(settings, handler)
    try:
        raw=DeepSeekModel(gw,settings.model_copy(update={'deepseek_api_key':SecretStr('synthetic-key')})).review({'review_packet':packet})
        assert validate_review(raw,packet).claims[0].support_status=='unsupported'
    finally: gw.close()
