from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.agent import Plan
from app.main import create_app
from app.service import ApiError
from test_api import app, client, login, session, settings
from test_graph import ask, call


def task(tid, role='consultation_agent', dependencies=None, require_sources=False):
    return {'task_id': tid, 'agent_id': role, 'description': tid,
            'depends_on': dependencies or [], 'require_sources': require_sources}


@pytest.mark.parametrize('tasks', [[], [task('x')] * 2, [task('x', 'unknown')],
                                  [task('x', dependencies=['missing'])], [task('x', dependencies=['x'])],
                                  [task('x', dependencies=['y']), task('y', dependencies=['x'])],
                                  [task('x', dependencies=['y', 'y']), task('y')],
                                  [task(str(i)) for i in range(5)]])
def test_plan_rejects_invalid_semantics(tasks):
    with pytest.raises(ValidationError):
        Plan.model_validate({'tasks': tasks})


def test_same_role_parallel_tasks_are_independent(client, app):
    app.state.model.plan = lambda s: {'tasks': [task('a'), task('b')]}
    barrier = Barrier(2)
    seen = []
    lock = Lock()

    def decide(s):
        barrier.wait(timeout=3)  # Fails if the two independent tasks are serialized.
        with lock:
            seen.append((s['task_id'], s['context'], s['observations'], s['model_calls']))
        return {'answer': s['task_id']}

    app.state.model.decide = decide
    headers = login(client)
    result = ask(client, headers, session(client, headers), '多任务').json()
    assert result['result_status'] == 'completed'
    assert result['task_count'] == 2 and result['distinct_agent_count'] == 1
    assert result['model_calls'] == 4 and result['tool_calls'] == 0
    assert [r['model_calls'] for r in result['task_results']] == [1, 1]
    assert len(seen) == 2 and all(x[2] == [] and x[3] == 1 for x in seen)
    assert seen[0][1] == seen[1][1] and seen[0][1] is not seen[1][1]


def test_dependency_waits_and_gets_validated_result(client, app):
    app.state.model.plan = lambda s: {'tasks': [task('c', dependencies=['a']), task('a'), task('b')]}
    calls = []

    def decide(s):
        calls.append(s['task_id'])
        if s['task_id'] == 'c':
            assert 'a' in calls and s['dependency_results'][0]['answer'] == 'a'
        return {'answer': s['task_id']}

    app.state.model.decide = decide
    headers = login(client)
    sid = session(client, headers)
    result = ask(client, headers, sid, '多任务').json()
    assert result['completed_task_count'] == 3
    assert calls.index('a') < calls.index('c')
    assert len(client.get(f'/sessions/{sid}/messages', headers=headers).json()['items']) == 2


def test_failed_dependency_blocks_only_dependents(client, app):
    app.state.model.plan = lambda s: {'tasks': [task('a'), task('b', dependencies=['a']), task('c')]}
    app.state.model.decide = lambda s: {'answer': '' if s['task_id'] == 'a' else '可用输出'}
    headers = login(client)
    result = ask(client, headers, session(client, headers), '多任务').json()
    assert result['result_status'] == 'partial'
    assert result['started_task_count'] == 2 and result['blocked_task_count'] == 1
    assert result['failed_task_count'] == 1 and result['completed_task_count'] == 1
    blocked = next(r for r in result['task_results'] if r['task_id'] == 'b')
    assert blocked['safe_error_code'] == 'DEPENDENCY_FAILED' and blocked['model_calls'] == 0


def test_global_budget_is_atomic_across_workers(client, app):
    app.state.flow.settings = app.state.flow.settings.model_copy(update={'max_model_calls': 2})
    app.state.model.plan = lambda s: {'tasks': [task('a'), task('b')]}
    headers = login(client)
    result = ask(client, headers, session(client, headers), '多任务').json()
    assert result['model_calls'] == 2
    assert result['result_status'] == 'partial' and result['safe_error_code'] == 'MODEL_BUDGET_EXCEEDED'
    assert sum(r['model_calls'] for r in result['task_results']) == 1


def test_worker_budget_does_not_spend_other_task_allowance(client, app):
    app.state.model.plan = lambda s: {'tasks': [task('a'), task('b')]}
    app.state.model.decide = lambda s: {'tool_calls': [call(query='x') for _ in range(3)]} if s['task_id'] == 'a' else {'answer': 'b'}
    app.state.flow.settings = app.state.flow.settings.model_copy(update={'max_tool_calls': 5, 'max_worker_tool_calls': 1})
    headers = login(client)
    result = ask(client, headers, session(client, headers), '多任务').json()
    # Independent workers can finish in either order; verify their own budgets by identity.
    by_id = {r['task_id']: r for r in result['task_results']}
    a, b = by_id['a'], by_id['b']
    assert a['safe_error_code'] == 'WORKER_TOOL_BUDGET_EXCEEDED'
    assert a['tool_calls'] == 1 and b['tool_calls'] == 0 and b['status'] == 'completed'


def test_missing_evidence_has_one_bounded_refinement(client, app):
    app.state.model.plan = lambda s: {'tasks': [task('a', require_sources=True), task('b')]}
    app.state.model.decide = lambda s: {'answer': '无引用'}
    headers = login(client)
    result = ask(client, headers, session(client, headers), '多任务').json()
    assert result['refinement_count'] == 1 and result['result_status'] == 'partial'
    refined = next(r for r in result['task_results'] if r['task_id'] == 'a')
    assert refined['status'] == 'partial'
    assert refined['model_calls'] == 2
    assert result['evidence_issues'] == [{'code': 'EVIDENCE_MISSING', 'task_id': 'a'}]

def test_worker_does_not_offer_tools_without_room_to_finish(client, app):
    app.state.flow.settings = app.state.flow.settings.model_copy(update={'max_worker_tool_calls': 1})
    app.state.model.plan = lambda s: {'tasks': [task('a', 'research_agent', require_sources=True), task('b')]}
    offered = []
    def decide(s):
        if s['task_id'] == 'b': return {'answer': '说明'}
        offered.append(s['allowed_tools'])
        if not s['observations']: return {'tool_calls': [call(query='合成资料')]}
        assert s['allowed_tools'] == []
        return {'answer': '依据已取得资料回答', 'source_ids': [d['id'] for o in s['observations'] for d in o['result']['documents']]}
    app.state.model.decide = decide
    headers = login(client)
    result = ask(client, headers, session(client, headers), '多任务').json()
    assert result['result_status'] == 'completed'
    assert offered[0] and offered[1] == []

@pytest.mark.parametrize('limits', [{'max_model_calls': 2}, {'max_worker_iterations': 1}])
def test_last_model_or_iteration_offers_only_final_answer(client, app, limits):
    app.state.flow.settings = app.state.flow.settings.model_copy(update=limits)
    app.state.model.plan = lambda s: {'tasks': [task('a', 'research_agent')]}
    def decide(s):
        assert s['allowed_tools'] == []
        return {'answer': '当前预算没有继续检索空间，未检索资料。'}
    app.state.model.decide = decide
    headers = login(client)
    result = ask(client, headers, session(client, headers), '检索资料').json()
    assert result['result_status'] == 'completed' and result['sources'] == [] and result['tool_calls'] == 0


def test_conflicting_source_is_not_summarized(client, app):
    app.state.model.plan = lambda s: {'tasks': [task('a'), task('b'), task('c', dependencies=['a', 'b'])]}
    app.state.model.decide = lambda s: ({'tool_calls': [call(query='x')]} if not s['observations'] else {'answer': '引用', 'source_ids': ['duplicate']})
    app.state.flow.tools.execute = lambda name, args, s: {'success': True, 'documents': [
        {'id': 'duplicate', 'source': 'synthetic', 'content': s['task_id'], 'verified': False}]}
    headers = login(client)
    result = ask(client, headers, session(client, headers), '多任务').json()
    assert result['safe_error_code'] == 'NO_USABLE_TASK_RESULTS' and result['sources'] == []
    assert result['blocked_task_count'] == 1
    assert all(r['status'] != 'completed' for r in result['task_results'])


@pytest.mark.parametrize('output', [{'answer': '虚构', 'task_ids': ['a', 'b'], 'source_ids': ['absent']},
                                    {'answer': '遗漏', 'task_ids': ['a']}])
def test_invalid_synthesis_keeps_completed_task_outputs(client, app, output):
    app.state.model.plan = lambda s: {'tasks': [task('a'), task('b')]}
    app.state.model.synthesize = lambda s: output
    headers = login(client)
    result = ask(client, headers, session(client, headers), '多任务').json()
    assert result['result_status'] == 'partial' and result['safe_error_code'] == 'SYNTHESIS_INVALID'
    assert result['completed_task_count'] == 2 and '虚构' not in result['answer']


def test_wave_checkpoint_resume_does_not_repeat_completed_workers(settings):
    first_app = create_app(settings)
    with TestClient(first_app) as first:
        headers = login(first)
        flow = first_app.state.flow
        first_app.state.model.plan = lambda s: {'tasks': [task('a'), task('b'), task('c', dependencies=['a'])]}
        flow.graph = flow.build_graph().compile(checkpointer=flow.saver, interrupt_after=['dispatch'])
        pending = ask(first, headers, session(first, headers), '多任务').json()
        assert pending['run_status'] == 'paused' and pending['completed_task_count'] == 2
    second_app = create_app(settings)
    with TestClient(second_app) as second:
        seen = Counter()
        second_app.state.model.plan = lambda s: pytest.fail('不应重新规划')
        second_app.state.model.decide = lambda s: (seen.update([s['task_id']]), {'answer': '恢复任务'})[1]
        result = second.post('/runs/' + pending['run_id'] + '/resume', headers=headers,
                             json={'checkpoint_id': pending['checkpoint_id']}).json()
        assert result['result_status'] == 'completed' and seen == {'c': 1}


def test_multi_demo_and_user_isolation(client):
    alice, bob = login(client), login(client, 'bob')
    sid = session(client, alice)
    result = ask(client, alice, sid, '三个专家多任务研究样本登记').json()
    assert result['result_status'] == 'completed' and result['distinct_agent_count'] == 3
    assert result['model_calls'] == 6 and result['tool_calls'] == 1
    assert result['evidence_status'] == 'passed'
    assert client.get('/runs/' + result['run_id'], headers=bob).status_code == 404


def test_cancel_parallel_workers_records_terminal_task_statuses(client, app):
    started, release = Barrier(3), Event()
    app.state.model.plan = lambda s: {'tasks': [task('a'), task('b')]}
    app.state.model.decide = lambda s: (started.wait(timeout=3), release.wait(3), {'answer': 'late'})[2]
    headers = login(client)
    sid = session(client, headers)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(ask, client, headers, sid, '多任务')
            started.wait(timeout=3)
            running = client.get(f'/sessions/{sid}/runs', headers=headers).json()[0]
            assert len(running['task_results']) == 2
            assert client.post('/runs/' + running['run_id'] + '/cancel', headers=headers).status_code == 200
            result = pending.result(timeout=3).json()
            assert result['result_status'] == 'cancelled'
            assert all(r['status'] == 'cancelled' for r in result['task_results'])
    finally:
        release.set()


def test_committed_tasks_survive_interrupted_wave_before_checkpoint(client, app):
    app.state.model.plan = lambda s: {'tasks': [task('a'), task('b')]}
    flow = app.state.flow
    original = flow._run_task

    def interrupted(*args):
        result = original(*args)
        raise ApiError(503, 'SIMULATED_PROCESS_INTERRUPT', '合成故障')

    flow._run_task = interrupted
    headers = login(client)
    sid = session(client, headers)
    assert ask(client, headers, sid, '多任务').status_code == 503
    pending = client.get(f'/sessions/{sid}/runs', headers=headers).json()[0]
    assert pending['run_status'] == 'paused' and pending['completed_task_count'] == 2
    flow._run_task = lambda *args: pytest.fail('已持久化完成任务不应重复执行')
    result = client.post('/runs/' + pending['run_id'] + '/resume', headers=headers,
                         json={'checkpoint_id': pending['checkpoint_id']}).json()
    assert result['result_status'] == 'completed' and result['model_calls'] == 4


def test_old_graph_checkpoint_rejected_without_erasing_history(settings):
    from sqlalchemy import select
    import json
    from app.models import Run
    application = create_app(settings)
    with TestClient(application) as client:
        headers = login(client)
        flow = application.state.flow
        flow.graph = flow.build_graph().compile(checkpointer=flow.saver, interrupt_after=['plan'])
        pending = ask(client, headers, session(client, headers), '检索资料').json()
        with application.state.store.sessions.begin() as db:
            run = db.scalar(select(Run).where(Run.id == pending['run_id']))
            metadata = json.loads(run.details_json)
            metadata['graph_version'] = 2
            run.details_json = json.dumps(metadata)
        response = client.post('/runs/' + pending['run_id'] + '/resume', headers=headers,
                               json={'checkpoint_id': pending['checkpoint_id']})
        assert response.status_code == 409 and response.json()['error']['code'] == 'CHECKPOINT_UNAVAILABLE'
        assert client.get('/runs/' + pending['run_id'], headers=headers).json()['run_status'] == 'paused'


def test_single_task_preserves_instruction_and_requires_citations(client, app):
    app.state.model.plan = lambda s: {'tasks': [task('a', require_sources=True)]}
    seen = []
    app.state.model.decide = lambda s: (seen.append(s['task_description']), {'answer': '无引用'})[1]
    headers = login(client)
    result = ask(client, headers, session(client, headers), '检索').json()
    assert seen == ['a'] and result['safe_error_code'] == 'EVIDENCE_MISSING'


def test_dependent_worker_can_cite_validated_predecessor_sources(client, app):
    app.state.model.plan = lambda s: {'tasks': [task('a', 'research_agent', require_sources=True), task('b', dependencies=['a'], require_sources=True)]}

    def decide(state):
        if state['task_id'] == 'a' and not state['observations']:
            return {'tool_calls': [call(query='x')]}
        return {'answer': '引用实际资料', 'source_ids': ['demo-sop-1']}

    app.state.model.decide = decide
    headers = login(client)
    result = ask(client, headers, session(client, headers), '多任务').json()
    assert result['result_status'] == 'completed' and result['tool_calls'] == 1
    assert result['task_results'][1]['sources'][0]['id'] == 'demo-sop-1'


def test_explicit_answer_length_is_validated_and_repaired_without_truncating_facts(client, app):
    app.state.flow.settings = app.state.flow.settings.model_copy(update={'schema_repair_limit': 1})
    app.state.model.plan = lambda s: {'tasks': [task('a'), task('b')]}
    attempts = []
    def synthesize(state):
        attempts.append(state.get('contract_repair'))
        return {'answer': '过长的回答。'*20 if len(attempts) == 1 else '简洁回答。',
            'task_ids': ['a', 'b'], 'source_ids': []}
    app.state.model.synthesize = synthesize
    headers = login(client)
    result = ask(client, headers, session(client, headers), '多任务，请汇总成不超过20字的答复。').json()
    assert len(attempts) == 2
    assert attempts[1]['code'] == 'ANSWER_LENGTH_EXCEEDED'
    assert result['answer'] == '简洁回答。' and result['result_status'] == 'completed'
