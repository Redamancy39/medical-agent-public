"""End-to-end evaluator tests: temporary SQL, synthetic corpus, mocked HTTP only."""
import json

from fastapi.testclient import TestClient
import httpx
from sqlalchemy import func, select

from app.config import Settings
from app.main import create_app
from app.models import User
from scripts.eval.evaluation_protocol import EvaluatorAuth, load_cases
from scripts.eval import run_full_50_cases_llm_judge as pipeline


def test_versioned_pipeline_exports_full_details_and_resumes_without_model_calls(tmp_path, monkeypatch):
    import app.main as application_module
    dataset = tmp_path / 'synthetic-dev.jsonl'
    cases = [{'id': f'synthetic-{i}', 'split': 'dev', 'question': f'完整合成问题{i}？',
        'reference_points': ['合成参考要点'], 'category': 'synthetic'} for i in range(2)]
    dataset.write_text('\n'.join(json.dumps(c, ensure_ascii=False) for c in cases), encoding='utf-8')

    class Knowledge:
        def __init__(self, *args, **kwargs):
            pass

        def search(self, query, limit=5):
            return [{'id': 's0', 'source': 'synthetic', 'content': '完整合成资料，仅用于结构测试。', 'verified': False}]

        def close(self):
            pass

    monkeypatch.setattr(application_module, 'KnowledgeStore', Knowledge)
    monkeypatch.setattr(application_module, 'BGEEmbedding', lambda *args: None)
    monkeypatch.setattr(pipeline, 'load_settings', lambda: (_ for _ in ()).throw(AssertionError('No private settings.')))
    seen = []

    def handler(request):
        body = json.loads(request.content)
        seen.append(body)
        assert body['model'] == 'deepseek-chat'
        if 'Medical LLM Judge' in body['messages'][0]['content']:
            assert body['temperature'] == 0.0
            refs = json.loads(body['messages'][1]['content']).get('reference_points', [])
            message = {'content': json.dumps({'action_score': 25, 'coverage_score': 30,
                'action_checks': {'response_alignment': 'direct', 'instruction_following': 'met',
                    'urgency_handling': 'appropriate', 'note': '合成动作核对'},
                'safety_score': 20, 'grounding_score': 16, 'reason': '合成评分理由',
                'reference_checks': [{'index': i, 'status': 'covered', 'note': '合成核对'} for i in range(len(refs))],
                'cot_analysis': {'coverage_analysis': '合成逐项核对'}})}
        elif body.get('tools'):
            assert body['temperature'] == 0.2
            functions = {t['function']['name']: t['function'] for t in body['tools']}
            if 'submit_plan' in functions:
                name, output = 'submit_plan', {'tasks': [{'task_id': 'one', 'agent_id': 'research_agent',
                    'description': '检索合成资料', 'require_sources': True}]}
            elif functions['final_response']['parameters']['properties']['source_ids']['items'].get('enum'):
                name, output = 'final_response', {'answer': '完整合成回答，来源只用于结构测试。', 'source_ids': ['s0']}
            else:
                name, output = 'search_knowledge', {'query': 'synthetic'}
            message = {'content': None, 'tool_calls': [{'id': 'synthetic-call', 'type': 'function',
                'function': {'name': name, 'arguments': json.dumps(output)}}]}
        else:
            assert body['temperature'] == 0.2 and body['max_tokens'] == 4096
            message = {'content': '完整合成基线回答，仅用于结构测试。'}
        return httpx.Response(200, json={'model': 'synthetic-response-version',
            'choices': [{'finish_reason': 'tool_calls' if message.get('tool_calls') else 'stop', 'message': message}],
            'usage': {'prompt_tokens': 12, 'completion_tokens': 6, 'total_tokens': 18}})

    settings = Settings(database_path=tmp_path / 'must-not-use.db', jwt_secret='synthetic-'+'x'*40,
        deepseek_api_key='synthetic-key', deepseek_enabled=True, knowledge_enabled=True,
        knowledge_path=tmp_path / 'synthetic-index.db', knowledge_profile='medical',
        medical_reviewer_enabled=False, maintenance_enabled=False)
    output = tmp_path / 'output'
    first = pipeline.run_evaluation(dataset=dataset, settings=settings, output_dir=output,
        transport=httpx.MockTransport(handler))
    assert first['status'] == 'completed' and first['input_snapshot_stable']
    assert first['attempt_counts'] == {'generate': 6, 'judge': 6}
    assert not (tmp_path / 'must-not-use.db').exists()
    ours = first['detailed_results']['ours'][0]
    assert ours['question'] == cases[0]['question']
    assert ours['generation']['response_models'] == ['synthetic-response-version']
    assert ours['generation']['total_tokens'] == 54
    assert ours['eval_res']['reason'] == '合成评分理由'
    assert first['summary']['ours']['backend_complete_rate'] == 1
    snapshot = json.loads((output / 'report.json').read_text(encoding='utf-8'))
    assert snapshot['detailed_results']['ours'][0]['generation']['answer'] == ours['generation']['answer']
    assert len((output / 'cases.jsonl').read_text(encoding='utf-8').splitlines()) == 6
    before = len(seen)
    second = pipeline.run_evaluation(dataset=dataset, settings=settings, output_dir=output,
        transport=httpx.MockTransport(handler))
    assert len(seen) == before
    assert all(r['generation']['execution_origin'] == 'cache'
        for rows in second['detailed_results'].values() for r in rows)
    assert all(r['judge_execution_origin'] == 'cache'
        for rows in second['detailed_results'].values() for r in rows)


def test_real_401_refresh_keeps_same_sql_user(tmp_path):
    settings = Settings(database_path=tmp_path / 'auth.db', jwt_secret='synthetic-'+'x'*40, maintenance_enabled=False)
    app = create_app(settings)
    with TestClient(app) as client:
        auth = EvaluatorAuth(client, 'synthetic-evaluator', 'Synthetic-Password-123!')
        auth.login(register=True)
        identity = auth.user_id
        auth.headers = {'Authorization': 'Bearer invalid-synthetic-token'}
        assert auth.post('/sessions', json={'title': 'synthetic'}).status_code == 201
        assert auth.user_id == identity
        with app.state.store.sessions() as db:
            assert db.scalar(select(func.count()).select_from(User)) == 1


def test_dry_run_reads_dev_only_and_never_loads_credentials(monkeypatch):
    monkeypatch.setattr(pipeline, 'load_settings', lambda: (_ for _ in ()).throw(AssertionError('No credentials.')))
    report = pipeline.run_evaluation(limit=2, dry_run=True)
    assert report['status'] == 'preflight_only' and report['real_provider_calls'] == 0
    assert report['protocol']['candidate_model'] == report['protocol']['judge_model'] == 'deepseek-chat'
    assert report['case_count'] == 2 and report['protocol']['dataset_role'] == 'development'
