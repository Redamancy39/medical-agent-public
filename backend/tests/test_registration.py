from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest

from fastapi.testclient import TestClient
from app.main import create_app
from test_api import app, client, login, session, settings

FIELDS = {'project': 'DEMO-A', 'sample_type': '血液', 'quantity': 3,
          'received_at': '2026-10-13', 'storage': 'DEMO-B 区域', 'note': '合成测试'}

def prepare(client, headers, sid, **extra):
    return client.post(f'/sessions/{sid}/registration-drafts', headers=headers,
                       json={'text': '请登记3份血液样本，项目DEMO-A，2026-10-13接收，存储在DEMO-B区域',
                             'request_id': str(uuid4()), **extra})

def operation(client, headers, draft, op, **extra):
    return client.post('/registration-drafts/' + draft['id'] + '/' + op, headers=headers,
                       json={'revision': draft['revision'], 'request_id': str(uuid4()), **extra})

def records(client, headers):
    return client.get('/registration-records', headers=headers).json()['items']

def test_draft_edit_review_and_confirm_are_different_actions(client):
    headers = login(client)
    sid = session(client, headers)
    response = prepare(client, headers, sid)
    assert response.status_code == 200
    draft = response.json()['draft']
    assert draft['status'] == 'ready' and draft['fields']['quantity'] == 3
    assert draft['workflow'] == 'registration_graph_v1' and len(records(client, headers)) == 0
    review = operation(client, headers, draft, 'review').json()
    token = review['confirmation_token']
    assert len(records(client, headers)) == 0
    edit = operation(client, headers, draft, 'edit', fields=FIELDS | {'quantity': 4}).json()['draft']
    assert edit['revision'] == 2 and edit['status'] == 'ready'
    stale = operation(client, headers, draft, 'confirm', confirmation_token=token, explicit_confirm=True)
    assert stale.status_code == 409 and len(records(client, headers)) == 0
    new_review = operation(client, headers, edit, 'review').json()
    body = {'revision': 2, 'request_id': str(uuid4()), 'confirmation_token': new_review['confirmation_token'], 'explicit_confirm': True}
    url = '/registration-drafts/' + edit['id'] + '/confirm'
    done = client.post(url, headers=headers, json=body)
    assert done.status_code == 200 and done.json()['record']['fields']['quantity'] == 4
    assert done.json()['draft']['status'] == 'completed'
    assert client.post(url, headers=headers, json=body).json()['replayed'] is True
    assert len(records(client, headers)) == 1
    assert operation(client, headers, edit, 'edit', fields=FIELDS).status_code == 409

def test_incomplete_cancel_and_unauthorized_never_write(client):
    headers = login(client)
    sid = session(client, headers)
    draft = prepare(client, headers, sid, text='登记3份血液样本').json()['draft']
    assert draft['status'] == 'incomplete' and set(draft['issues']) == {'project', 'received_at', 'storage'}
    assert operation(client, headers, draft, 'review').status_code == 422
    draft = operation(client, headers, draft, 'edit', fields=FIELDS).json()['draft']
    reviewed = operation(client, headers, draft, 'review').json()
    other = login(client, 'bob')
    assert operation(client, other, draft, 'confirm', confirmation_token=reviewed['confirmation_token'], explicit_confirm=True).status_code == 404
    assert prepare(client, other, sid).status_code == 404
    assert operation(client, headers, draft, 'cancel').status_code == 200
    assert operation(client, headers, draft, 'confirm', confirmation_token=reviewed['confirmation_token'], explicit_confirm=True).status_code == 409
    assert records(client, headers) == [] and records(client, other) == []

def test_no_confirmation_token_or_wrong_fields_cannot_write(client):
    headers = login(client)
    draft = prepare(client, headers, session(client, headers)).json()['draft']
    assert operation(client, headers, draft, 'confirm', confirmation_token='x' * 48, explicit_confirm=True).status_code == 409
    review = operation(client, headers, draft, 'review').json()
    assert operation(client, headers, draft, 'confirm', confirmation_token=review['confirmation_token'], explicit_confirm=False).status_code == 422
    invalid = operation(client, headers, draft, 'edit', fields=FIELDS | {'project': 'PRIVATE', 'received_at': '2026-02-30', 'quantity': 0}).json()['draft']
    assert set(invalid['issues']) == {'project', 'received_at', 'quantity'}
    assert operation(client, headers, invalid, 'review').status_code == 422
    assert operation(client, headers, invalid, 'edit', fields=FIELDS | {'quantity': True}).status_code == 422
    assert records(client, headers) == []

def test_request_replay_conflicts_and_reopening(settings):
    app = create_app(settings)
    with TestClient(app) as client:
        headers = login(client)
        sid = session(client, headers)
        rid = str(uuid4())
        response = prepare(client, headers, sid, request_id=rid)
        assert response.status_code == 200
        draft = response.json()['draft']
        assert prepare(client, headers, sid, request_id=rid).json()['replayed'] is True
        assert prepare(client, headers, sid, request_id=rid, text='不同内容').status_code == 409
        review = operation(client, headers, draft, 'review').json()
    with TestClient(create_app(settings)) as client:
        assert client.get('/registration-drafts/' + draft['id'], headers=headers).json()['draft']['status'] == 'awaiting_confirmation'
        assert operation(client, headers, draft, 'confirm', confirmation_token=review['confirmation_token'], explicit_confirm=True).status_code == 200
        assert len(records(client, headers)) == 1
        audit = client.get('/registration-drafts/' + draft['id'] + '/audit', headers=headers).json()['items']
        assert [x['action'] for x in audit] == ['prepare', 'review', 'confirm']

def test_concurrent_confirm_and_edit_are_serialized(client):
    headers = login(client)
    draft = prepare(client, headers, session(client, headers)).json()['draft']
    token = operation(client, headers, draft, 'review').json()['confirmation_token']
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: operation(client, headers, draft, 'confirm', confirmation_token=token, explicit_confirm=True), range(2)))
    assert all(r.status_code == 200 for r in results) and len(records(client, headers)) == 1
    second = prepare(client, headers, session(client, headers)).json()['draft']
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda n: operation(client, headers, second, 'edit', fields=FIELDS | {'quantity': n}), [4, 5]))
    assert sorted(r.status_code for r in results) == [200, 409]

def test_ambiguous_extraction_is_visible_and_never_guessed(client):
    headers = login(client)
    draft = prepare(client, headers, session(client, headers), text='登记3份或5份血液和组织，项目DEMO-A或DEMO-B，2026-10-13，DEMO-B区域').json()['draft']
    assert draft['status'] == 'incomplete'
    assert draft['fields']['quantity'] is None and draft['fields']['sample_type'] == '' and draft['fields']['project'] == ''
    assert records(client, headers) == []

def test_write_and_receipt_rollback_together(client, app, monkeypatch):
    from app.registration import RegistrationService
    headers = login(client)
    draft = prepare(client, headers, session(client, headers)).json()['draft']
    token = operation(client, headers, draft, 'review').json()['confirmation_token']
    original = RegistrationService.save_receipt
    def fail_receipt(db, user_id, row, body, fingerprint, action, result):
        raise RuntimeError('synthetic receipt failure')
    monkeypatch.setattr(RegistrationService, 'save_receipt', staticmethod(fail_receipt))
    body = {'revision': draft['revision'], 'request_id': str(uuid4()), 'confirmation_token': token, 'explicit_confirm': True}
    url = '/registration-drafts/' + draft['id'] + '/confirm'
    assert client.post(url, headers=headers, json=body).status_code == 500
    assert records(client, headers) == []
    assert client.get('/registration-drafts/' + draft['id'], headers=headers).json()['draft']['status'] == 'awaiting_confirmation'
    monkeypatch.setattr(RegistrationService, 'save_receipt', staticmethod(original))
    assert client.post(url, headers=headers, json=body).status_code == 200
    assert len(records(client, headers)) == 1

def test_business_never_calls_models_and_strict_confirmation(client, app):
    app.state.model.decide = lambda _: (_ for _ in ()).throw(AssertionError('must not call model'))
    headers = login(client)
    draft = prepare(client, headers, session(client, headers)).json()['draft']
    token = operation(client, headers, draft, 'review').json()['confirmation_token']
    assert operation(client, headers, draft, 'confirm', confirmation_token=token, explicit_confirm=1).status_code == 422
    assert operation(client, headers, draft, 'confirm', confirmation_token=token, explicit_confirm=True).status_code == 200

@pytest.mark.parametrize('competing', ['edit', 'cancel'])
def test_confirm_competing_mutation_has_one_atomic_winner(client, competing):
    headers = login(client)
    draft = prepare(client, headers, session(client, headers)).json()['draft']
    token = operation(client, headers, draft, 'review').json()['confirmation_token']
    with ThreadPoolExecutor(2) as pool:
        confirm = pool.submit(operation, client, headers, draft, 'confirm', confirmation_token=token, explicit_confirm=True)
        mutation = pool.submit(operation, client, headers, draft, competing, **({'fields': FIELDS | {'quantity': 4}} if competing == 'edit' else {}))
        confirm, mutation = confirm.result(), mutation.result()
    assert sorted([confirm.status_code, mutation.status_code]) == [200, 409]
    rows = records(client, headers)
    current = client.get('/registration-drafts/' + draft['id'], headers=headers).json()['draft']
    if confirm.status_code == 200:
        assert len(rows) == 1 and rows[0]['fields']['quantity'] == 3 and current['status'] == 'completed'
    else:
        assert rows == [] and current['status'] == ('ready' if competing == 'edit' else 'cancelled')

def test_second_review_rotates_confirmation_and_wrong_scope_is_private(client):
    headers = login(client)
    draft = prepare(client, headers, session(client, headers)).json()['draft']
    first = operation(client, headers, draft, 'review').json()['confirmation_token']
    second = operation(client, headers, draft, 'review').json()['confirmation_token']
    assert first != second
    assert operation(client, headers, draft, 'confirm', confirmation_token=first, explicit_confirm=True).status_code == 409
    other = login(client, 'bob')
    assert client.get('/registration-drafts/' + draft['id'] + '/audit', headers=other).status_code == 404
    assert client.get('/registration-drafts/' + draft['id'], headers=other).status_code == 404
    assert operation(client, headers, draft, 'confirm', confirmation_token=second, explicit_confirm=True).status_code == 200
