"""Synthetic, offline acceptance of comparable and resumable evaluations."""
from copy import deepcopy
import json
from types import SimpleNamespace

import httpx
import pytest

from app.config import Settings
from scripts.eval import llm_judge, run_ablation_baseline as baseline


@pytest.fixture
def config(tmp_path, monkeypatch):
    value = Settings(database_path=tmp_path / 'eval.db', jwt_secret='synthetic-jwt-' + 'x' * 40,
        deepseek_model='deepseek-chat', deepseek_api_key='synthetic-key', model_max_tokens=4096)
    monkeypatch.setattr(baseline, 'load_settings', lambda: value)
    monkeypatch.setattr(llm_judge, 'load_settings', lambda: value)
    return value


def response(answer='合成回答', **extra):
    return {'model': 'returned-model-version', 'choices': [{'finish_reason': 'stop',
        'message': {'content': answer}}], **extra}


def test_direct_generation_uses_configured_model_and_records_response_model(config):
    def handler(request):
        payload = json.loads(request.content)
        assert payload['model'] == 'deepseek-chat' and payload['max_tokens'] == 4096
        assert payload['temperature'] == 0.2
        return httpx.Response(200, json=response(usage={'prompt_tokens': 0, 'completion_tokens': 2, 'total_tokens': 2}))

    result = baseline.call_llm_direct('synthetic prompt', settings=config, transport=httpx.MockTransport(handler))
    assert result['requested_model'] == 'deepseek-chat'
    assert result['response_model'] == 'returned-model-version'
    assert result['prompt_tokens'] == 0


def test_missing_token_usage_is_unknown_instead_of_zero(config):
    result = baseline.call_llm_direct('synthetic', settings=config,
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=response())))
    assert result['prompt_tokens'] is result['total_tokens'] is None


def test_document_normalization_keeps_source_provenance():
    source = {'id': 's0', 'source': 'synthetic', 'content': '合成切片', 'document_id': 'doc',
        'version': 'v1', 'source_sha256': 'a' * 64,
        'source_spans': [{'start': 0, 'end': 8, 'quote': 'Original'}]}
    before = deepcopy(source)
    docs, status, error = baseline.extract_document_payload([source])
    assert status == 'success' and error is None
    assert docs[0]['source_sha256'] == 'a' * 64 and docs[0]['source_spans'] == source['source_spans']
    docs[0]['source_spans'][0]['quote'] = 'changed'
    assert source == before


def test_invalid_document_is_a_retrieval_failure_instead_of_invented_id():
    docs, status, error = baseline.extract_document_payload([{'content': '无ID的合成资料'}])
    assert docs == [] and status == 'failed' and error


def test_naive_uses_full_evidence_and_does_not_instruct_unbound_supplement(config, monkeypatch):
    source = {'id': 's0', 'content': '摘述' * 300 + '末尾条件必须保留', 'source': 'synthetic',
        'source_sha256': 'a' * 64, 'source_spans': [{'start': 0, 'end': 8, 'quote': 'Original'}]}
    captured = []

    def generate(prompt, **kwargs):
        captured.append(prompt)
        return {'answer': '合成回答', 'status': 'completed', 'error': None, 'latency': 0.1,
            'prompt_tokens': None, 'completion_tokens': None, 'total_tokens': None}

    def search(question, limit):
        assert limit == 5
        return [source]

    client = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=config,
        flow=SimpleNamespace(tools=SimpleNamespace(knowledge=SimpleNamespace(search=search))))))
    monkeypatch.setattr(baseline, 'call_llm_direct', generate)
    result = baseline.call_naive_rag(client, {}, '合成问题')
    assert captured and '末尾条件必须保留' in captured[0] and 'Original' in captured[0]
    assert '根据医学常识补充' not in captured[0]
    assert result['sources'][0]['source_sha256'] == 'a' * 64


def test_session_error_never_registers_an_unrelated_user(config):
    paths = []

    def post(path, **kwargs):
        paths.append(path)
        return httpx.Response(503, json={})

    client = SimpleNamespace(post=post)
    headers = {'Authorization': 'synthetic-token'}
    before = dict(headers)
    result = baseline.call_ours(client, headers, '合成问题')
    assert paths == ['/sessions'] and headers == before
    assert result['run_data']['result_status'] == 'failed'
    assert result.get('model_calls') is None


def test_judge_construction_and_parsing_do_not_load_private_settings(monkeypatch):
    monkeypatch.setattr(llm_judge, 'load_settings', lambda: pytest.fail('Must remain offline until evaluation.'))
    judge = llm_judge.MedicalLLMJudge()
    assert judge.model_name == 'deepseek-chat'


def scores(**extra):
    return {'action_score': 25, 'coverage_score': 35, 'safety_score': 20, 'grounding_score': 20,
        'action_checks': {'response_alignment': 'direct', 'instruction_following': 'met',
            'urgency_handling': 'appropriate', 'note': 'Synthetic explicit decisions.'},
        'reason': 'Synthetic judgment.', **extra}


@pytest.mark.parametrize('extra', [
    {'action_score': float('nan')}, {'coverage_score': float('inf')},
    {'safety_score': True}, {'grounding_score': -1},
])
def test_invalid_judge_scores_are_not_silently_clipped(config, extra):
    with pytest.raises(ValueError):
        llm_judge.MedicalLLMJudge().parse_judge_response(json.dumps(scores(**extra)))


def test_missing_judge_dimension_is_not_a_real_zero(config):
    raw = scores()
    del raw['coverage_score']
    with pytest.raises(ValueError):
        llm_judge.MedicalLLMJudge().parse_judge_response(json.dumps(raw))


def test_judge_no_evidence_cap_is_enforced_and_adjustment_recorded(config):
    raw = json.dumps(scores())
    judge = llm_judge.MedicalLLMJudge(api_key='synthetic', base_url='https://api.deepseek.com',
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=response(raw))))
    result = judge.evaluate_single({'question': '合成问题', 'reference_points': []}, '合成回答', [])
    assert result['judge_status'] == 'success' and result['grounding_score'] == 8
    assert result['total_score'] == 88 and result['score_rule_adjustments']
    assert result['response_model'] == 'returned-model-version'


def test_judge_api_error_is_unknown_score_not_medical_failure(config):
    judge = llm_judge.MedicalLLMJudge(api_key='synthetic', base_url='https://api.deepseek.com',
        transport=httpx.MockTransport(lambda r: httpx.Response(503, json={'error': 'private-upstream'})))
    result = judge.evaluate_single({'question': '合成问题'}, '合成回答', [])
    assert result['judge_status'] == 'failed'
    assert result['total_score'] is None and result['verdict'] is None
    assert 'private-upstream' not in json.dumps(result)


def test_judge_preserves_complete_quote_instead_of_400_char_slice(config):
    judge = llm_judge.MedicalLLMJudge()
    messages = judge.build_judge_prompt({'question': '合成问题'}, '合成回答', [
        {'content': '摘述' * 300 + '末尾条件', 'source_spans': [{'quote': '完整原文锚点'}]}])
    assert '末尾条件' in messages[1]['content'] and '完整原文锚点' in messages[1]['content']


def test_cost_estimate_requires_explicit_rates():
    estimate = llm_judge.MedicalLLMJudge.estimate_dataset_cost(1, 3)
    assert estimate['est_cost_rmb'] is None
