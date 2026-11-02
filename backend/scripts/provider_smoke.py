"""Explicit, synthetic-only cloud smoke; never imported by the app or offline tests.

Bound: DeepSeek <= 3 requests (512 output tokens each); Mem0 <= 5 requests.
No retries, no real user data, no unscoped search or bulk delete.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.agent import Plan, SearchArgs, Synthesis
from app.config import load_settings


class Smoke:
    def __init__(self, settings, report_path):
        self.settings, self.path = settings, report_path
        self.report = {'created_at': datetime.now(timezone.utc).isoformat(), 'synthetic_only': True,
                       'requests': [], 'deepseek': {'status': 'not_run'}, 'mem0': {'status': 'not_run'}}
        self.client = httpx.Client(timeout=25, trust_env=False, follow_redirects=False)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.report, ensure_ascii=False, indent=2), encoding='utf-8')

    def request(self, provider, operation, method, url, key, body=None):
        count = sum(r['provider'] == provider for r in self.report['requests'])
        if count >= (3 if provider == 'deepseek' else 5):
            raise RuntimeError('REQUEST_BUDGET_EXCEEDED')
        record = {'provider': provider, 'operation': operation}
        self.report['requests'].append(record)
        self.save()  # Record the attempt even if process/network fails.
        start = time.monotonic()
        try:
            response = self.client.request(method, url, headers={'Authorization':
                ('Bearer ' if provider == 'deepseek' else 'Token ') + key}, json=body)
            record['http_status'] = response.status_code
            response.raise_for_status()
            data = response.json()
            record['status'] = 'passed'
            if provider == 'deepseek':
                record['usage'] = {k: v for k, v in data.get('usage', {}).items()
                                   if k in ('prompt_tokens', 'completion_tokens', 'total_tokens') and isinstance(v, int)}
            return data
        except httpx.HTTPStatusError:
            record['status'] = 'http_error'
            raise RuntimeError('HTTP_' + str(record['http_status'])) from None
        except Exception:
            record['status'] = 'network_or_response_error'
            raise RuntimeError('NETWORK_OR_RESPONSE_ERROR') from None
        finally:
            record['latency_seconds'] = round(time.monotonic() - start, 3)
            self.save()

    def ds(self):
        key = self.settings.deepseek_api_key.get_secret_value()
        if not key:
            self.report['deepseek'] = {'status': 'key_missing'}
            return
        # Never send credentials to a user-overridden or redirected host.
        if self.settings.deepseek_base_url.rstrip('/') != 'https://api.deepseek.com':
            self.report['deepseek'] = {'status': 'unsupported_base_url'}
            return
        base = {'model': self.settings.deepseek_model, 'thinking': {'type': 'disabled'}, 'max_tokens': 512, 'stream': False}
        def chat(operation, body):
            return self.request('deepseek', operation, 'POST', 'https://api.deepseek.com/chat/completions', key, {**base, **body})
        try:
            planned = chat('plan_json', {'response_format': {'type': 'json_object'}, 'messages': [
                {'role': 'system', 'content': 'Return only JSON. Synthetic software workflow test, no medical advice.'},
                {'role': 'user', 'content': 'Split a synthetic sample registration UI explanation into exactly two tasks. '
                 'Return {"tasks":[{"task_id":"a","agent_id":"consultation_agent","description":"Explain editable draft",'
                 '"depends_on":[],"require_sources":false},{"task_id":"b","agent_id":"research_agent",'
                 '"description":"Look up synthetic SOP","depends_on":[],"require_sources":true}]}.'}]})
            Plan.model_validate(json.loads(planned['choices'][0]['message']['content']))
            self.report['deepseek']['plan_valid'] = True
            tool = {'type': 'function', 'function': {'name': 'search_knowledge', 'description': 'Read synthetic SOP only',
                'parameters': SearchArgs.model_json_schema()}}
            messages = [{'role': 'user', 'content': 'Use search_knowledge to look up the synthetic editable draft SOP. Return one tool call.'}]
            called = chat('native_tool_call', {'messages': messages, 'tools': [tool],
                          'tool_choice': {'type': 'function', 'function': {'name': 'search_knowledge'}}})
            message = called['choices'][0]['message']
            calls = message.get('tool_calls', [])
            if len(calls) != 1 or calls[0]['function']['name'] != 'search_knowledge':
                raise ValueError('TOOL_CONTRACT_INVALID')
            SearchArgs.model_validate(json.loads(calls[0]['function']['arguments']))
            self.report['deepseek']['tool_arguments_valid'] = True
            final = chat('tool_result_continuation', {'response_format': {'type': 'json_object'}, 'tools': [tool],
                'messages': [{'role': 'system', 'content': 'Return only JSON {"answer":"...","task_ids":["a","b"],'
                    '"source_ids":["synthetic-sop"]}. Explain software draft/edit/confirm/cancel from the supplied synthetic evidence.'},
                    *messages, {k: message[k] for k in ('role', 'content', 'tool_calls') if k in message},
                    {'role': 'tool', 'tool_call_id': calls[0]['id'], 'content': json.dumps({'success': True, 'documents': [
                        {'id': 'synthetic-sop', 'content': 'Drafts can be edited, confirmed, or cancelled.', 'verified': False}]})}]})
            output = Synthesis.model_validate(json.loads(final['choices'][0]['message']['content']))
            if set(output.task_ids) != {'a', 'b'} or output.source_ids != ['synthetic-sop']:
                raise ValueError('SYNTHESIS_CONTRACT_INVALID')
            self.report['deepseek'].update(status='passed', model=self.settings.deepseek_model,
                                          tool_result_continuation_valid=True)
        except RuntimeError as error:
            self.report['deepseek'].update(status='failed', safe_error_code=str(error))
        except Exception:
            self.report['deepseek'].update(status='failed', safe_error_code='CONTRACT_INVALID')

    def mem0(self):
        key = self.settings.mem0_api_key.get_secret_value()
        if not key:
            self.report['mem0'] = {'status': 'key_missing'}
            return
        user_id = 'medical-agent-smoke-' + str(uuid4())
        marker = 'Synthetic software tester prefers concise Chinese answers. Smoke marker ' + user_id
        result = self.report['mem0'] = {'status': 'running', 'synthetic_user_id': user_id, 'created_memory_ids': [],
                                     'deleted_memory_ids': [], 'extraction_tested': False}
        def request(operation, path, body=None, method='POST'):
            return self.request('mem0', operation, method, 'https://api.mem0.ai' + path, key, body)
        def search(uid):
            return request('scoped_search', '/v3/memories/search/', {'query': marker, 'filters': {'user_id': uid}, 'top_k': 3})
        try:
            added = request('add_verbatim', '/v3/memories/add/', {'messages': [{'role': 'user', 'content': marker}],
                'user_id': user_id, 'infer': False, 'enable_graph': False, 'metadata': {'synthetic': True, 'smoke': user_id}})
            result['add_status'] = added.get('status', 'unknown')
            for item in added.get('results', []):
                mid = item.get('id') or item.get('memory_id')
                if mid:
                    result['created_memory_ids'].append(str(UUID(mid)))
            found = search(user_id).get('results', [])
            matched = [item for item in found if user_id in item.get('memory', '')]
            result['retrieval_passed'] = bool(matched)
            # Recovery if response has no IDs: ONLY the marker in this unique new user scope.
            for item in matched:
                mid = str(UUID(item['id']))
                if mid not in result['created_memory_ids']:
                    result['created_memory_ids'].append(mid)
            other = search(user_id + '-other').get('results', [])
            result['isolation_passed'] = not other
            result['status'] = 'passed' if matched and not other else 'partial'
        except RuntimeError as error:
            result.update(status='failed', safe_error_code=str(error))
        except Exception:
            result.update(status='failed', safe_error_code='CONTRACT_INVALID')
        finally:
            # At most one verbatim message was written. No bulk/cascading deletion.
            for mid in result['created_memory_ids'][:1]:
                try:
                    request('delete_own_fixture', '/v1/memories/' + mid + '/?delete_linked=false', method='DELETE')
                    result['deleted_memory_ids'].append(mid)
                except Exception:
                    result['cleanup_status'] = 'failed'
            if result['deleted_memory_ids']:
                try:
                    result['cleanup_status'] = 'passed' if not search(user_id).get('results', []) else 'partial'
                except Exception:
                    result['cleanup_status'] = 'unverified'
            else:
                result.setdefault('cleanup_status', 'not_run')
            if result['status'] == 'passed' and result['cleanup_status'] != 'passed':
                result['status'] = 'partial'
            self.save()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true', help='Explicitly enable the bounded cloud smoke')
    parser.add_argument('--provider', choices=['ds', 'mem0', 'both'], default='both')
    args = parser.parse_args()
    if not args.run:
        print('not_run; cloud_requests=0; add --run to explicitly opt in')
        return
    report_path = Path(__file__).resolve().parents[2] / 'tmp' / ('provider-smoke-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.json')
    smoke = Smoke(load_settings(), report_path)
    try:
        if args.provider in ('ds', 'both'):
            smoke.ds()
            smoke.save()
            print('deepseek:', smoke.report['deepseek']['status'], flush=True)
        if args.provider in ('mem0', 'both'):
            smoke.mem0()
            print('mem0:', smoke.report['mem0']['status'], flush=True)
        smoke.save()
        print('cloud_requests:', len(smoke.report['requests']), 'report:', report_path)
        if any(smoke.report[p]['status'] not in ('passed', 'not_run') for p in ('deepseek', 'mem0')):
            raise SystemExit(2)
    finally:
        smoke.client.close()


if __name__ == '__main__':
    main()
