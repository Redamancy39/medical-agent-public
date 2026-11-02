"""Versioned evaluation state, bounded retries and honest denominators."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import statistics
import subprocess
from uuid import uuid4

METHODS = ('zero_shot', 'naive_rag', 'ours')
ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET = ROOT / 'backend/evaluation/medical-v1/dev.jsonl'
DEFAULT_MODEL = 'deepseek-chat'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()


def load_cases(path=DEFAULT_DATASET):
    path = Path(path)
    text = path.read_text(encoding='utf-8')
    cases = [json.loads(line) for line in text.splitlines() if line.strip()] if path.suffix == '.jsonl' else json.loads(text)
    if (not isinstance(cases, list) or not cases or any(not isinstance(c, dict)
            or not isinstance(c.get('id'), str) or not c['id'].strip()
            or not isinstance(c.get('question'), str) or not c['question'].strip() for c in cases)
            or len({c['id'] for c in cases}) != len(cases)):
        raise ValueError('DATASET_SCHEMA_INVALID')
    return cases


def tree_fingerprint(roots):
    hashes = {}
    for root in map(Path, roots):
        for path in sorted(root.rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts:
                hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest(hashes)


def index_fingerprint(path):
    path = Path(path)
    if path.is_file(): return hashlib.sha256(path.read_bytes()).hexdigest()
    if path.is_dir():
        # Embedded Milvus holds its zero-byte process LOCK exclusively on Windows.
        # All actual manifest, schema, vector, delta and index data remain hashed.
        return digest({str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob('*')) if p.is_file() and p.name != 'LOCK'})
    return None


def build_protocol(cases, *, candidate_model=DEFAULT_MODEL, judge_model=DEFAULT_MODEL, max_tokens=4096,
                   settings=None, code_sha256=None, corpus_sha256=None):
    code_sha256 = code_sha256 or tree_fingerprint([ROOT / 'backend/app', ROOT / 'backend/scripts/eval'])
    corpus_sha256 = corpus_sha256 or tree_fingerprint([ROOT / 'backend/knowledge'])
    names = ('knowledge_profile', 'knowledge_enabled', 'reranker_enabled', 'reranker_device',
        'reranker_threshold', 'search_top_k', 'reviewer_max_tokens', 'schema_repair_limit', 'max_model_calls',
        'max_tool_calls', 'max_worker_model_calls', 'max_worker_tool_calls', 'max_parallel_tasks',
        'max_worker_iterations', 'medical_reviewer_enabled', 'run_timeout_seconds', 'step_timeout_seconds',
        'provider_timeout_seconds', 'max_context_chars')
    runtime = {k: getattr(settings, k) for k in names} if settings else {}
    index_sha = None
    if settings and settings.knowledge_enabled:
        path = settings.knowledge_database
        index_sha = {suffix: index_fingerprint(p)
            for suffix in ('', '-wal') if (p := Path(str(path) + suffix))}
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True, timeout=5).strip()
    except (OSError, subprocess.SubprocessError):
        commit = None
    packages = {}
    for name in ('httpx', 'pydantic', 'langgraph', 'pymilvus', 'torch', 'transformers'):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {'schema_version': 'medical-evaluation-v2', 'dataset_sha256': digest(cases),
        'case_hashes': {c['id']: digest(c) for c in cases},
        'dataset_role': ('development' if all(c.get('split') == 'dev' for c in cases) else
            'historical_regression' if all(c.get('split') == 'historical_regression' for c in cases) else 'regression_or_heldout'),
        'candidate_model': candidate_model, 'judge_model': judge_model,
        'generation_temperature': 0.2, 'judge_temperature': 0.0, 'max_tokens': max_tokens,
        'judge_max_tokens': 1200, 'max_attempts_per_phase': 2,
        'code_sha256': code_sha256, 'corpus_sha256': corpus_sha256, 'index_sha256': index_sha,
        'git_commit': commit, 'packages': packages, 'runtime': runtime,
        'memory_policy': 'disabled_isolated_case_sessions', 'web_policy': 'disabled_fixed_local_corpus',
        'comparison_type': 'system_bundles_not_multiagent_causal_ablation',
        'retrieval_policy': 'same_local_search_top5_and_original_context; worker_queries_may_differ',
        'naive_knowledge_policy': 'retrieval_only', 'zero_shot_knowledge_policy': 'parametric',
        'clinical_review': 'not_run', 'judge_bias_validation': 'not_run'}


def generation_status(result):
    status = (result.get('run_data') or {}).get('result_status', result.get('status'))
    if status in ('completed', 'partial') and isinstance(result.get('answer'), str) and result['answer'].strip():
        return status
    return 'failed'


class EvaluationCache:
    def __init__(self, path, protocol):
        self.path, self.protocol = Path(path), deepcopy(protocol)
        self.fingerprint = digest(protocol)
        self.data = {'protocol': self.protocol, 'protocol_sha256': self.fingerprint, 'attempts': []}
        if self.path.exists():
            saved = json.loads(self.path.read_text(encoding='utf-8'))
            if saved.get('protocol_sha256') != self.fingerprint or saved.get('protocol') != protocol:
                raise ValueError('CACHE_PROTOCOL_MISMATCH')
            self.data = saved
            for row in self.data['attempts']:
                if (row['result_sha256'] != digest(row['result'])
                        or row.get('record_sha256') != digest({k: v for k, v in row.items() if k != 'record_sha256'})):
                    raise ValueError('CACHE_RECORD_HASH_INVALID')

    def attempts(self, phase, method, case_id, binding=None):
        return [r for r in self.data['attempts'] if (r['phase'], r['method'], r['case_id'], r['binding'])
            == (phase, method, case_id, binding)]

    def latest(self, phase, method, case_id, binding=None):
        rows = self.attempts(phase, method, case_id, binding)
        return deepcopy(rows[-1]['result']) if rows else None

    def pending(self, phase, method, case_id, binding=None):
        rows = self.attempts(phase, method, case_id, binding)
        if len(rows) >= self.protocol['max_attempts_per_phase']:
            return False
        if not rows:
            return True
        result = rows[-1]['result']
        # Short answers, partial answers and low scores never trigger selective regeneration.
        return (generation_status(result) == 'failed' if phase == 'generate'
            else result.get('judge_status') != 'success')

    def append(self, phase, method, case_id, result, binding=None):
        if method not in METHODS or case_id not in self.protocol['case_hashes'] or phase not in ('generate', 'judge'):
            raise ValueError('CACHE_CASE_INVALID')
        row = {'phase': phase, 'method': method, 'case_id': case_id, 'binding': binding,
            'attempt': len(self.attempts(phase, method, case_id, binding))+1,
            'recorded_at': datetime.now(timezone.utc).isoformat(),
            'result_sha256': digest(result), 'result': deepcopy(result)}
        row['record_sha256'] = digest(row)
        self.data['attempts'].append(row)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + '.' + uuid4().hex + '.tmp')
        temporary.write_text(json.dumps(self.data, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
        temporary.replace(self.path)


class EvaluatorAuth:
    """Ephemeral credentials; 401 retry uses the same identity and request payload."""
    def __init__(self, client, username, password):
        self.client, self.username, self.password = client, username, password
        self.headers, self.user_id = {}, None

    def login(self, *, register=False):
        credentials = {'username': self.username, 'password': self.password}
        if register:
            response = self.client.post('/auth/register', json=credentials)
            if response.status_code != 201:
                raise ValueError('EVALUATOR_REGISTRATION_FAILED')
        response = self.client.post('/auth/login', json=credentials)
        if response.status_code != 200:
            raise ValueError('EVALUATOR_LOGIN_FAILED')
        headers = {'Authorization': 'Bearer ' + response.json()['access_token']}
        identity = self.client.get('/auth/me', headers=headers)
        if identity.status_code != 200 or not identity.json().get('id'):
            raise ValueError('EVALUATOR_IDENTITY_UNVERIFIED')
        user_id = identity.json()['id']
        if self.user_id is not None and user_id != self.user_id:
            raise ValueError('EVALUATOR_IDENTITY_CHANGED')
        self.user_id, self.headers = user_id, headers

    def request(self, method, path, **kwargs):
        response = getattr(self.client, method)(path, headers=dict(self.headers), **kwargs)
        if response.status_code == 401:
            self.login()
            response = getattr(self.client, method)(path, headers=dict(self.headers), **kwargs)
        return response

    def post(self, path, **kwargs):
        return self.request('post', path, **kwargs)

    def get(self, path, **kwargs):
        return self.request('get', path, **kwargs)


def generate_candidates(cases, cache, generators):
    results = {m: [] for m in METHODS}
    for index, case in enumerate(cases):
        # Rotate the fixed order, without using outcomes to choose which method runs next.
        order = METHODS[index % 3:] + METHODS[:index % 3]
        for method in order:
            before_count = len(cache.attempts('generate', method, case['id']))
            while cache.pending('generate', method, case['id']):
                try:
                    result = generators[method](case['question'])
                except Exception:
                    result = {'answer': '', 'sources': [], 'latency': None, 'total_tokens': None,
                        'run_data': {'result_status': 'failed', 'safe_error_code': 'GENERATION_EXECUTION_FAILED'}}
                result['generation_status'] = generation_status(result)
                cache.append('generate', method, case['id'], result)
            result = cache.latest('generate', method, case['id'])
            reused = len(cache.attempts('generate', method, case['id'])) == before_count
            results[method].append({**result, 'case_id': case['id'], 'execution_origin': 'cache' if reused else 'generated'})
    return results


def judge_candidates(cases, candidates, cache, judge):
    case_map = {c['id']: c for c in cases}
    results = {m: [] for m in METHODS}
    for method in METHODS:
        for item in candidates[method]:
            cid = item['case_id']
            binding = digest({'answer': item.get('answer'), 'sources': item.get('sources')})
            if generation_status(item) == 'failed':
                judgment = {'judge_status': 'not_run', 'judge_error_code': 'GENERATION_FAILED',
                    'total_score': None, 'verdict': None}
            else:
                before_count = len(cache.attempts('judge', method, cid, binding))
                while cache.pending('judge', method, cid, binding):
                    try:
                        judgment = judge.evaluate_single(case_map[cid], item['answer'], item.get('sources', []))
                    except Exception:
                        judgment = {'judge_status': 'failed', 'judge_error_code': 'JUDGE_EXECUTION_FAILED',
                            'total_score': None, 'verdict': None}
                    cache.append('judge', method, cid, judgment, binding)
                judgment = cache.latest('judge', method, cid, binding)
            results[method].append({'case_id': cid, 'category': case_map[cid].get('category', ''),
                'question': case_map[cid]['question'], 'case_snapshot': deepcopy(case_map[cid]),
                'method': method, 'generation': item, 'eval_res': judgment,
                'judge_execution_origin': 'not_run' if generation_status(item) == 'failed' else
                    'cache' if len(cache.attempts('judge', method, cid, binding)) == before_count else 'judged'})
    return results


def mean_known(values):
    values = [v for v in values if type(v) in (int, float) and math.isfinite(v)]
    return round(statistics.mean(values), 3) if values else None


def summarize(rows, expected_cases):
    judged = [r for r in rows if r['eval_res'].get('judge_status') == 'success']
    generations = [r['generation'] for r in rows]
    counts = Counter(generation_status(g) for g in generations)
    statuses = Counter(r['eval_res'].get('judge_status', 'not_run') for r in rows)
    passed = sum(r['eval_res'].get('verdict') == 'PASS' for r in judged)
    reviewed = [c for g in generations for c in (g.get('run_data') or {}).get('claim_reviews', [])
        if c.get('kind') == 'medical_fact']
    return {'expected_cases': expected_cases, 'observed_cases': len(rows), 'judge_success_count': len(judged),
        'generation_status_counts': dict(counts), 'judge_status_counts': dict(statuses),
        'backend_complete_rate': counts['completed']/expected_cases if expected_cases else None,
        'judge_success_rate': len(judged)/expected_cases if expected_cases else None,
        'pass_rate_all_cases': passed/expected_cases if expected_cases else None,
        'pass_rate_judged': passed/len(judged) if judged else None,
        'safety_pass_rate_judged': sum(r['eval_res'].get('safety_score', 0) >= 15 for r in judged)/len(judged) if judged else None,
        'citation_presence_rate': sum(bool(g.get('sources')) for g in generations)/expected_cases if expected_cases else None,
        'mean_total': mean_known([r['eval_res'].get('total_score') for r in judged]),
        'mean_scores': {k: mean_known([r['eval_res'].get(k) for r in judged])
            for k in ('action_score', 'coverage_score', 'safety_score', 'grounding_score')},
        'mean_latency_seconds': mean_known([g.get('latency') for g in generations]),
        'model_reviewed_fact_count': len(reviewed),
        'model_omitted_fact_count': sum(c.get('final_start') is None for c in reviewed),
        'clinical_accuracy': None, 'over_deletion_rate': None, 'professional_review': 'not_run'}


def attempt_usage_totals(attempts):
    result = {}
    for phase in ('generate', 'judge'):
        rows = [r['result'] for r in attempts if r['phase'] == phase]
        known = [r['total_tokens'] for r in rows if type(r.get('total_tokens')) is int and r['total_tokens'] >= 0]
        result[phase] = {'attempts': len(rows), 'known_token_subtotal': sum(known),
            'unknown_token_attempts': len(rows)-len(known),
            'total_tokens': sum(known) if len(known) == len(rows) else None}
    return result


def evaluation_status(results, inputs_stable):
    if not inputs_stable:
        return 'inputs_changed'
    return 'completed' if all(r['eval_res'].get('judge_status') == 'success'
        for rows in results.values() for r in rows) else 'partial'
