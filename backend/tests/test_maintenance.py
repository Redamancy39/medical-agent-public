import json
from threading import Event

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import create_app
from app.maintenance import preferences
from app.models import MemoryFact, MemoryJob, SessionSummary
from app.providers import ProviderError
from test_api import app, client, login, session, settings
from test_graph import ask


def finish(app):
    if app.state.flow.maintenance.future:
        app.state.flow.maintenance.future.result(timeout=5)


def test_whitelist_does_not_promote_questions_diagnoses_or_assistant_guesses():
    assert preferences('解释肺炎治疗') == {}
    assert preferences('我希望你判断是不是肺炎') == {}
    assert preferences('我偏好中文和简洁的回答') == {
        'answer_language': '用户偏好回答语言：中文', 'answer_style': '用户偏好回答风格：简洁'}
    assert preferences('纠正一下，我偏好英文回答')['answer_language'].endswith('英文')
    assert preferences('我是研究生')['occupation'] == '用户明确背景：研究生'


def test_eleven_turn_summary_window_and_original_history(client, app):
    headers = login(client)
    sid = session(client, headers)
    for i in range(10):
        assert ask(client, headers, sid, f'合成问题{i}：此事项尚未解决').json()['result_status'] == 'completed'
    finish(app)
    assert client.get(f'/sessions/{sid}/summary', headers=headers).json()['status'] == 'empty'
    result = ask(client, headers, sid, '合成问题10').json()
    finish(app)
    summary = client.get(f'/sessions/{sid}/summary', headers=headers).json()
    assert summary['status'] == 'ready' and summary['covered_until_seq'] == 2 and summary['version'] == 1
    assert '尚未解决' in summary['content']
    assert len(client.get(f'/sessions/{sid}/messages', headers=headers).json()['items']) == 22
    last = ask(client, headers, sid, '当前问题只出现一次').json()
    state = app.state.flow.snapshot(last['run_id']).values
    assert state['context']['summary']['covered_until_seq'] == 2
    assert sum(m['role'] == 'user' for m in state['context']['history']) == 10
    assert sum(m.get('content') == '当前问题只出现一次' for m in state['messages']) == 1


def test_preference_persists_corrects_deletes_and_does_not_resurrect(settings):
    application = create_app(settings)
    with TestClient(application) as first:
        headers = login(first)
        sid = session(first, headers)
        ask(first, headers, sid, '我偏好中文回答')
        finish(application)
        rows = first.get('/memories', headers=headers).json()['items']
        assert len(rows) == 1 and rows[0]['synced_version'] == 1
    restarted = create_app(settings)
    with TestClient(restarted) as client:
        ask(client, headers, sid, '纠正一下，我偏好英文回答')
        finish(restarted)
        fact = client.get('/memories', headers=headers).json()['items'][0]
        assert fact['version'] == fact['synced_version'] == 2 and fact['content'].endswith('英文')
        result = ask(client, headers, sid, '读取我的偏好').json()
        memories = restarted.state.flow.snapshot(result['run_id']).values['context']['memories']
        assert len(memories) == 1 and memories[0]['content'].endswith('英文')
        assert client.post('/memories/' + fact['id'], headers=headers, json={'operation': 'delete'}).status_code == 200
        finish(restarted)
        result = ask(client, headers, sid, '重新读取我的偏好').json()
        assert restarted.state.flow.snapshot(result['run_id']).values['context']['memories'] == []
        assert client.get('/memories', headers=headers).json()['items'][0]['status'] == 'deleted'
        assert len(client.get(f'/sessions/{sid}/messages', headers=headers).json()['items']) == 8


def test_memory_failure_never_discards_saved_answer(client, app):
    app.state.flow.memory.add = lambda *args: (_ for _ in ()).throw(ProviderError('RATE_LIMITED'))
    headers = login(client)
    sid = session(client, headers)
    result = ask(client, headers, sid, '我偏好中文回答').json()
    finish(app)
    saved = client.get('/runs/' + result['run_id'], headers=headers).json()
    assert saved['answer'] == result['answer'] and saved['result_status'] == 'completed'
    assert saved['memory_write_status'] == 'failed' and saved['maintenance_error_code'] == 'RATE_LIMITED'
    assert len(client.get(f'/sessions/{sid}/messages', headers=headers).json()['items']) == 2


def test_unknown_add_reconciles_without_duplicate_write(client, app):
    memory = app.state.flow.memory
    original = memory.add
    count = []

    def ambiguous(*args):
        count.append(1)
        original(*args)
        raise ProviderError('REMOTE_TIMEOUT')

    memory.add = ambiguous
    headers = login(client)
    ask(client, headers, session(client, headers), '我偏好中文回答')
    finish(app)
    assert client.get('/maintenance/jobs', headers=headers).json()['items'][0]['status'] == 'uncertain'
    client.post('/maintenance/retry', headers=headers)
    assert count == [1]
    fact = client.get('/memories', headers=headers).json()['items'][0]
    assert fact['synced_version'] == 1
    assert client.get('/maintenance/jobs', headers=headers).json()['items'][0]['status'] == 'done'


def test_unknown_add_with_no_evidence_is_not_blindly_repeated(client, app):
    count = []
    app.state.flow.memory.add = lambda *args: (count.append(1), (_ for _ in ()).throw(ProviderError('REMOTE_TIMEOUT')))[1]
    headers = login(client)
    ask(client, headers, session(client, headers), '我偏好中文回答')
    finish(app)
    client.post('/maintenance/retry', headers=headers)
    assert count == [1] and client.get('/maintenance/jobs', headers=headers).json()['items'][0]['status'] == 'uncertain'


def test_pending_async_add_is_not_declared_done(client, app):
    app.state.flow.memory.add = lambda *args: {'status': 'pending', 'event_id': '00000000-0000-0000-0000-000000000001'}
    app.state.flow.memory.event = lambda *args: {'status': 'PENDING'}
    headers = login(client)
    result = ask(client, headers, session(client, headers), '我偏好中文回答').json()
    finish(app)
    client.post('/maintenance/retry', headers=headers)
    assert client.get('/runs/' + result['run_id'], headers=headers).json()['memory_write_status'] == 'awaiting_remote'
    assert client.get('/memories', headers=headers).json()['items'][0]['synced_version'] == 0


def test_correction_while_add_in_flight_cleans_only_stale_fixture(client, app):
    entered, release = Event(), Event()
    memory = app.state.flow.memory
    original = memory.add

    def delayed(*args):
        if args[1].endswith('中文'):
            entered.set()
            release.wait(4)
        return original(*args)

    memory.add = delayed
    headers = login(client)
    try:
        ask(client, headers, session(client, headers), '我偏好中文回答')
        assert entered.wait(2)
        fact = client.get('/memories', headers=headers).json()['items'][0]
        client.post('/memories/' + fact['id'], headers=headers,
                    json={'operation': 'update', 'content': '用户偏好回答语言：英文'})
        release.set()
        finish(app)
        updated = client.get('/memories', headers=headers).json()['items'][0]
        assert updated['synced_version'] == updated['version'] == 2
        user_id = client.get('/auth/me', headers=headers).json()['id']
        rows = memory.list_scoped(user_id)
        assert len(rows) == 1 and rows[0]['content'].endswith('英文')
    finally:
        release.set()


def test_summary_failure_keeps_history_and_can_retry(client, app):
    app.state.model.summarize = lambda *args: {'content': ''}
    headers = login(client)
    sid = session(client, headers)
    for i in range(11):
        assert ask(client, headers, sid, str(i)).json()['result_status'] == 'completed'
    finish(app)
    assert client.get(f'/sessions/{sid}/summary', headers=headers).json()['status'] == 'empty'
    assert client.get('/maintenance/jobs', headers=headers).json()['items'][0]['safe_error_code'] == 'SUMMARY_INVALID'
    app.state.model.summarize = lambda *args: {'content': '合成摘要，待解决事项保留。'}
    client.post('/maintenance/retry', headers=headers)
    assert client.get(f'/sessions/{sid}/summary', headers=headers).json()['covered_until_seq'] == 2
    assert len(client.get(f'/sessions/{sid}/messages', headers=headers).json()['items']) == 22


def test_maintenance_api_user_isolation_and_validation(client, app):
    alice, bob = login(client), login(client, 'bob')
    sid = session(client, alice)
    ask(client, alice, sid, '我偏好中文回答')
    finish(app)
    fact = client.get('/memories', headers=alice).json()['items'][0]
    assert client.get('/memories', headers=bob).json()['items'] == []
    assert client.get('/maintenance/jobs', headers=bob).json()['items'] == []
    assert client.get(f'/sessions/{sid}/summary', headers=bob).status_code == 404
    assert client.post('/memories/' + fact['id'], headers=bob, json={'operation': 'delete'}).status_code == 404
    assert client.post('/memories/' + fact['id'], headers=alice, json={'operation': 'update'}).status_code == 422
    assert client.post('/memories/' + fact['id'], headers=alice, json={'operation': 'update', 'content': '不属于语言偏好的内容'}).status_code == 422


def test_same_preference_and_request_replay_do_not_add_twice(client, app):
    headers = login(client)
    sid = session(client, headers)
    first = ask(client, headers, sid, '我偏好中文回答').json()
    client.post(f'/sessions/{sid}/chat', headers=headers, json={'question': '我偏好中文回答', 'request_id': first['request_id']})
    ask(client, headers, sid, '我偏好中文回答')
    finish(app)
    assert len(client.get('/maintenance/jobs', headers=headers).json()['items']) == 1
    assert len(client.get('/memories', headers=headers).json()['items']) == 1


def test_negated_preference_is_not_stored_as_positive():
    assert preferences('请记住，我不喜欢中文回答')['answer_language'].endswith('避免中文')
    assert preferences('我希望你解释中文论文') == {}


def test_summary_version_conflict_does_not_overwrite_newer_state(client, app):
    headers = login(client)
    sid = session(client, headers)
    user_id = client.get('/auth/me', headers=headers).json()['id']

    def competing_update(*args):
        with app.state.store.sessions.begin() as db:
            db.add(SessionSummary(session_id=sid, user_id=user_id, version=1, status='invalidated', content=''))
        return {'content': '不应提交的旧版本摘要'}

    app.state.model.summarize = competing_update
    for i in range(11):
        ask(client, headers, sid, str(i))
    finish(app)
    summary = client.get(f'/sessions/{sid}/summary', headers=headers).json()
    assert summary['version'] == 1 and summary['content'] == '' and summary['covered_until_seq'] == 0
    assert client.get('/maintenance/jobs', headers=headers).json()['items'][0]['safe_error_code'] == 'SUMMARY_VERSION_CONFLICT'


def test_deleted_preference_invalidates_summary_and_blocks_old_messages(client, app):
    headers = login(client)
    sid = session(client, headers)
    ask(client, headers, sid, '我偏好中文回答')
    for i in range(10):
        ask(client, headers, sid, str(i))
    finish(app)
    fact = client.get('/memories', headers=headers).json()['items'][0]
    assert client.get(f'/sessions/{sid}/summary', headers=headers).json()['status'] == 'ready'
    client.post('/memories/' + fact['id'], headers=headers, json={'operation': 'delete'})
    finish(app)
    assert client.get(f'/sessions/{sid}/summary', headers=headers).json()['status'] == 'invalidated'
    last = ask(client, headers, sid, '后续普通问题').json()
    finish(app)
    summary = client.get(f'/sessions/{sid}/summary', headers=headers).json()
    assert '我偏好中文' not in summary['content']
    assert app.state.flow.snapshot(last['run_id']).values['context']['memories'] == []


def test_deleted_preference_can_be_explicitly_restored(client, app):
    headers = login(client)
    sid = session(client, headers)
    ask(client, headers, sid, '我偏好中文回答')
    finish(app)
    fact = client.get('/memories', headers=headers).json()['items'][0]
    client.post('/memories/' + fact['id'], headers=headers, json={'operation': 'delete'})
    finish(app)
    client.post('/memories/' + fact['id'], headers=headers, json={'operation': 'update', 'content': fact['content']})
    finish(app)
    restored = client.get('/memories', headers=headers).json()['items'][0]
    assert restored['status'] == 'active' and restored['version'] == restored['synced_version'] == 3
    result = ask(client, headers, sid, '读取偏好').json()
    assert app.state.flow.snapshot(result['run_id']).values['context']['memories'][0]['content'] == fact['content']


def test_deleted_remote_cache_without_metadata_cannot_resurrect(client, app):
    headers = login(client)
    sid = session(client, headers)
    ask(client, headers, sid, '我偏好中文回答')
    finish(app)
    user_id = client.get('/auth/me', headers=headers).json()['id']
    old = app.state.flow.memory.list_scoped(user_id)[0]
    fact = client.get('/memories', headers=headers).json()['items'][0]
    client.post('/memories/' + fact['id'], headers=headers, json={'operation': 'delete'})
    finish(app)
    app.state.flow.memory.search = lambda *args: [{'id': old['id'], 'content': old['content']}]
    result = ask(client, headers, sid, '我的偏好是什么').json()
    assert app.state.flow.snapshot(result['run_id']).values['context']['memories'] == []
