import json
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import Store
from app.main import create_app
from app.models import ProviderCall
from app.providers import DeepSeekModel, Gateway, Mem0Memory, ProviderError, PubMedSearch
from app.agent import FakeTools
from test_api import login, session, settings
from test_graph import ask


def gateway(settings, handler):
    store = Store(settings.database_path)
    store.initialize()
    return Gateway(store, settings, httpx.MockTransport(handler))


@pytest.mark.parametrize('status,code', [(401, 'AUTH_FAILED'), (402, 'BALANCE_EXHAUSTED'), (429, 'RATE_LIMITED'), (503, 'UPSTREAM_ERROR')])
def test_provider_fault_codes_and_journal_hide_raw_error(settings, status, code):
    client = gateway(settings, lambda r: httpx.Response(status, json={'error': 'secret-value-never-return'}))
    try:
        with pytest.raises(ProviderError) as error:
            client.request('deepseek', 'test', 'POST', 'https://api.deepseek.com/chat/completions', key='private-test-key')
        assert str(error.value) == code
        with client.store.sessions() as db:
            row = db.scalar(select(ProviderCall))
            assert row.safe_error_code == code and row.http_status == status and row.elapsed_seconds >= 0
    finally:
        client.close()


def test_global_cloud_budget_and_timeout(settings):
    settings = settings.model_copy(update={'cloud_model_request_limit': 1})
    client = gateway(settings, lambda r: (_ for _ in ()).throw(httpx.ReadTimeout('private-upstream-message')))
    try:
        with pytest.raises(ProviderError, match='REMOTE_TIMEOUT'):
            client.request('deepseek', 'test', 'POST', 'https://api.deepseek.com/chat/completions')
        with pytest.raises(ProviderError, match='CLOUD_BUDGET_EXCEEDED'):
            client.request('deepseek', 'test', 'POST', 'https://api.deepseek.com/chat/completions')
        assert client.counts['deepseek'] == 1
    finally:
        client.close()


def test_native_tool_call_json_continuation_through_api(settings):
    settings = settings.model_copy(update={'deepseek_enabled': True, 'mem0_enabled': True,
                                          'deepseek_api_key': SecretStr('test-key'), 'mem0_api_key': SecretStr('test-mem0-key')})
    bodies = []

    def handler(request):
        body = json.loads(request.content)
        if request.url.host == 'api.mem0.ai':
            assert body['filters']['user_id'].startswith('medical-agent-')
            return httpx.Response(200, json={'results': []})
        bodies.append(body)
        assert sum(m['role'] == 'system' for m in body['messages']) == 1
        if len(bodies) == 1:
            message = {'role': 'assistant', 'content': json.dumps({'tasks': [{'task_id': 'a', 'agent_id': 'research_agent',
                'description': '检索合成样本', 'require_sources': True}]})}
        elif len(bodies) == 2:
            message = {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'call-1', 'type': 'function',
                'function': {'name': 'search_knowledge', 'arguments': '{"query":"合成样本"}'}}]}
        else:
            assert any(m.get('tool_call_id') == 'call-1' for m in body['messages'])
            message = {'role': 'assistant', 'content': '{"answer":"有引用的合成回答","source_ids":["demo-sop-1"]}'}
        return httpx.Response(200, json={'choices': [{'message': message, 'finish_reason': 'stop'}],
                                       'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}})

    application = create_app(settings, transport=httpx.MockTransport(handler))
    with TestClient(application) as client:
        application.state.flow.tools = FakeTools()
        headers = login(client)
        result = ask(client, headers, session(client, headers), '检索合成样本').json()
        assert result['mode'] == 'cloud_real' and result['result_status'] == 'completed'
        assert result['model_calls'] == 3 and result['tool_calls'] == 1
        assert result['context_details']['memory_status'] == 'empty'
        calls = client.get('/runs/' + result['run_id'] + '/providers', headers=headers).json()['items']
        assert len(calls) == 4 and sum(r['usage'].get('total_tokens', 0) for r in calls) == 45
        assert all(body['thinking'] == {'type': 'disabled'} for body in bodies)
        bob = login(client, 'bob')
        assert client.get('/runs/' + result['run_id'] + '/providers', headers=bob).status_code == 404


def test_memory_read_failure_is_distinct_from_no_match(settings):
    settings = settings.model_copy(update={'mem0_enabled': True, 'mem0_api_key': SecretStr('test-key')})
    application = create_app(settings, transport=httpx.MockTransport(lambda r: httpx.Response(503, json={'error': 'hidden'})))
    with TestClient(application) as client:
        headers = login(client)
        result = ask(client, headers, session(client, headers), '你好').json()
        assert result['result_status'] == 'completed' and result['context_details']['memory_status'] == 'failed'
        assert result['context_details']['memory_error_code'] == 'UPSTREAM_ERROR'


def test_mem0_filters_crud_and_wrong_scope_response(settings):
    owner, memory_id = str(uuid4()), str(uuid4())
    requests = []

    def handler(request):
        requests.append(request)
        if request.method == 'PUT' or request.method == 'DELETE':
            return httpx.Response(200, json={'message': 'ok'})
        return httpx.Response(200, json={'results': [{'id': memory_id, 'memory': '中文偏好', 'user_id': 'wrong-scope'}]})

    gw = gateway(settings, handler)
    adapter = Mem0Memory(gw, settings.model_copy(update={'mem0_api_key': SecretStr('test-key')}))
    try:
        with pytest.raises(ProviderError, match='MEMORY_RESPONSE_INVALID'):
            adapter.search(owner, '偏好')
        assert json.loads(requests[0].content)['filters'] == {'user_id': adapter.scope(owner)}
        adapter.update(owner, memory_id, '英文偏好', {'version': 2})
        adapter.delete(owner, memory_id)
        assert requests[-1].url.params['delete_linked'] == 'false'
    finally:
        gw.close()


def test_pubmed_two_request_budget_and_metadata_provenance(settings):
    seen = []

    def handler(request):
        seen.append(request)
        if request.url.path.endswith('esearch.fcgi'):
            return httpx.Response(200, json={'esearchresult': {'idlist': ['123']}})
        return httpx.Response(200, json={'result': {'123': {'title': 'Synthetic index fixture', 'pubdate': '2026'}}})

    gw = gateway(settings, handler)
    try:
        documents = PubMedSearch(gw).search('biobanking', 3)
        assert len(seen) == 2 and documents[0]['content_kind'] == 'search_metadata'
        assert documents[0]['verified'] is False and documents[0]['url'] == 'https://pubmed.ncbi.nlm.nih.gov/123/'
    finally:
        gw.close()


def test_malformed_plan_is_not_silently_fallback(settings):
    # Isolate failure without repair; bounded repair is covered by the lead-contract tests.
    settings = settings.model_copy(update={'deepseek_enabled': True, 'deepseek_api_key': SecretStr('test-key'),
        'schema_repair_limit': 0})
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json={'choices': [
        {'finish_reason': 'stop', 'message': {'content': 'not-json'}}]}))
    with TestClient(create_app(settings, transport=transport)) as client:
        headers = login(client)
        result = ask(client, headers, session(client, headers), '检索').json()
        assert result['result_status'] == 'failed' and result['safe_error_code'] == 'MODEL_JSON_INVALID'
        assert result['plan_status'] == 'failed' and result['model_calls'] == 1


def test_one_schema_repair_is_counted_and_never_bypasses_global_budget(settings):
    settings = settings.model_copy(update={'deepseek_enabled': True, 'deepseek_api_key': SecretStr('test-key'),
                                          'schema_repair_limit': 1})
    count = []

    def handler(request):
        count.append(1)
        content = '{"response":"ack"}' if len(count) % 2 else '{"answer":"ack","source_ids":[]}'
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {'content': content}}]})

    application = create_app(settings, transport=httpx.MockTransport(handler))
    with TestClient(application) as client:
        headers = login(client)
        result = ask(client, headers, session(client, headers)).json()
        assert result['result_status'] == 'completed' and result['model_calls'] == 2
        assert result['schema_repair_count'] == 1 and result['provider_contract_details']['extra_field_count'] == 1
        application.state.flow.settings = settings.model_copy(update={'max_model_calls': 1})
        result = ask(client, headers, session(client, headers)).json()
        assert result['result_status'] == 'failed' and result['model_calls'] == 1 and len(count) == 3
        assert result['safe_error_code'] == 'MODEL_BUDGET_EXCEEDED'


def test_native_final_response_has_no_external_tool_side_effect(settings):
    settings = settings.model_copy(update={'deepseek_enabled': True, 'deepseek_api_key': SecretStr('test-key')})

    def handler(request):
        body = json.loads(request.content)
        assert body['tool_choice'] == 'required' and 'response_format' not in body
        assert any(t['function']['name'] == 'final_response' for t in body['tools'])
        return httpx.Response(200, json={'choices': [{'finish_reason': 'tool_calls', 'message': {
            'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'final-1', 'type': 'function',
                'function': {'name': 'final_response', 'arguments': '{"answer":"ack","source_ids":[]}'}}]}}]})

    with TestClient(create_app(settings, transport=httpx.MockTransport(handler))) as client:
        headers = login(client)
        result = ask(client, headers, session(client, headers)).json()
        assert result['result_status'] == 'completed' and result['model_calls'] == 1 and result['tool_calls'] == 0
