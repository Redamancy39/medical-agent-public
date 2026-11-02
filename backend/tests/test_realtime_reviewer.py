import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.medical_corpus import load_documents
from app.medical_reviewer import build_packet, validate_review, apply_review
from app.contracts import ContractViolation
from test_api import settings, login, session
from test_graph import ask, call
from test_multitask import task


def source():
    doc = load_documents()[0]; section = doc['sections'][0]
    return {'id': 'citation-1', 'source': 'milvus_local', 'verified': False, 'document_id': doc['id'],
        'version': doc['version'], 'source_sha256': doc['source_sha256'], 'start': section['start'],
        'end': section['end'], 'content': section['text'], 'source_spans': section['source_spans'], 'url': doc['url']}


def verdict(index=0, kind='medical_fact', status='supported', evidence_ids=None):
    return {'index': index, 'kind': kind, 'support_status': status, 'evidence_ids': evidence_ids or [],
            'policy_rules': [], 'note': '合成结构测试，非语义正确证明。'}


def test_missing_and_invented_claim_or_evidence_rejected():
    packet = build_packet('test', '一个句子。另一个句子。', [source()])
    with pytest.raises(ContractViolation, match='COVERAGE'):
        validate_review({'claims': [verdict()]}, packet)
    with pytest.raises(ContractViolation, match='EVIDENCE_ID'):
        validate_review({'claims': [verdict(evidence_ids=['invented']), verdict(1, status='unsupported')]}, packet)
    with pytest.raises(ContractViolation, match='MEDICAL_EVIDENCE_REQUIRED'):
        validate_review({'claims': [verdict(), verdict(1, status='unsupported')]}, packet)


def test_full_raw_quote_can_expand_citation_without_changing_corpus():
    packet = build_packet('test', '收缩压是心脏搏动时的压力。捏造结论。', [source()])
    evidence = next(e for e in packet['evidence'] if 'Your blood pressure is highest when your heart beats' in e['quote'])
    output = validate_review({'claims': [verdict(evidence_ids=[evidence['id']]), verdict(1, status='unsupported')]}, packet)
    applied = apply_review(output, packet, [source()])
    assert '捏造结论' not in applied['answer'] and applied['omitted_claim_count'] == 1
    assert applied['claim_reviews'][1]['final_start'] is None
    assert applied['sources'][0]['source_spans'][-1]['quote'] == evidence['quote']
    assert source()['source_spans'] != applied['sources'][0]['source_spans']


def test_scope_notice_survives_model_rejection():
    from app.medical_reviewer import POLICY_NOTICE
    packet = build_packet('test', '来源免责声明。', [])
    output = validate_review({'claims': [verdict(kind='corpus_scope', status='unsupported')]}, packet)
    applied = apply_review(output, packet, [])
    assert POLICY_NOTICE in applied['answer'] and applied['sources'] == []
    notice = applied['claim_reviews'][-1]
    assert notice['origin'] == 'program_policy'
    assert applied['answer'][notice['final_start']:notice['final_end']] == POLICY_NOTICE


def test_facts_cannot_be_hidden_in_scope_disclaimer():
    packet = build_packet('test', '这是NLM资料：原发性高血压最常见，通常无症状。', [source()])
    with pytest.raises(ContractViolation, match='FACT_CLASSIFICATION_INVALID'):
        validate_review({'claims': [verdict(kind='corpus_scope')]}, packet)


def application(settings, review, budget=10, multi=False):
    app = create_app(settings.model_copy(update={'knowledge_profile': 'medical', 'maintenance_enabled': False,
        'max_model_calls': budget, 'medical_reviewer_enabled': True}))
    app.state.model.review = review
    app.state.model.plan = lambda s: {'tasks': [task('one', require_sources=True)] + ([task('two')] if multi else [])}
    app.state.test_tools_execute = lambda *a: {'success': True, 'documents': [source()]}
    def decide(s):
        if not s['observations']: return {'tool_calls': [call(query='source')]}
        return {'answer': '收缩压是心脏搏动时的压力。未证实的治疗。', 'source_ids': ['citation-1']}
    app.state.model.decide = decide
    return app


def successful_review(s):
    p = s['review_packet']
    return {'claims': [verdict(0, evidence_ids=[p['evidence'][0]['id']]), verdict(1, status='unsupported')]}


def test_single_final_review_omits_unsupported_claim_and_is_persisted(settings):
    app = application(settings, successful_review)
    with TestClient(app) as client:
        app.state.flow.tools.execute = app.state.test_tools_execute
        headers = login(client)
        result = ask(client, headers, session(client, headers), '研究血压').json()
        assert result['result_status'] == 'partial' and result['reviewer_status'] == 'completed'
        assert result['model_calls'] == 4 and result['omitted_claim_count'] == 1
        assert '未证实的治疗' not in result['answer'] and result['clinical_review_status'] == 'not_run'
        reread = client.get('/runs/' + result['run_id'], headers=headers).json()
        assert reread['claim_reviews'] == result['claim_reviews']
        assert reread['reviewed_answer_sha256'] == result['reviewed_answer_sha256']


def test_review_cannot_bypass_original_global_budget(settings):
    app = application(settings, lambda s: pytest.fail('review must not run beyond budget'), budget=3)
    with TestClient(app) as client:
        app.state.flow.tools.execute = app.state.test_tools_execute
        headers = login(client)
        result = ask(client, headers, session(client, headers), '研究血压').json()
        assert result['model_calls'] == 3 and result['reviewer_status'] == 'failed'
        assert result['safe_error_code'] == 'MODEL_BUDGET_EXCEEDED'
        assert '未证实的治疗' not in result['answer']


def test_multi_synthesis_also_passes_final_reviewer(settings):
    app = application(settings, successful_review, multi=True)
    app.state.model.synthesize = lambda s: {'answer': '收缩压是心脏搏动时的压力。未证实的治疗。',
        'task_ids': ['one', 'two'], 'source_ids': ['citation-1']}
    with TestClient(app) as client:
        app.state.flow.tools.execute = app.state.test_tools_execute
        headers = login(client)
        result = ask(client, headers, session(client, headers), '多任务').json()
        assert result['reviewer_status'] == 'completed' and result['model_calls'] == 7
        assert '未证实的治疗' not in result['answer']


def test_repeated_invalid_reviewer_returns_safe_partial(settings):
    app = application(settings, lambda s: {'claims': []})
    with TestClient(app) as client:
        app.state.flow.tools.execute = app.state.test_tools_execute
        app.state.flow.settings = app.state.flow.settings.model_copy(update={'schema_repair_limit': 1})
        headers = login(client)
        result = ask(client, headers, session(client, headers), '研究血压').json()
        assert result['result_status'] == 'partial' and result['reviewer_status'] == 'failed'
        assert result['contract_repair_counts']['review'] == 1 and result['model_calls'] == 5
        assert '未证实的治疗' not in result['answer']
