"""Explicit HTTP acceptance, synthetic account only. Requires run.py --real.

10 small real turns, KB + rerank, real summary and Mem0, multi-task, public web,
correction/deletion, replay and cross-user isolation. No credentials in output.
"""
import argparse
import json
import secrets
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4

BASE = 'http://127.0.0.1:8010'
http = build_opener(ProxyHandler({}))


def request(path, token=None, body=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = Request(BASE + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
    try:
        with http.open(req, timeout=120) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


def account():
    body = {'username': 'live_' + uuid4().hex[:12], 'password': secrets.token_urlsafe(24)}
    assert request('/auth/register', body=body)[0] == 201
    code, data = request('/auth/login', body=body)
    assert code == 200
    return data['access_token']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not args.run:
        print('not_run; add --run to explicitly enable the synthetic cloud acceptance')
        return
    assert request('/health')[1]['mode'] == 'cloud_real'
    report_path = Path(__file__).resolve().parents[2] / 'tmp' / ('full-flow-live-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.json')
    report = {'synthetic_only': True, 'cases': [], 'provider_calls': [], 'cleanup': 'pending'}
    token, other = account(), account()
    sid = request('/sessions', token, {'title': 'D/E/F真实合成验收'})[1]['id']
    report['session_id'] = sid

    def save():
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    def wait_maintenance():
        deadline, checks = time.monotonic() + 70, 0
        while time.monotonic() < deadline:
            jobs = request('/maintenance/jobs', token)[1]['items']
            pending = [j for j in jobs if j['status'] not in ('done', 'superseded')]
            if not pending:
                return
            if any(j['status'] in ('failed', 'uncertain', 'awaiting_remote') for j in pending) and checks < 2:
                request('/maintenance/retry', token, {})
                checks += 1
            time.sleep(0.25)
        raise RuntimeError('MAINTENANCE_NOT_COMPLETED')

    def ask(name, question, actor=token, conversation=sid):
        body = {'question': question, 'request_id': str(uuid4())}
        code, data = request('/sessions/' + conversation + '/chat', actor, body)
        case = {'name': name, 'http_status': code, 'run_id': data.get('run_id'),
                'result_status': data.get('result_status'), 'safe_error_code': data.get('safe_error_code')}
        report['cases'].append(case)
        save()
        print(name + ': ' + str(case['result_status']), flush=True)
        if code != 200 or data['result_status'] != 'completed':
            raise RuntimeError('CASE_NOT_COMPLETED_' + name)
        case.update(model_calls=data['model_calls'], tool_calls=data['tool_calls'],
                    task_count=data['task_count'], distinct_agent_count=data['distinct_agent_count'],
                    context_details=data['context_details'], summary_coverage=data['summary_coverage'],
                    source_kinds=[s.get('content_kind') for s in data['sources']],
                    rerank_used=any(s.get('reranker') == 'BAAI/bge-reranker-v2-m3' for s in data['sources']))
        return data, body

    try:
        for i in range(10):
            ask('recent_turn_' + str(i+1), f'这是合成通信测试第{i+1}轮。请只回复“已收到”。')
        assert request('/sessions/' + sid + '/summary', token)[1]['status'] == 'empty'
        knowledge, body = ask('knowledge_and_preferences', '我偏好简洁中文回答。检索本地合成资料，介绍样本登记草稿的编辑、确认和取消流程，请引用资料。')
        assert knowledge['sources'] and any(s.get('reranker') for s in knowledge['sources'])
        wait_maintenance()
        summary = request('/sessions/' + sid + '/summary', token)[1]
        assert summary['status'] == 'ready' and summary['covered_until_seq'] == 2
        assert request('/sessions/' + sid + '/chat', token, body)[1]['replayed'] is True
        assert request('/runs/' + knowledge['run_id'], other)[0] == 404
        assert request('/memories', other)[1]['items'] == []
        multi, _ = ask('multi_task_with_memory_and_summary', '请做三个专家任务：consultation_agent解释登记流程，research_agent检索本地合成SOP，diagnostic_agent根据research结果检查必填字段与确认条件。仅使用本地合成资料，请汇总并引用。')
        assert multi['task_count'] == 3 and multi['distinct_agent_count'] == 3
        assert multi['summary_coverage'] >= 2 and multi['context_details']['memory_count'] >= 1
        wait_maintenance()
        web, _ = ask('pubmed_network', '请联网查询 biobanking sample management，给出最多两个PubMed索引结果和链接，只说明标题与日期，不声称读过论文正文。')
        assert any(s['source'] == 'pubmed' for s in web['sources'])
        wait_maintenance()
        facts = request('/memories', token)[1]['items']
        assert len(facts) == 2 and all(f['version'] == f['synced_version'] for f in facts)
        language = next(f for f in facts if f['key'] == 'answer_language')
        request('/memories/' + language['id'], token, {'operation': 'update', 'content': '用户偏好回答语言：英文'})
        wait_maintenance()
        updated = request('/memories', token)[1]['items']
        assert next(f for f in updated if f['id'] == language['id'])['synced_version'] == 2
        corrected, _ = ask('corrected_memory', '我的长期回答语言偏好是什么？请依据本人记忆简洁回答。')
        assert corrected['context_details']['memory_count'] >= 1
        wait_maintenance()
        other_sid = request('/sessions', other, {'title': '隔离验证'})[1]['id']
        isolated, _ = ask('other_user_memory_empty', '我的长期偏好有哪些？没有记忆请说明。', other, other_sid)
        assert isolated['context_details']['memory_count'] == 0
        report['status'] = 'passed'
    except Exception as error:
        report['status'] = 'failed'
        report['safe_error_code'] = str(error) if isinstance(error, RuntimeError) else 'ASSERTION_OR_HTTP_ERROR'
        print('acceptance: failed', flush=True)
    finally:
        for fact in request('/memories', token)[1]['items']:
            if fact['status'] != 'deleted':
                request('/memories/' + fact['id'], token, {'operation': 'delete'})
        try:
            wait_maintenance()
            facts = request('/memories', token)[1]['items']
            report['cleanup'] = 'passed' if all(f['status'] == 'deleted' and f['synced_version'] == f['version'] for f in facts) else 'failed'
        except Exception:
            report['cleanup'] = 'unverified'
        for case in report['cases']:
            if case['run_id']:
                actor = other if case['name'] == 'other_user_memory_empty' else token
                calls = request('/runs/' + case['run_id'] + '/providers', actor)[1].get('items', [])
                report['provider_calls'] += [{'run_id': case['run_id'], **row} for row in calls]
        report['totals'] = {p: sum(r['provider'] == p for r in report['provider_calls']) for p in ('deepseek', 'mem0', 'pubmed')}
        report['token_usage'] = {k: sum(row['usage'].get(k, 0) for row in report['provider_calls']) for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
        save()
        print(json.dumps({'status': report['status'], 'cleanup': report['cleanup'], 'requests': report['totals'], 'report': str(report_path)}), flush=True)
    if report['status'] != 'passed' or report['cleanup'] != 'passed':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
