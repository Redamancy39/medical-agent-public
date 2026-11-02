"""Local HTTP smoke check. Creates synthetic accounts; never prints credentials."""
import json
import secrets
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4

BASE_URL = 'http://127.0.0.1:8010'
http = build_opener(ProxyHandler({}))


def call(path, body=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = Request(BASE_URL + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
    try:
        with http.open(request, timeout=10) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


def account():
    body = {'username': 'smoke_' + uuid4().hex[:12], 'password': secrets.token_urlsafe(24)}
    assert call('/auth/register', body)[0] == 201
    status, result = call('/auth/login', body)
    assert status == 200
    return result['access_token']


def main():
    assert call('/health')[1]['external_calls_enabled'] is False
    token = account()
    status, conversation = call('/sessions', {'title': '本地HTTP验收会话'}, token)
    assert status == 201
    session_id = conversation['id']
    body = {'question': '验证持久会话接口', 'request_id': str(uuid4())}
    status, first = call(f'/sessions/{session_id}/chat', body, token)
    assert status == 200 and first['result_status'] == 'completed'
    assert call(f'/sessions/{session_id}/chat', body, token)[1]['replayed'] is True
    assert len(call(f'/sessions/{session_id}/messages', token=token)[1]['items']) == 2
    status, multi = call(f'/sessions/{session_id}/chat', {'question': '三个专家研究样本登记', 'request_id': str(uuid4())}, token)
    assert status == 200 and multi['result_status'] == 'completed'
    assert multi['graph_version'] == 3 and multi['task_count'] == 3 and multi['distinct_agent_count'] == 3
    assert multi['model_calls'] == 6 and multi['tool_calls'] == 1
    assert multi['completed_task_count'] == 3 and multi['evidence_status'] == 'passed'
    assert call('/runs/' + first['run_id'], token=token)[1]['run_status'] == 'finished'
    other_token = account()
    assert call(f'/sessions/{session_id}/messages', token=other_token)[0] == 404
    assert call('/sessions', token=other_token)[1]['total'] == 0
    assert call('/openapi.json')[0] == 200
    print(json.dumps({'http_smoke': 'passed', 'mode': 'offline_fake', 'cloud_requests': 0}))


if __name__ == '__main__':
    main()
