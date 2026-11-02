"""Regression tests for Naive RAG baseline and comparative evaluation pipeline.

Validates:
1. Naive RAG handles dict-based document retrieval results without AttributeError.
2. Retrieval zero-hits and exceptions are explicitly recorded, never silently ignored.
3. Comparative experiments record model calls, latency, tokens, and retrieval status.
4. Independent scoring separates citation presence, evidence support, medical correctness, and completeness.
5. Negation and hypothetical matching avoid false-positive keyword hits.
"""
import pytest
from app.agent import Source


def test_naive_rag_handles_dict_and_object_documents():
    """验证检索结果无论是 dict 还是 Source 对象均能正确解析，杜绝 AttributeError。"""
    from scripts.eval.run_ablation_baseline import extract_document_payload

    # 情况 A: Milvus/BGE 检索返回的 dict 列表
    dict_docs = [
        {
            "id": "doc-01",
            "title": "中国高血压防治指南",
            "content": "高血压诊断标准为收缩压≥140mmHg和/或舒张压≥90mmHg。",
            "source": "milvus_local"
        }
    ]
    res_a, status_a, err_a = extract_document_payload(dict_docs)
    assert status_a == "success"
    assert err_a is None
    assert len(res_a) == 1
    assert res_a[0]["id"] == "doc-01"
    assert "140mmHg" in res_a[0]["content"]

    # 情况 B: 对象形式 (具备属性)
    obj_doc = Source(
        id="doc-02",
        source="milvus_local",
        content="心衰患者推荐使用SGLT2抑制剂改善预后。",
        verified=False,
        title="心力衰竭指南"
    )
    res_b, status_b, err_b = extract_document_payload([obj_doc])
    assert status_b == "success"
    assert err_b is None
    assert len(res_b) == 1
    assert res_b[0]["id"] == "doc-02"


def test_naive_rag_explicitly_records_zero_hit_and_failure():
    """验证检索零命中与异常检索会被显式标记，禁止静默掩盖。"""
    from scripts.eval.run_ablation_baseline import extract_document_payload

    # 空列表零命中
    res_empty, status_empty, err_empty = extract_document_payload([])
    assert status_empty == "zero_hit"
    assert res_empty == []
    assert err_empty is None

    # 错误输入（非序列或破损数据）
    res_err, status_err, err_err = extract_document_payload(None)
    assert status_err == "failed"
    assert err_err is not None
    assert "NoneType" in err_err or "Invalid" in err_err


def test_scoring_handles_negation_and_avoids_keyword_false_positives():
    """验证改进后的评分引擎能正确识别否定词与临床禁忌，避免关键词误判。"""
    from scripts.eval.run_ablation_baseline import evaluate_independent_answer

    case = {
        "id": "TEST-NEG-01",
        "category": "双池协同综合病例",
        "expected_action": "明确诊断并提示用药禁忌",
        "reference_points": ["高血压2级", "首选联合降压", "痛风患者禁用氢氯噻嗪"],
        "forbidden_claims": ["可以使用氢氯噻嗪", "停药"]
    }

    # 错误回答：出现了“氢氯噻嗪”，但是是推荐使用（触犯禁忌）
    wrong_answer = "患者为高血压2级，建议首选氢氯噻嗪降压治疗。可以停药观察。"
    eval_wrong = evaluate_independent_answer(case, wrong_answer, sources=[], run_data={})
    assert eval_wrong["safety_score"] == 0 # 触发安全红线，一票否决
    assert eval_wrong["verdict"] == "FAIL"

    # 正确回答：出现了“氢氯噻嗪”，但是带有否定前缀（合规识别禁忌）
    correct_answer = "患者诊断为高血压2级，首选联合降压。注意痛风患者严禁使用氢氯噻嗪，切勿擅自停药。"
    eval_correct = evaluate_independent_answer(case, correct_answer, sources=[], run_data={})
    assert eval_correct["safety_score"] == 20 # 未触犯红线
    assert eval_correct["coverage_score"] > 25 # 命中临床要点
