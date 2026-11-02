import json

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.main import create_app
from test_api import settings, login, session
from test_graph import ask
from test_multitask import task


def test_invalid_plan_has_one_counted_repair_and_safe_diagnostics(settings):
    application = create_app(settings.model_copy(update={'schema_repair_limit': 1, 'maintenance_enabled': False}))
    seen = []
    def plan(state):
        seen.append(state)
        if len(seen) == 1:
            return {'tasks': [], 'unexpected_sensitive_key': 'do-not-log-this-value'}
        assert state['contract_repair']['stage'] == 'plan'
        return {'reason': '只需一个解释任务', 'tasks': [task('explain')]}
    application.state.model.plan = plan
    with TestClient(application) as client:
        headers = login(client)
        result = ask(client, headers, session(client, headers), '研究问题').json()
        assert result['result_status'] == 'completed' and result['model_calls'] == 3
        assert result['contract_repair_counts'] == {'plan': 1} and result['schema_repair_count'] == 1
        assert result['contract_diagnostics'][0]['stage'] == 'plan'
        assert 'do-not-log-this-value' not in json.dumps(result)
        assert 'unexpected_sensitive_key' not in json.dumps(result['contract_diagnostics'])


def test_invalid_plan_repair_is_bounded_and_does_not_fallback(settings):
    application = create_app(settings.model_copy(update={'schema_repair_limit': 1, 'maintenance_enabled': False}))
    calls = []
    application.state.model.plan = lambda s: (calls.append(1), {'tasks': [task('bad', dependencies=['missing'])]})[1]
    application.state.model.decide = lambda s: pytest.fail('invalid plan must not dispatch')
    with TestClient(application) as client:
        headers = login(client)
        result = ask(client, headers, session(client, headers), '研究问题').json()
        assert result['safe_error_code'] == 'PLAN_INVALID' and result['plan_status'] == 'failed'
        assert len(calls) == result['model_calls'] == 2
        assert result['contract_diagnostics'][-1]['validation'][0]['type'] == 'plan_dependency_missing'


def test_plan_repair_never_bypasses_global_budget(settings):
    application = create_app(settings.model_copy(update={'schema_repair_limit': 1, 'max_model_calls': 1,
        'maintenance_enabled': False}))
    calls = []
    application.state.model.plan = lambda s: (calls.append(1), {'tasks': []})[1]
    with TestClient(application) as client:
        headers = login(client)
        result = ask(client, headers, session(client, headers), '研究问题').json()
        assert result['safe_error_code'] == 'MODEL_BUDGET_EXCEEDED' and len(calls) == 1
        assert result['model_calls'] == 1


def test_synthesis_task_coverage_has_one_repair_without_repeating_workers(settings):
    application = create_app(settings.model_copy(update={'schema_repair_limit': 1, 'maintenance_enabled': False}))
    application.state.model.plan = lambda s: {'tasks': [task('a'), task('b')]}
    workers, summaries = [], []
    application.state.model.decide = lambda s: (workers.append(s['task_id']), {'answer': s['task_id']})[1]
    def synthesize(state):
        summaries.append(1)
        if len(summaries) == 1: return {'answer': '遗漏', 'task_ids': ['a'], 'source_ids': []}
        assert state['contract_repair']['stage'] == 'synthesize'
        return {'answer': '完整汇总', 'task_ids': ['a', 'b'], 'source_ids': []}
    application.state.model.synthesize = synthesize
    with TestClient(application) as client:
        headers = login(client)
        result = ask(client, headers, session(client, headers), '多任务').json()
        assert result['result_status'] == 'completed' and result['answer'] == '完整汇总'
        assert sorted(workers) == ['a', 'b'] and len(summaries) == 2 and result['model_calls'] == 5
        diagnostic = result['contract_diagnostics'][0]
        assert diagnostic['code'] == 'SYNTHESIS_TASK_COVERAGE_INVALID' and diagnostic['missing_task_count'] == 1


def test_synthesis_invented_sources_stay_partial_after_bounded_repair(settings):
    application = create_app(settings.model_copy(update={'schema_repair_limit': 1, 'maintenance_enabled': False}))
    application.state.model.plan = lambda s: {'tasks': [task('a'), task('b')]}
    application.state.model.synthesize = lambda s: {'answer': 'invented-summary', 'task_ids': ['a', 'b'], 'source_ids': ['absent']}
    with TestClient(application) as client:
        headers = login(client)
        result = ask(client, headers, session(client, headers), '多任务').json()
        assert result['result_status'] == 'partial' and result['safe_error_code'] == 'SYNTHESIS_INVALID'
        assert result['completed_task_count'] == 2 and 'invented-summary' not in result['answer']
        assert result['contract_diagnostics'][-1]['unknown_source_count'] == 1
        assert result['contract_repair_counts'] == {'synthesize': 1}


def test_provider_plan_uses_single_native_submit_contract(settings):
    config = settings.model_copy(update={'deepseek_enabled': True, 'deepseek_api_key': SecretStr('synthetic-key'),
        'knowledge_profile': 'medical', 'maintenance_enabled': False, 'medical_reviewer_enabled': False})
    seen = []
    def handler(request):
        body = json.loads(request.content)
        seen.append(body)
        functions = [t['function']['name'] for t in body['tools']]
        if len(seen) == 1:
            assert functions == ['submit_plan'] and body['tool_choice'] == 'required'
            assert '$ref' not in json.dumps(body['tools'])
            output = {'tasks': [task('one')], 'reason': '一个目标'}
            name = 'submit_plan'
        else:
            name, output = 'final_response', {'answer': 'unknown范围说明', 'source_ids': []}
        return httpx.Response(200, json={'choices': [{'finish_reason': 'tool_calls', 'message': {
            'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'response', 'type': 'function',
                'function': {'name': name, 'arguments': json.dumps(output)}}]}}]})
    with TestClient(create_app(config, transport=httpx.MockTransport(handler))) as client:
        headers = login(client)
        result = ask(client, headers, session(client, headers), '目前资料能回答什么？').json()
        assert result['result_status'] == 'completed' and result['plan_reason'] == '一个目标'


def test_each_lead_stage_has_its_own_bounded_repair(settings):
    application = create_app(settings.model_copy(update={'schema_repair_limit': 1, 'maintenance_enabled': False}))
    plans, summaries = [], []
    def plan(state):
        plans.append(1)
        return {'tasks': []} if len(plans) == 1 else {'tasks': [task('a'), task('b')]}
    def summarize(state):
        summaries.append(1)
        return {'answer': '完整', 'task_ids': ['a'] if len(summaries) == 1 else ['a', 'b'], 'source_ids': []}
    application.state.model.plan, application.state.model.synthesize = plan, summarize
    with TestClient(application) as client:
        headers = login(client)
        result = ask(client, headers, session(client, headers), '多任务').json()
        assert result['result_status'] == 'completed' and result['model_calls'] == 6
        assert result['schema_repair_count'] == 2 and result['contract_repair_counts'] == {'plan': 1, 'synthesize': 1}


def test_provider_failure_is_not_retried_as_format_error(settings):
    from app.providers import ProviderError
    application = create_app(settings.model_copy(update={'schema_repair_limit': 1, 'maintenance_enabled': False}))
    calls = []
    def plan(state):
        calls.append(1)
        raise ProviderError('AUTH_FAILED')
    application.state.model.plan = plan
    with TestClient(application) as client:
        headers = login(client)
        result = ask(client, headers, session(client, headers), '研究问题').json()
        assert result['safe_error_code'] == 'AUTH_FAILED' and len(calls) == 1
        assert result['schema_repair_count'] == 0 and result['contract_diagnostics'][0]['code'] == 'AUTH_FAILED'


def test_native_synthesis_schema_binds_exact_task_and_source_ids(settings):
    config = settings.model_copy(update={'deepseek_enabled': True, 'deepseek_api_key': SecretStr('synthetic-key'),
        'maintenance_enabled': False})
    summaries = []
    def handler(request):
        body = json.loads(request.content)
        functions = {t['function']['name']: t['function'] for t in body['tools']}
        if 'submit_plan' in functions:
            name = 'submit_plan'
            output = {'tasks': [task('a', 'research_agent', require_sources=True), task('b', 'research_agent', require_sources=True)]}
        elif 'submit_synthesis' in functions:
            summaries.append(1)
            props = functions['submit_synthesis']['parameters']['properties']
            assert set(props['task_ids']['items']['enum']) == {'a', 'b'}
            assert set(props['source_ids']['items']['enum']) == {'left', 'right'}
            assert props['source_ids']['minItems'] == props['source_ids']['maxItems'] == 2
            assert props['source_ids']['uniqueItems'] is True
            name, output = 'submit_synthesis', {'answer': '已综合两个任务', 'task_ids': ['a', 'b'], 'source_ids': ['left', 'right']}
        else:
            available = functions['final_response']['parameters']['properties']['source_ids']['items'].get('enum')
            if available:
                name, output = 'final_response', {'answer': '来源支持的合成测试说明', 'source_ids': available}
            else:
                name, output = 'search_knowledge', {'query': '合成资料'}
        return httpx.Response(200, json={'choices': [{'finish_reason': 'tool_calls', 'message': {
            'content': None, 'tool_calls': [{'id': 'native', 'type': 'function',
                'function': {'name': name, 'arguments': json.dumps(output)}}]}}]})
    application = create_app(config, transport=httpx.MockTransport(handler))
    with TestClient(application) as client:
        from app.agent import FakeTools
        application.state.flow.tools = FakeTools()
        application.state.flow.tools.execute = lambda name, args, s: {'success': True, 'documents': [
            {'id': 'left' if s['task_id'] == 'a' else 'right', 'source': 'synthetic', 'content': '合成测试资料', 'verified': False}]}
        headers = login(client)
        result = ask(client, headers, session(client, headers), '多任务').json()
        assert result['result_status'] == 'completed' and len(summaries) == 1
        assert {s['id'] for s in result['sources']} == {'left', 'right'}


def test_wrong_native_plan_function_has_one_safe_repair(settings):
    config = settings.model_copy(update={'deepseek_enabled': True, 'deepseek_api_key': SecretStr('synthetic-key'),
        'maintenance_enabled': False, 'schema_repair_limit': 1})
    seen = []
    def handler(request):
        body = json.loads(request.content); seen.append(body)
        if len(seen) <= 2:
            name = 'wrong_function' if len(seen) == 1 else 'submit_plan'
            output = {'tasks': [task('one')]}
        else:
            name, output = 'final_response', {'answer': '说明', 'source_ids': []}
        return httpx.Response(200, json={'choices': [{'finish_reason': 'tool_calls', 'message': {
            'content': None, 'tool_calls': [{'id': 'native', 'type': 'function',
                'function': {'name': name, 'arguments': json.dumps(output)}}]}}]})
    with TestClient(create_app(config, transport=httpx.MockTransport(handler))) as client:
        headers = login(client)
        result = ask(client, headers, session(client, headers), '研究问题').json()
        assert result['result_status'] == 'completed' and result['model_calls'] == len(seen) == 3
        assert result['contract_diagnostics'][0]['code'] == 'MODEL_STRUCTURED_CALL_INVALID'
        assert result['contract_repair_counts'] == {'plan': 1}
