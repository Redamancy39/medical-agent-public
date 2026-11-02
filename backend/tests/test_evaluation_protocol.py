"""Protocol/cache/auth/artifact checks use synthetic questions and fake providers."""
from copy import deepcopy
import csv
import json
from types import SimpleNamespace

import httpx
import pytest

from scripts.eval.evaluation_protocol import (
    DEFAULT_DATASET, METHODS, EvaluationCache, EvaluatorAuth, build_protocol, digest,
    generate_candidates, judge_candidates, load_cases, summarize,
    evaluation_status,
)
from scripts.eval.evaluation_artifacts import export_artifacts


@pytest.fixture
def cases():
    return [{'id': 'synthetic-1', 'split': 'dev', 'question': '完整的合成问题？',
        'reference_points': ['Reference must never enter generation.'], 'category': 'synthetic'}]


@pytest.fixture
def protocol(cases):
    return build_protocol(cases, code_sha256='code-v1', corpus_sha256='corpus-v1')


def candidate(answer='短', status='completed'):
    return {'answer': answer, 'sources': [], 'latency': None, 'total_tokens': None,
        'run_data': {'result_status': status, 'safe_error_code': None}}


@pytest.mark.parametrize('field,value', [
    ('candidate_model', 'deepseek-flash'), ('judge_model', 'another-judge'),
    ('code_sha256', 'code-v2'), ('corpus_sha256', 'corpus-v2'), ('max_tokens', 2048),
    ('generation_temperature', 0.0), ('dataset_sha256', 'another-dataset'),
])
def test_cache_never_mixes_protocols(tmp_path, protocol, field, value):
    path = tmp_path / 'state.json'
    cache = EvaluationCache(path, protocol)
    cache.append('generate', 'ours', 'synthetic-1', candidate())
    before = path.read_bytes()
    changed = {**protocol, field: value}
    with pytest.raises(ValueError, match='CACHE_PROTOCOL_MISMATCH'):
        EvaluationCache(path, changed)
    assert path.read_bytes() == before


def test_legacy_cache_is_not_silently_reused_or_overwritten(tmp_path, protocol):
    path = tmp_path / 'state.json'
    path.write_text(json.dumps({'detailed_results': {'ours': [candidate()]}}), encoding='utf-8')
    before = path.read_bytes()
    with pytest.raises(ValueError, match='CACHE_PROTOCOL_MISMATCH'):
        EvaluationCache(path, protocol)
    assert path.read_bytes() == before


def test_cache_tampering_with_case_binding_is_rejected(tmp_path, protocol):
    path = tmp_path / 'state.json'
    cache = EvaluationCache(path, protocol)
    cache.append('generate', 'ours', 'synthetic-1', candidate())
    raw = json.loads(path.read_text(encoding='utf-8'))
    raw['attempts'][0]['case_id'] = 'different-case'
    path.write_text(json.dumps(raw), encoding='utf-8')
    with pytest.raises(ValueError, match='CACHE_RECORD_HASH_INVALID'):
        EvaluationCache(path, protocol)


@pytest.mark.parametrize('status', ['completed', 'partial'])
def test_all_methods_cache_short_and_partial_answers_equally(tmp_path, cases, protocol, status):
    calls = []
    cache = EvaluationCache(tmp_path / 'state.json', protocol)
    generators = {m: lambda q, m=m: (calls.append((m, q)), candidate(status=status))[1] for m in METHODS}
    first = generate_candidates(cases, cache, generators)
    assert len(calls) == 3 and all(q == cases[0]['question'] for _, q in calls)
    assert all(first[m][0]['execution_origin'] == 'generated' for m in METHODS)
    reloaded = EvaluationCache(cache.path, protocol)
    second = generate_candidates(cases, reloaded, {m: lambda q: pytest.fail('Must use cache.') for m in METHODS})
    assert all(second[m][0]['answer'] == '短' and second[m][0]['execution_origin'] == 'cache' for m in METHODS)


def test_infrastructure_retries_are_bounded_and_keep_every_attempt(tmp_path, cases, protocol):
    cache = EvaluationCache(tmp_path / 'state.json', protocol)
    calls = []
    generators = {m: lambda q, m=m: (calls.append(m), candidate('', 'failed'))[1] for m in METHODS}
    generate_candidates(cases, cache, generators)
    assert len(calls) == 6 and all(calls.count(m) == 2 for m in METHODS)
    generate_candidates(cases, cache, {m: lambda q: pytest.fail('Budget already exhausted.') for m in METHODS})
    assert len(cache.data['attempts']) == 6


def test_low_judge_scores_do_not_trigger_answer_or_judge_regeneration(tmp_path, cases, protocol):
    cache = EvaluationCache(tmp_path / 'state.json', protocol)
    candidates = generate_candidates(cases, cache, {m: lambda q: candidate() for m in METHODS})
    calls = []
    judge = SimpleNamespace(evaluate_single=lambda *args: (calls.append(1),
        {'judge_status': 'success', 'total_score': 10, 'verdict': 'FAIL', 'reason': 'Synthetic low score.'})[1])
    first = judge_candidates(cases, candidates, cache, judge)
    second = judge_candidates(cases, candidates, EvaluationCache(cache.path, protocol), judge)
    assert len(calls) == 3
    assert first['ours'][0]['question'] == cases[0]['question']
    assert second['ours'][0]['judge_execution_origin'] == 'cache'
    assert second['ours'][0]['case_snapshot']['reference_points'] == cases[0]['reference_points']


def test_generation_failure_is_retained_without_charging_judge(tmp_path, cases, protocol):
    cache = EvaluationCache(tmp_path / 'state.json', protocol)
    candidates = generate_candidates(cases, cache, {m: lambda q: candidate('', 'failed') for m in METHODS})
    judge = SimpleNamespace(evaluate_single=lambda *args: pytest.fail('No answer to judge.'))
    rows = judge_candidates(cases, candidates, cache, judge)
    for method in METHODS:
        assert rows[method][0]['eval_res']['judge_status'] == 'not_run'
        assert summarize(rows[method], 1)['pass_rate_all_cases'] == 0
        assert summarize(rows[method], 1)['mean_total'] is None


def test_judge_failure_is_separate_from_medical_score_and_denominators():
    success = {'case_id': 'a', 'generation': candidate(status='partial'),
        'eval_res': {'judge_status': 'success', 'total_score': 90, 'verdict': 'PASS', 'safety_score': 20}}
    failed = {'case_id': 'b', 'generation': candidate('', 'failed'),
        'eval_res': {'judge_status': 'failed', 'total_score': None, 'verdict': None}}
    summary = summarize([success, failed], 2)
    assert summary['mean_total'] == 90
    assert summary['judge_success_count'] == 1 and summary['judge_success_rate'] == 0.5
    assert summary['pass_rate_all_cases'] == 0.5 and summary['pass_rate_judged'] == 1
    assert summary['backend_complete_rate'] == 0 and summary['over_deletion_rate'] is None


@pytest.mark.parametrize('judge_status,inputs_stable,expected', [
    ('success', True, 'completed'), ('failed', True, 'partial'),
    ('not_run', True, 'partial'), ('success', False, 'inputs_changed'),
])
def test_pipeline_completion_does_not_hide_unjudged_cases(judge_status, inputs_stable, expected):
    results = {'ours': [{'eval_res': {'judge_status': judge_status}}]}
    assert evaluation_status(results, inputs_stable) == expected


class AuthClient:
    def __init__(self, code=401, identity='same-user'):
        self.calls, self.request_count, self.code, self.identity = [], 0, code, identity

    def post(self, path, **kwargs):
        self.calls.append((path, deepcopy(kwargs)))
        if path == '/auth/login':
            return httpx.Response(200, json={'access_token': 'synthetic-new-token'})
        if path == '/sessions':
            self.request_count += 1
            return httpx.Response(self.code if self.request_count == 1 else 201, json={'id': 'session'})
        pytest.fail('Must never register a replacement user.')

    def get(self, path, **kwargs):
        self.calls.append((path, deepcopy(kwargs)))
        assert path == '/auth/me'
        return httpx.Response(200, json={'id': self.identity})


def test_401_reauthenticates_same_identity_and_reuses_request_payload():
    client = AuthClient()
    auth = EvaluatorAuth(client, 'same-username', 'synthetic-password')
    auth.user_id, auth.headers = 'same-user', {'Authorization': 'synthetic-old-token'}
    result = auth.post('/sessions', json={'request_id': 'unchanged', 'question': '合成问题'})
    assert result.status_code == 201
    assert [p for p, _ in client.calls] == ['/sessions', '/auth/login', '/auth/me', '/sessions']
    assert client.calls[0][1]['json'] == client.calls[-1][1]['json']
    assert client.calls[1][1]['json']['username'] == 'same-username'


def test_non_401_never_changes_identity_or_retries():
    client = AuthClient(code=503)
    auth = EvaluatorAuth(client, 'same-username', 'synthetic-password')
    assert auth.post('/sessions', json={}).status_code == 503
    assert len(client.calls) == 1


def test_identity_change_on_refresh_is_rejected():
    client = AuthClient(identity='another-user')
    auth = EvaluatorAuth(client, 'same-username', 'synthetic-password')
    auth.user_id = 'same-user'
    with pytest.raises(ValueError, match='IDENTITY_CHANGED'):
        auth.post('/sessions', json={})
    assert client.request_count == 1


def test_default_cases_are_dev_only():
    assert DEFAULT_DATASET.name == 'dev.jsonl'
    assert all(c['split'] == 'dev' for c in load_cases())


def test_question_answer_scores_and_reasons_are_exported_verbatim(tmp_path, cases, protocol):
    cache = EvaluationCache(tmp_path / 'state.json', protocol)
    answer = '完整合成回答。' * 100
    candidates = generate_candidates(cases, cache, {m: lambda q: candidate(answer) for m in METHODS})
    judge = SimpleNamespace(evaluate_single=lambda *args: {'judge_status': 'success',
        'total_score': 88, 'verdict': 'PASS', 'reason': '逐项合成原因', 'cot_analysis': {'coverage_analysis': '覆盖说明'}})
    rows = judge_candidates(cases, candidates, cache, judge)
    paths = export_artifacts(tmp_path / 'result', {'detailed_results': rows, 'protocol_sha256': digest(protocol)}, cache.data['attempts'])
    records = [json.loads(line) for line in open(paths['case_jsonl'], encoding='utf-8')]
    assert len(records) == 3 and all(r['generation']['answer'] == answer for r in records)
    assert records[0]['question'] == cases[0]['question']
    assert records[0]['eval_res']['reason'] == '逐项合成原因'
    with open(paths['summary_csv'], encoding='utf-8-sig', newline='') as stream:
        csv_rows = list(csv.DictReader(stream))
    assert len(csv_rows) == 3 and csv_rows[0]['answer'] == answer
    assert '覆盖说明' in csv_rows[0]['dimension_reasons_json']
    assert len(open(paths['attempts_jsonl'], encoding='utf-8').readlines()) == 6


def test_application_records_requested_and_response_models(tmp_path):
    from app.config import Settings
    from app.database import Store
    from app.models import ProviderCall
    from app.providers import Gateway, DeepSeekModel
    from sqlalchemy import select
    settings = Settings(database_path=tmp_path / 'provider.db', jwt_secret='synthetic-'+'x'*40,
        deepseek_model='deepseek-chat', deepseek_temperature=0.2, deepseek_api_key='synthetic-key')
    store = Store(settings.database_path)
    store.initialize()

    def handler(request):
        body = json.loads(request.content)
        assert body['model'] == 'deepseek-chat' and body['temperature'] == 0.2
        return httpx.Response(200, json={'model': 'returned-snapshot',
            'choices': [{'finish_reason': 'stop', 'message': {'content': '合成输出'}}]})

    gateway = Gateway(store, settings, transport=httpx.MockTransport(handler))
    try:
        DeepSeekModel(gateway, settings)._chat('test', [{'role': 'user', 'content': '合成问题'}])
        with store.sessions() as db:
            usage = json.loads(db.scalar(select(ProviderCall)).usage_json)
        assert usage['requested_model'] == 'deepseek-chat' and usage['response_model'] == 'returned-snapshot'
        assert 'total_tokens' not in usage
    finally:
        gateway.close()
        store.engine.dispose()
