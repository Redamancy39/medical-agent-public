"""Paired topology benchmark. Default is offline; real worker calls require --run-real."""
import argparse
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.agent import FakeModel, Source, source_documents
from app.config import Settings, load_settings
from app.database import Store
from app.knowledge import BGEEmbedding, KnowledgeStore, LocalReranker
from app.models import Conversation, ProviderCall, User
from app.providers import DeepSeekModel, Gateway
from app.runtime_tools import RuntimeTools
from app.schemas import ChatInput
from app.workflow import SingleAgentFlow

ROOT = Path(__file__).resolve().parents[2]

class ControlledModel:
    """One fixed planner per cell; worker/synthesis use the selected provider."""
    def __init__(self, provider, topology, local_tools_only=False):
        self.provider, self.topology, self.local_tools_only = provider, topology, local_tools_only
    def plan(self, state):
        q = state['question']
        research = {'task_id': 'research', 'agent_id': 'research_agent', 'description': q,
                    'require_sources': True, 'depends_on': []}
        if self.topology == 'single':
            return {'tasks': [research]}
        return {'tasks': [research,
            {'task_id': 'explain', 'agent_id': 'consultation_agent', 'description': '根据research已给出的来源解释本题规则与限制；资料足够时直接回答，无需重复检索：' + q,
             'depends_on': ['research'], 'require_sources': True},
            {'task_id': 'review', 'agent_id': 'diagnostic_agent', 'description': '核对research已给出的来源对本题回答的支持及遗漏；资料足够时直接回答，无需重复检索，不作临床判断：' + q,
             'depends_on': ['research'], 'require_sources': True}]}
    def decide(self, state):
        if self.local_tools_only:
            state = {**state, 'allowed_tools': [n for n in state['allowed_tools'] if n == 'search_knowledge']}
        result = self.provider.decide(state)
        if isinstance(self.provider, FakeModel) and result.get('answer'):
            result['source_ids'] = list(dict.fromkeys(d['id'] for d in source_documents(state)))
        return result
    def synthesize(self, state):
        return self.provider.synthesize(state)
    def summarize(self, previous, messages):
        return self.provider.summarize(previous, messages)

def rubric_checks(answer, rubric):
    text = (answer or '').lower().replace(' ', '')
    return {r['id']: all(word.lower().replace(' ', '') in text for word in r.get('all', [])) and
            (not r.get('any') or any(word.lower().replace(' ', '') in text for word in r['any'])) for r in rubric}

def nearest_rank(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)] if values else None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-real', action='store_true', help='At most 36 DeepSeek HTTP requests, no Mem0 or web')
    parser.add_argument('--local-tools-only', action='store_true', help='Both topologies receive only the local KB tool; a separate experimental condition')
    args = parser.parse_args()
    data_path = ROOT / 'backend/evaluation/cases-v1.json'
    dataset_bytes = data_path.read_bytes()
    dataset = json.loads(dataset_bytes)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S') + '-' + uuid4().hex[:6]
    output = ROOT / 'tmp' / ('g-eval-' + ('real-' if args.run_real else 'offline-') + stamp)
    output.mkdir(parents=True)
    settings = load_settings() if args.run_real else Settings(jwt_secret='synthetic-evaluation-' + 'x' * 40)
    settings = settings.model_copy(update={'database_path': output / 'app.db', 'knowledge_path': output / 'knowledge.db', 'deepseek_enabled': args.run_real,
        'mem0_enabled': False, 'knowledge_enabled': args.run_real, 'web_search_enabled': False,
        'maintenance_enabled': False, 'max_model_calls': 16, 'max_tool_calls': 5,
        'max_worker_model_calls': 4, 'max_worker_tool_calls': 2, 'max_worker_iterations': 4,
        'run_timeout_seconds': 90, 'step_timeout_seconds': 25, 'model_max_tokens': 768,
        'cloud_model_request_limit': 36, 'schema_repair_limit': 1 if args.run_real else 0})
    store = Store(settings.database_path)
    store.initialize()
    gateway = Gateway(store, settings) if args.run_real else None
    provider = DeepSeekModel(gateway, settings) if args.run_real else FakeModel()
    embedding = BGEEmbedding(settings.embedding_cache) if args.run_real else None
    reranker = LocalReranker(settings.reranker_path) if args.run_real else None
    tools = RuntimeTools(KnowledgeStore(settings.knowledge_path, embedding, reranker)) if args.run_real else None
    documents_bytes = (ROOT / 'backend/knowledge/synthetic-documents.json').read_bytes()
    if tools:
        tools.knowledge.import_documents(json.loads(documents_bytes))
    report = {'dataset_version': dataset['dataset_version'], 'dataset_sha256': hashlib.sha256(dataset_bytes).hexdigest(),
              'mode': 'cloud_real' if args.run_real else 'offline_fake', 'synthetic_only': True,
              'method': 'same questions, fresh sessions, fixed topology plans, same model/tool caps; planning is deterministic and counts one budget attempt but makes no HTTP call',
              'limits': {'model_attempts_per_run': 16, 'tools_per_run': 5, 'model_attempts_per_worker': 4,
                         'tools_per_worker': 2, 'output_tokens_per_request': 768, 'cloud_requests_global': 36 if args.run_real else 0},
              'human_review': 'not_run', 'clinical_quality': 'not_evaluated', 'cells': []}
    report['tool_policy'] = 'local_kb_only' if args.local_tools_only else 'normal_readonly_tools'
    report['knowledge_sha256'] = hashlib.sha256(documents_bytes).hexdigest() if args.run_real else None
    report['retrieval'] = 'local_bge_with_user_reranker' if args.run_real else 'fake_fixture'
    report['model'] = settings.deepseek_model if args.run_real else 'fake'
    report['thinking_enabled'] = settings.deepseek_thinking_enabled if args.run_real else False
    report['implementation_sha256'] = {name: hashlib.sha256((ROOT / 'backend/app' / name).read_bytes()).hexdigest()
                                       for name in ('workflow.py', 'providers.py', 'multitask.py')}
    def save():
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    flow = None
    try:
        with store.sessions.begin() as db:
            user = User(username='synthetic_evaluation', password_hash='not-a-login-account')
            db.add(user); db.flush(); uid = user.id
        for case_index, case in enumerate(dataset['cases']):
            # Alternate order to limit a systematic single-first bias.
            order = ('single', 'multi') if case_index % 2 == 0 else ('multi', 'single')
            for topology in order:
                with store.sessions.begin() as db:
                    conversation = Conversation(user_id=uid, title=case['id'] + '-' + topology)
                    db.add(conversation); db.flush(); sid = conversation.id
                flow = SingleAgentFlow(store, settings, ControlledModel(provider, topology, args.local_tools_only), tools=tools)
                start = time.monotonic()
                result = flow.submit(uid, sid, ChatInput(question=case['question'], request_id=uuid4())).model_dump(mode='json')
                elapsed = time.monotonic() - start
                with store.sessions() as db:
                    calls = [{'provider': c.provider, 'operation': c.operation, 'status': c.status, 'safe_error_code': c.safe_error_code,
                              'usage': json.loads(c.usage_json)} for c in db.scalars(select(ProviderCall).where(ProviderCall.run_id == result['run_id']))]
                snapshot = flow.snapshot(result['run_id']).values
                observed_tasks = result['task_count'] if result['task_results'] else len(snapshot.get('plan', {}).get('tasks', []))
                observed_roles = result['distinct_agent_count'] if result['task_results'] else int(bool(result['agent_id'] and result['worker_iterations']))
                topology_ok = observed_tasks == (1 if topology == 'single' else 3) and observed_roles == (1 if topology == 'single' else 3)
                try:
                    for source in result['sources']:
                        Source.model_validate(source)
                    source_ok = bool(result['sources']) and len({s['id'] for s in result['sources']}) == len(result['sources'])
                except Exception:
                    source_ok = False
                cell = {'case_id': case['id'], 'topology': topology, 'question': case['question'], 'elapsed_seconds': round(elapsed, 4),
                        'result': result, 'observed_tasks': observed_tasks, 'observed_roles': observed_roles,
                        'topology_ok': topology_ok, 'source_contract_ok': source_ok,
                        'rubric_presence': rubric_checks(result['answer'], case['rubric']) if args.run_real else None,
                        'rubric_method': 'lexical_presence_only_not_semantic_correctness', 'http_calls': calls,
                        'token_usage': {k: sum(c['usage'].get(k, 0) for c in calls) for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')}}
                report['cells'].append(cell); save()
                print(case['id'] + '/' + topology + ': ' + str(result['result_status']), flush=True)
                # Flow owns its tools: reopen read-only KB for the next cell.
                flow.close(); flow = None
                if args.run_real:
                    tools = RuntimeTools(KnowledgeStore(settings.knowledge_path, embedding, reranker))
        report['by_topology'] = {}
        for topology in ('single', 'multi'):
            cells = [c for c in report['cells'] if c['topology'] == topology]
            report['by_topology'][topology] = {'denominator': len(cells), 'completed': sum(c['result']['result_status'] == 'completed' for c in cells),
                'topology_ok': sum(c['topology_ok'] for c in cells), 'source_contract_ok': sum(c['source_contract_ok'] for c in cells),
                'latency_p50_seconds': nearest_rank([c['elapsed_seconds'] for c in cells], .5),
                'latency_p95_seconds': nearest_rank([c['elapsed_seconds'] for c in cells], .95),
                'model_attempts': sum(c['result']['model_calls'] or 0 for c in cells),
                'tool_attempts': sum(c['result']['tool_calls'] or 0 for c in cells),
                'http_requests': sum(len(c['http_calls']) for c in cells),
                'total_tokens': sum(c['token_usage']['total_tokens'] for c in cells)}
        report['status'] = 'passed' if len(report['cells']) == 6 and all(c['topology_ok'] and c['source_contract_ok'] and c['result']['result_status'] == 'completed' for c in report['cells']) else 'failed'
        save()
        print(json.dumps({'status': report['status'], 'report': str(output / 'report.json'), 'http_requests': gateway.counts if gateway else {}}))
    finally:
        if flow: flow.close()
        if tools: tools.close()
        if gateway: gateway.close()
        store.engine.dispose()
    if report.get('status') != 'passed': raise SystemExit(2)

if __name__ == '__main__':
    main()
