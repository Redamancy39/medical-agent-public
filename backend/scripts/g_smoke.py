"""Local HTTP acceptance; synthetic business data only. --run required."""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[2]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--real-agents', action='store_true', help='Allow two real-model API cases in addition to synthetic registration')
    args = parser.parse_args()
    if not args.run:
        print('not_run: pass --run for local HTTP; --real-agents additionally authorizes two cloud agent cases')
        return
    report = {'synthetic_only': True, 'business_mode': 'synthetic_sql', 'checks': {}, 'agent_cases': []}
    output = ROOT / 'tmp' / ('g-http-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S') + '-' + uuid4().hex[:6] + '.json')
    with httpx.Client(base_url='http://127.0.0.1:8010', trust_env=False, timeout=120) as client:
        def request(path, body=None, headers=None):
            response = client.get(path, headers=headers) if body is None else client.post(path, headers=headers, json=body)
            return response.status_code, response.json()
        health = request('/health')[1]
        report['mode'] = health['mode']
        def actor(prefix):
            body = {'username': prefix + uuid4().hex[:15], 'password': 'Synthetic-G-HTTP-Only!'}
            assert request('/auth/register', body)[0] == 201
            status, data = request('/auth/login', body)
            assert status == 200
            return {'Authorization': 'Bearer ' + data['access_token']}
        headers, other = actor('g_owner_'), actor('g_other_')
        sid = request('/sessions', {'title': '批次G模拟业务HTTP'}, headers)[1]['id']
        report['session_id'] = sid
        def prepare(value):
            return request(f'/sessions/{sid}/registration-drafts', {'text': value, 'request_id': str(uuid4())}, headers)
        def op(draft, name, **extra):
            return request('/registration-drafts/' + draft['id'] + '/' + name,
                {'revision': draft['revision'], 'request_id': str(uuid4()), **extra}, headers)
        def records():
            return request('/registration-records', headers=headers)[1]['items']
        def check(name, predicate):
            report['checks'][name] = bool(predicate)
            if not predicate: raise RuntimeError(name)
        try:
            incomplete = prepare('登记3份血液样本')[1]['draft']
            check('missing_fields_pause_zero_records', incomplete['status'] == 'incomplete' and len(incomplete['issues']) == 3 and records() == [])
            check('incomplete_review_rejected', op(incomplete, 'review')[0] == 422)
            fields = {'project': 'DEMO-A', 'sample_type': '血液', 'quantity': 3, 'received_at': '2026-10-13', 'storage': 'DEMO-B 区域', 'note': '合成HTTP验收'}
            draft = op(incomplete, 'edit', fields=fields)[1]['draft']
            reviewed = op(draft, 'review')[1]
            check('review_zero_records', records() == [])
            updated = op(draft, 'edit', fields=fields | {'quantity': 4})[1]['draft']
            check('old_revision_rejected', op(draft, 'confirm', confirmation_token=reviewed['confirmation_token'], explicit_confirm=True)[0] == 409 and records() == [])
            new_review = op(updated, 'review')[1]
            body = {'revision': updated['revision'], 'request_id': str(uuid4()), 'confirmation_token': new_review['confirmation_token'], 'explicit_confirm': True}
            url = '/registration-drafts/' + draft['id'] + '/confirm'
            check('cross_user_confirm_rejected', request(url, body, other)[0] == 404)
            confirmed = request(url, body, headers)[1]
            check('explicit_confirm_one_batch', confirmed['draft']['status'] == 'completed' and len(records()) == 1 and len(confirmed['record']['sample_ids']) == 4)
            check('confirm_replay_one_batch', request(url, body, headers)[1]['replayed'] and len(records()) == 1)
            cancelled = prepare('请登记3份组织样本，项目DEMO-B，2026-10-13接收，存储在DEMO-C区域')[1]['draft']
            token = op(cancelled, 'review')[1]['confirmation_token']
            check('cancel_zero_extra_records', op(cancelled, 'cancel')[1]['draft']['status'] == 'cancelled' and len(records()) == 1)
            check('confirm_after_cancel_rejected', op(cancelled, 'confirm', confirmation_token=token, explicit_confirm=True)[0] == 409 and len(records()) == 1)
            check('other_user_records_empty', request('/registration-records', headers=other)[1]['items'] == [])
            check('refresh_preserves_state', request('/registration-drafts/' + updated['id'], headers=headers)[1]['draft']['status'] == 'completed')
            if health['mode'] == 'offline_fake' or args.real_agents:
                questions = [
                    ('single', '请仅由research_agent完成一个任务：检索本地合成资料，说明样本登记字段和编辑、确认、取消的规则，请引用资料。'),
                    ('multi', '请做三个专家任务：consultation_agent解释登记流程，research_agent检索本地合成SOP，diagnostic_agent根据research结果检查必填字段与确认条件。仅使用本地合成资料，请汇总并引用。')]
                for topology, question in questions:
                    agent_sid = request('/sessions', {'title': 'G HTTP ' + topology}, headers)[1]['id']
                    request_body = {'question': question, 'request_id': str(uuid4())}
                    started = time.monotonic()
                    code, run = request('/sessions/' + agent_sid + '/chat', request_body, headers)
                    calls = request('/runs/' + run['run_id'] + '/providers', headers=headers)[1]['items']
                    report['agent_cases'].append({'topology': topology, 'elapsed_seconds': round(time.monotonic()-started, 4), 'result': run, 'providers': calls})
                    check(topology + '_completed', code == 200 and run['result_status'] == 'completed' and bool(run['sources']))
                    check(topology + '_tasks', run['task_count'] == (1 if topology == 'single' else 3))
                    if topology == 'multi': check('multi_three_roles', run['distinct_agent_count'] == 3)
                    check(topology + '_chat_replay', request('/sessions/' + agent_sid + '/chat', request_body, headers)[1]['replayed'])
                    check(topology + '_cross_user_run_404', request('/runs/' + run['run_id'], headers=other)[0] == 404)
                    print(topology + ': ' + run['result_status'], flush=True)
            else:
                report['agent_observation'] = 'not_run_real_flag_required'
            report['status'] = 'passed'
        except Exception as error:
            report['status'] = 'failed'
            report['safe_error_code'] = str(error) if isinstance(error, RuntimeError) else type(error).__name__
        finally:
            report['records'] = records()
            calls = [c for row in report['agent_cases'] for c in row['providers']]
            report['requests'] = {p: sum(c['provider'] == p for c in calls) for p in ('deepseek', 'mem0', 'pubmed')}
            report['token_usage'] = {k: sum(c['usage'].get(k, 0) for c in calls) for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps({'status': report['status'], 'checks': len(report['checks']), 'requests': report['requests'], 'report': str(output)}))
    if report['status'] != 'passed': raise SystemExit(2)

if __name__ == '__main__':
    main()
