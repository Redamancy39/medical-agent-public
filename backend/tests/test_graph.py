import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import create_app
from app.models import Message, Run
from test_api import app, client, login, session, settings


def ask(client, headers, sid, question='你好'):
    return client.post(f'/sessions/{sid}/chat', headers=headers,
                       json={'question': question, 'request_id': str(uuid4())})


def call(name='search_knowledge', **arguments):
    return {'id': str(uuid4()), 'name': name, 'arguments': arguments}


def test_direct_graph_and_events(client, app):
    headers = login(client)
    sid = session(client, headers)
    result = ask(client, headers, sid).json()
    assert result['result_status'] == 'completed'
    assert result['graph_version'] == 3 and result['checkpoint_id']
    assert result['plan_status'] == 'skipped'
    assert result['model_calls'] == 1 and result['tool_calls'] == 0
    stages = [x['stage'] for x in client.get('/runs/' + result['run_id'] + '/events', headers=headers).json()['items']]
    assert 'load_context' in stages and 'worker' in stages and 'persist_result' in stages
    assert app.state.flow.snapshot(result['run_id']).next == ()


def test_react_tool_protocol_and_sources(client, app):
    headers = login(client)
    result = ask(client, headers, session(client, headers), '检索研究项目资料').json()
    assert result['plan_status'] == 'completed'
    assert result['tool_calls'] == 1 and result['model_calls'] == 3
    assert result['sources'] and result['sources'][0]['verified'] is False
    state = app.state.flow.snapshot(result['run_id']).values
    requested = [x['id'] for m in state['messages'] for x in m.get('tool_calls', [])]
    returned = [m['tool_call_id'] for m in state['messages'] if m['role'] == 'tool']
    assert requested == returned


def test_ten_turn_context_does_not_duplicate_current_question(client, app):
    headers = login(client)
    sid = session(client, headers)
    for i in range(11):
        assert ask(client, headers, sid, f'历史问题{i}').status_code == 200
    result = ask(client, headers, sid, '当前问题').json()
    context = app.state.flow.snapshot(result['run_id']).values['context']
    assert len(context['history']) == 20
    assert context['history'][0]['content'] == '历史问题1'
    assert not any(m['content'] == '当前问题' for m in context['history'])
    assert context['older_history_omitted'] is True
    assert context['summary_status'] in ('ready', 'empty')
    assert len(client.get(f'/sessions/{sid}/messages', headers=headers).json()['items']) == 24


def test_invalid_tool_arguments_never_execute(client, app):
    headers = login(client)
    app.state.model.decide = lambda state: {'tool_calls': [call(query='资料', max_results=2.5)]}
    executions = []
    original = app.state.flow.tools.execute
    app.state.flow.tools.execute = lambda *args: (executions.append(args), original(*args))[1]
    result = ask(client, headers, session(client, headers)).json()
    assert result['safe_error_code'] == 'TOOL_ARGUMENTS_INVALID'
    assert result['result_status'] == 'failed' and executions == []


def test_unknown_tool_and_role_permissions(client, app):
    headers = login(client)
    app.state.model.decide = lambda state: {'tool_calls': [call('arbitrary_tool', query='x')]}
    result = ask(client, headers, session(client, headers)).json()
    assert result['safe_error_code'] == 'TOOL_NOT_ALLOWED' and result['tool_calls'] == 0
    app.state.model.decide = lambda state: {'tool_calls': [call('deep_research', query='x')]}
    result = ask(client, headers, session(client, headers)).json()
    assert result['safe_error_code'] == 'TOOL_NOT_ALLOWED'


def test_batch_budget_is_enforced_per_tool(client, app):
    headers = login(client)
    app.state.model.decide = lambda state: {'tool_calls': [call(query='x', max_results=1) for _ in range(3)]}
    result = ask(client, headers, session(client, headers), '检索资料').json()
    assert result['tool_calls'] == 2
    assert result['result_status'] == 'partial'
    assert result['safe_error_code'] == 'TOOL_BUDGET_EXCEEDED'
    assert len(result['sources']) == len({source['id'] for source in result['sources']})


def test_model_budget_and_empty_output(client, app):
    headers = login(client)
    app.state.model.decide = lambda state: {'answer': ''}
    result = ask(client, headers, session(client, headers)).json()
    assert result['result_status'] == 'failed' and result['safe_error_code'] == 'OUTPUT_INVALID'


def test_invalid_plan_is_not_silently_executed(client, app):
    headers = login(client)
    app.state.model.plan = lambda state: {'tasks': [{'agent_id': 'unknown', 'description': 'x'}]}
    result = ask(client, headers, session(client, headers), '研究这个问题').json()
    assert result['plan_status'] == 'failed' and result['safe_error_code'] == 'PLAN_INVALID'
    assert result['tool_calls'] == 0


def test_checkpoint_interrupt_restart_and_resume(settings):
    with TestClient(create_app(settings)) as first:
        headers = login(first)
        sid = session(first, headers)
        pending = ask(first, headers, sid, '请澄清我的请求').json()
        assert pending['run_status'] == 'awaiting_input'
        assert pending['checkpoint_id']
    with TestClient(create_app(settings)) as restarted:
        response = restarted.post('/runs/' + pending['run_id'] + '/resume', headers=headers,
                                  json={'checkpoint_id': pending['checkpoint_id'], 'clarification': '检索样本管理资料'})
        assert response.status_code == 200
        result = response.json()
        assert result['run_id'] == pending['run_id'] and result['result_status'] == 'completed'
        assert result['tool_calls'] == 1
        history = restarted.get(f'/sessions/{sid}/messages', headers=headers).json()['items']
        assert [m['role'] for m in history] == ['user', 'assistant', 'user', 'assistant']
        assert len(history) == 4


def test_cancel_waiting_run_and_cross_user_resume(client):
    alice, bob = login(client), login(client, 'bob')
    sid = session(client, alice)
    pending = ask(client, alice, sid, '请澄清我的请求').json()
    path = '/runs/' + pending['run_id']
    assert client.post(path + '/resume', headers=bob, json={'checkpoint_id': pending['checkpoint_id'], 'clarification': 'x'}).status_code == 404
    assert client.post(path + '/cancel', headers=bob).status_code == 404
    assert client.get(path + '/events', headers=bob).status_code == 404
    cancelled = client.post(path + '/cancel', headers=alice).json()
    assert cancelled['run_status'] == 'cancelled'
    assert client.get(path + '/events', headers=alice).json()['items'][-1]['stage'] == 'cancel'
    assert client.post(path + '/resume', headers=alice, json={'checkpoint_id': pending['checkpoint_id'], 'clarification': 'x'}).status_code == 409
    assert ask(client, alice, sid).json()['result_status'] == 'completed'


def test_stale_resume_and_no_new_turn_while_waiting(client):
    headers = login(client)
    sid = session(client, headers)
    pending = ask(client, headers, sid, '请澄清我的请求').json()
    assert ask(client, headers, sid).status_code == 409
    assert client.post('/runs/' + pending['run_id'] + '/resume', headers=headers,
                       json={'checkpoint_id': 'stale-checkpoint', 'clarification': '继续'}).status_code == 409


def test_cancel_running_does_not_hold_database_lock(client, app):
    headers = login(client)
    sid = session(client, headers)
    started, release = Event(), Event()
    def slow(state):
        started.set()
        release.wait(5)
        return {'answer': 'late response must not win cancellation'}
    app.state.model.decide = slow
    with ThreadPoolExecutor(max_workers=1) as pool:
        request = pool.submit(ask, client, headers, sid)
        assert started.wait(3)
        with app.state.store.sessions() as db:
            run_id = db.scalar(select(Run.id).where(Run.session_id == sid))
        cancelled = client.post('/runs/' + run_id + '/cancel', headers=headers)
        assert cancelled.status_code == 200
        release.set()
        result = request.result(timeout=5).json()
    assert result['run_status'] == 'cancelled'
    assert 'late response' not in result['answer']


def test_sqlite_checkpoints_are_not_just_memory(client, settings):
    headers = login(client)
    result = ask(client, headers, session(client, headers)).json()
    path = settings.database_path.with_name('checkpoints.db')
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM checkpoints WHERE thread_id=?', ('run:' + result['run_id'],)).fetchone()[0] > 0


def test_output_citations_are_checked(client, app):
    headers = login(client)
    app.state.model.decide = lambda state: {'answer': '已验证结论', 'source_ids': ['invented-source']}
    result = ask(client, headers, session(client, headers)).json()
    assert result['safe_error_code'] == 'OUTPUT_INVALID'


def test_fake_memory_is_scoped_by_server_identity(client, app):
    alice, bob = login(client), login(client, 'bob')
    alice_id = client.get('/auth/me', headers=alice).json()['id']
    app.state.flow.memory.items = [{'id': 'a-memory', 'user_id': alice_id, 'content': 'synthetic Alice preference'}]
    result = ask(client, bob, session(client, bob)).json()
    assert app.state.flow.snapshot(result['run_id']).values['context']['memories'] == []


def test_model_budget_includes_lead_and_worker(client, app):
    app.state.flow.settings = app.state.flow.settings.model_copy(update={'max_model_calls': 2})
    headers = login(client)
    result = ask(client, headers, session(client, headers), '检索资料').json()
    assert result['model_calls'] == 2 and result['tool_calls'] == 1
    assert result['safe_error_code'] == 'MODEL_BUDGET_EXCEEDED' and result['result_status'] == 'partial'


def test_step_timeout_returns_real_terminal_state(client, app):
    app.state.flow.settings = app.state.flow.settings.model_copy(update={'step_timeout_seconds': 0.1})
    release = Event()
    app.state.model.decide = lambda state: (release.wait(2), {'answer': 'late'})[1]
    headers = login(client)
    try:
        result = ask(client, headers, session(client, headers)).json()
        assert result['run_status'] == 'timed_out' and result['safe_error_code'] == 'STEP_TIMEOUT'
        assert result['model_calls'] == 1
    finally:
        release.set()


def test_mid_graph_checkpoint_resumes_without_replanning(settings):
    first_app = create_app(settings)
    with TestClient(first_app) as first:
        headers = login(first)
        sid = session(first, headers)
        flow = first_app.state.flow
        flow.graph = flow.build_graph().compile(checkpointer=flow.saver, interrupt_after=['plan'])
        pending = ask(first, headers, sid, '检索资料').json()
        assert pending['run_status'] == 'paused' and pending['model_calls'] == 1
    with TestClient(create_app(settings)) as restarted:
        result = restarted.post('/runs/' + pending['run_id'] + '/resume', headers=headers,
                                json={'checkpoint_id': pending['checkpoint_id']}).json()
        assert result['result_status'] == 'completed' and result['model_calls'] == 3
        assert len(restarted.get(f'/sessions/{sid}/messages', headers=headers).json()['items']) == 2


def test_repeated_resume_does_not_add_messages(client):
    headers = login(client)
    sid = session(client, headers)
    pending = ask(client, headers, sid, '请澄清').json()
    body = {'checkpoint_id': pending['checkpoint_id'], 'clarification': '检索资料'}
    first = client.post('/runs/' + pending['run_id'] + '/resume', headers=headers, json=body)
    repeat = client.post('/runs/' + pending['run_id'] + '/resume', headers=headers, json=body)
    assert first.status_code == repeat.status_code == 200
    assert repeat.json()['replayed'] is True
    assert len(client.get(f'/sessions/{sid}/messages', headers=headers).json()['items']) == 4


def test_resume_submission_survives_execution_interruption(client, app):
    headers = login(client)
    sid = session(client, headers)
    pending = ask(client, headers, sid, '请澄清').json()
    body = {'checkpoint_id': pending['checkpoint_id'], 'clarification': '检索资料'}
    original = app.state.flow._execute
    app.state.flow._execute = lambda *args: (_ for _ in ()).throw(RuntimeError('synthetic interruption'))
    assert client.post('/runs/' + pending['run_id'] + '/resume', headers=headers, json=body).status_code == 500
    app.state.flow._execute = original
    with app.state.store.sessions.begin() as db:
        run = db.get(Run, pending['run_id'])
        metadata = json.loads(run.details_json)
        metadata['lease_until'] = 0  # Simulate the crashed worker lease expiring.
        run.details_json = json.dumps(metadata)
    result = client.post('/runs/' + pending['run_id'] + '/resume', headers=headers, json=body)
    assert result.status_code == 200 and result.json()['result_status'] == 'completed'
    assert len(client.get(f'/sessions/{sid}/messages', headers=headers).json()['items']) == 4


def test_legacy_batch_a_database_upgrade_preserves_records(settings):
    from app.security import HASHER
    from app.models import timestamp
    user_id, sid, rid, request_id = [str(uuid4()) for _ in range(4)]
    now = timestamp()
    with sqlite3.connect(settings.database_path) as db:
        db.executescript('''
            CREATE TABLE users (id TEXT PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT, active BOOLEAN, created_at TEXT);
            CREATE TABLE sessions (id TEXT PRIMARY KEY, user_id TEXT, title TEXT, next_seq INTEGER, created_at TEXT, updated_at TEXT);
            CREATE TABLE runs (id TEXT PRIMARY KEY, user_id TEXT, session_id TEXT, request_id TEXT, fingerprint TEXT, run_status TEXT, result_status TEXT, answer TEXT, safe_error_code TEXT, created_at TEXT, finished_at TEXT);
            CREATE TABLE messages (id TEXT PRIMARY KEY, session_id TEXT, run_id TEXT, seq INTEGER, role TEXT, content TEXT, created_at TEXT);
            CREATE TABLE execution_events (id INTEGER PRIMARY KEY, run_id TEXT, stage TEXT, status TEXT, created_at TEXT);
        ''')
        db.execute('INSERT INTO users VALUES (?,?,?,?,?)', (user_id, 'legacy', HASHER.hash('Legacy-Synthetic-123!'), True, now))
        db.execute('INSERT INTO sessions VALUES (?,?,?,?,?,?)', (sid, user_id, '旧会话', 3, now, now))
        db.execute('INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?)', (rid, user_id, sid, request_id, 'x'*64, 'finished', 'completed', '旧回答', None, now, now))
        for seq, role, content in [(1, 'user', '旧问题'), (2, 'assistant', '旧回答')]:
            db.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,?)', (str(uuid4()), sid, rid, seq, role, content, now))
    for _ in range(2):
        with TestClient(create_app(settings)) as migrated:
            response = migrated.post('/auth/login', json={'username': 'legacy', 'password': 'Legacy-Synthetic-123!'})
            headers = {'Authorization': 'Bearer ' + response.json()['access_token']}
            assert [m['content'] for m in migrated.get(f'/sessions/{sid}/messages', headers=headers).json()['items']] == ['旧问题', '旧回答']
            old = migrated.get('/runs/' + rid, headers=headers).json()
            assert old['graph_version'] is None and old['model_calls'] is None


def test_run_list_and_active_progress_are_private(client, app):
    alice, bob = login(client), login(client, 'bob')
    sid = session(client, alice)
    result = ask(client, alice, sid, '请澄清我的请求').json()
    assert result['plan_status'] == 'skipped' and result['model_calls'] == 0
    assert client.get(f'/sessions/{sid}/runs', headers=alice).json()[0]['run_id'] == result['run_id']
    assert client.get(f'/sessions/{sid}/runs', headers=bob).status_code == 404


def test_old_executor_cannot_overwrite_new_lease_owner(client, app):
    import time
    headers = login(client)
    sid = session(client, headers)
    def replacement(state):
        with app.state.store.sessions.begin() as db:
            run = db.get(Run, state['run_id'])
            metadata = json.loads(run.details_json)
            metadata.update(lease_token='replacement-test-owner', lease_until=time.time()+60, stage='other_owner')
            run.details_json = json.dumps(metadata)
        return {'answer': 'old result'}
    app.state.model.decide = replacement
    response = ask(client, headers, sid)
    assert response.status_code == 409
    with app.state.store.sessions() as db:
        run = db.scalar(select(Run).where(Run.session_id == sid))
        assert run.run_status == 'running'
        assert json.loads(run.details_json)['stage'] == 'other_owner'
