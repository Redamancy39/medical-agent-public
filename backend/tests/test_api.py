from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import Settings, load_settings
from app.main import create_app
from app.models import Message, User


@pytest.fixture
def settings(tmp_path):
    return Settings(database_path=tmp_path / 'test.db', jwt_secret='test-only-signing-key-' + 'x' * 64)


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def login(client, name='alice'):
    body = {'username': name, 'password': 'Synthetic-Password-123!'}
    response = client.post('/auth/register', json=body)
    assert response.status_code == 201
    response = client.post('/auth/login', json=body)
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['access_token']}


def session(client, headers):
    response = client.post('/sessions', headers=headers, json={'title': '测试会话'})
    assert response.status_code == 201
    return response.json()['id']


def test_health_and_auth(client, app):
    assert client.get('/health').json()['mode'] == 'offline_fake'
    assert client.get('/auth/me').status_code == 401
    headers = login(client)
    assert client.get('/auth/me', headers=headers).json()['username'] == 'alice'
    assert client.post('/auth/register', json={'username': 'Alice', 'password': 'Another-Synthetic-123!'}).status_code == 409
    assert client.post('/auth/login', json={'username': 'alice', 'password': 'Wrong-Synthetic-123!'}).status_code == 401
    with app.state.store.sessions() as db:
        user = db.scalar(select(User))
        assert user.password_hash.startswith('$argon2')
        assert 'Synthetic-Password' not in user.password_hash


@pytest.mark.parametrize('case', ['expired', 'wrong_key', 'wrong_algorithm', 'wrong_audience', 'missing_exp', 'tampered'])
def test_invalid_tokens(client, settings, case):
    headers = login(client)
    token = headers['Authorization'].split(' ', 1)[1]
    payload = jwt.decode(token, options={'verify_signature': False})
    key = settings.jwt_secret.get_secret_value()
    algorithm = 'HS256'
    if case == 'expired':
        payload['exp'] = datetime.now(timezone.utc) - timedelta(seconds=1)
    elif case == 'wrong_key':
        key = 'invalid-test-key-' + 'z' * 40
    elif case == 'wrong_algorithm':
        algorithm = 'HS512'
    elif case == 'wrong_audience':
        payload['aud'] = 'other-application'
    elif case == 'missing_exp':
        del payload['exp']
    token = jwt.encode(payload, key, algorithm=algorithm)
    if case == 'tampered':
        pieces = token.split('.')
        pieces[1] = ('A' if pieces[1][0] != 'A' else 'B') + pieces[1][1:]
        token = '.'.join(pieces)
    response = client.get('/auth/me', headers={'Authorization': 'Bearer ' + token})
    assert response.status_code == 401
    assert response.json()['error']['code'] == 'INVALID_TOKEN'


def test_disabled_user(client, app):
    headers = login(client)
    with app.state.store.sessions.begin() as db:
        db.scalar(select(User)).active = False
    assert client.get('/sessions', headers=headers).status_code == 401


def test_session_ownership_and_payload_identity(client):
    alice = login(client)
    bob = login(client, 'bob')
    sid = session(client, alice)
    run = client.post(f'/sessions/{sid}/chat', headers=alice, json={'question': 'hello', 'request_id': str(uuid4())}).json()
    assert client.get('/sessions', headers=bob).json()['total'] == 0
    for path in [f'/sessions/{sid}', f'/sessions/{sid}/messages', '/runs/' + run['run_id']]:
        assert client.get(path, headers=bob).status_code == 404
    assert client.post(f'/sessions/{sid}/chat', headers=bob, json={'question': 'hello', 'request_id': str(uuid4())}).status_code == 404
    response = client.post(f'/sessions/{sid}/chat', headers=alice, json={'question': 'hello', 'user_id': 'bob'})
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'VALIDATION_ERROR'


def test_chat_idempotency_and_pagination(client):
    headers = login(client)
    sid = session(client, headers)
    body = {'question': '记录这个研究问题', 'request_id': str(uuid4())}
    first = client.post(f'/sessions/{sid}/chat', headers=headers, json=body)
    repeat = client.post(f'/sessions/{sid}/chat', headers=headers, json=body)
    assert first.status_code == repeat.status_code == 200
    assert first.json()['result_status'] == 'completed'
    assert first.json()['mode'] == 'offline_fake'
    assert repeat.json()['run_id'] == first.json()['run_id']
    assert repeat.json()['replayed'] is True
    page = client.get(f'/sessions/{sid}/messages?limit=1', headers=headers).json()
    assert page['has_more'] is True
    assert page['items'][0]['role'] == 'user'
    second = client.get(f'/sessions/{sid}/messages?after_seq={page["next_after_seq"]}', headers=headers).json()
    assert [m['role'] for m in second['items']] == ['assistant']
    assert second['items'][0]['seq'] == 2
    changed = dict(body, question='different question')
    assert client.post(f'/sessions/{sid}/chat', headers=headers, json=changed).status_code == 409
    other = session(client, headers)
    assert client.post(f'/sessions/{other}/chat', headers=headers, json=body).status_code == 409


def test_restart_retains_history_and_token(settings):
    with TestClient(create_app(settings)) as first:
        headers = login(first)
        sid = session(first, headers)
        run = first.post(f'/sessions/{sid}/chat', headers=headers, json={'question': 'first', 'request_id': str(uuid4())}).json()
    with TestClient(create_app(settings)) as restarted:
        assert restarted.get('/sessions', headers=headers).json()['total'] == 1
        assert len(restarted.get(f'/sessions/{sid}/messages', headers=headers).json()['items']) == 2
        assert restarted.get('/runs/' + run['run_id'], headers=headers).json()['answer'] == run['answer']
        restarted.post(f'/sessions/{sid}/chat', headers=headers, json={'question': 'continue', 'request_id': str(uuid4())})
        assert [m['seq'] for m in restarted.get(f'/sessions/{sid}/messages', headers=headers).json()['items']] == [1, 2, 3, 4]


def test_concurrent_retry_is_one_turn(client):
    headers = login(client)
    sid = session(client, headers)
    body = {'question': 'concurrent', 'request_id': str(uuid4())}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: client.post(f'/sessions/{sid}/chat', headers=headers, json=body), range(2)))
    assert all(r.status_code == 200 for r in results)
    assert len({r.json()['run_id'] for r in results}) == 1
    assert len(client.get(f'/sessions/{sid}/messages', headers=headers).json()['items']) == 2


def test_model_failure_has_durable_status(client, app):
    headers = login(client)
    sid = session(client, headers)
    def broken(question):
        raise RuntimeError('synthetic-secret-that-must-not-appear')
    app.state.model.reply = broken
    body = {'question': 'failure test', 'request_id': str(uuid4())}
    response = client.post(f'/sessions/{sid}/chat', headers=headers, json=body)
    assert response.status_code == 200
    result = response.json()
    assert result['run_status'] == result['result_status'] == 'failed'
    assert result['safe_error_code'] == 'MODEL_FAILED'
    assert 'synthetic-secret' not in response.text
    assert client.get('/runs/' + result['run_id'], headers=headers).json()['result_status'] == 'failed'
    assert client.post(f'/sessions/{sid}/chat', headers=headers, json=body).json()['replayed'] is True


def test_database_failure_rolls_back_and_returns_safe_error(client, app):
    headers = login(client)
    sid = session(client, headers)
    from sqlalchemy import event
    def refuse_messages(connection, cursor, statement, parameters, context, executemany):
        if statement.lower().startswith('insert into messages'):
            raise RuntimeError('synthetic-storage-secret')
    event.listen(app.state.store.engine, 'before_cursor_execute', refuse_messages)
    try:
        response = client.post(f'/sessions/{sid}/chat', headers=headers, json={'question': 'rollback', 'request_id': str(uuid4())})
        assert response.status_code == 500
        assert response.json()['error']['code'] == 'INTERNAL_ERROR'
        assert 'synthetic-storage-secret' not in response.text
    finally:
        event.remove(app.state.store.engine, 'before_cursor_execute', refuse_messages)
    assert client.get(f'/sessions/{sid}/messages', headers=headers).json()['items'] == []


@pytest.mark.parametrize('question', ['', '   ', 'x' * 8001], ids=['empty', 'whitespace', 'oversized'])
def test_invalid_question_has_no_writes(client, question):
    headers = login(client)
    sid = session(client, headers)
    response = client.post(f'/sessions/{sid}/chat', headers=headers, json={'question': question})
    assert response.status_code == 422
    assert client.get(f'/sessions/{sid}/messages', headers=headers).json()['items'] == []


def test_settings_generate_secret_preserving_private_values(tmp_path):
    path = tmp_path / '.env'
    path.write_text('DEEPSEEK_API_KEY=synthetic-key-for-test\nMEM0_API_KEY=another-synthetic-key\nJWT_SECRET=\n', encoding='utf-8')
    first = load_settings(path)
    second = load_settings(path)
    assert first.jwt_secret == second.jwt_secret
    assert len(first.jwt_secret.get_secret_value()) >= 32
    assert first.deepseek_api_key.get_secret_value() == 'synthetic-key-for-test'
    assert second.mem0_api_key.get_secret_value() == 'another-synthetic-key'
    assert 'synthetic-key-for-test' not in repr(first)
    assert 'synthetic-key-for-test' not in first.model_dump_json()


def test_offline_network_and_logs(client, caplog, monkeypatch):
    import socket
    def reject(*args, **kwargs):
        raise AssertionError('network is disabled in batch A')
    monkeypatch.setattr(socket.socket, 'connect', reject)
    headers = login(client)
    sid = session(client, headers)
    response = client.post(f'/sessions/{sid}/chat', headers=headers, json={'question': 'private synthetic content'})
    assert response.status_code == 200
    assert 'private synthetic content' not in caplog.text
    assert headers['Authorization'] not in caplog.text


def test_external_switches_are_not_silently_used(settings):
    changed = settings.model_copy(update={'deepseek_enabled': True})
    with pytest.raises(RuntimeError, match='离线'):
        create_app(changed)


def test_password_whitespace_is_not_silently_changed(client):
    body = {'username': 'spaces', 'password': '  Synthetic-Password-123!  '}
    assert client.post('/auth/register', json=body).status_code == 201
    assert client.post('/auth/login', json=body).status_code == 200
    assert client.post('/auth/login', json=dict(body, password=body['password'].strip())).status_code == 401


def test_unexpected_failure_does_not_escape_asgi(settings):
    from sqlalchemy import event
    application = create_app(settings)
    def fail_health(connection, cursor, statement, parameters, context, executemany):
        if statement == 'SELECT 1':
            raise RuntimeError('synthetic-exception-must-not-escape')
    event.listen(application.state.store.engine, 'before_cursor_execute', fail_health)
    with TestClient(application, raise_server_exceptions=True) as client:
        response = client.get('/health')
        assert response.status_code == 500
        assert 'synthetic-exception' not in response.text
        assert response.headers['X-Request-ID'] == response.json()['request_id']


def test_concurrent_distinct_turns_keep_sequence(client):
    headers = login(client)
    sid = session(client, headers)
    bodies = [{'question': str(i), 'request_id': str(uuid4())} for i in range(3)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(pool.map(lambda body: client.post(f'/sessions/{sid}/chat', headers=headers, json=body), bodies))
    assert all(response.status_code == 200 for response in responses)
    messages = client.get(f'/sessions/{sid}/messages', headers=headers).json()['items']
    assert [message['seq'] for message in messages] == [1, 2, 3, 4, 5, 6]
    assert [message['role'] for message in messages] == ['user', 'assistant'] * 3
