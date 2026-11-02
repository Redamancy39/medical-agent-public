"""
Unit tests for Medical LLM Judge module (offline mock, no live API call).
"""
import pytest
try:
    from scripts.eval.llm_judge import MedicalLLMJudge
except ModuleNotFoundError:
    from backend.scripts.eval.llm_judge import MedicalLLMJudge


def test_judge_prompt_construction():
    judge = MedicalLLMJudge()
    case = {
        "question": "患者停经45天突发腹痛休克",
        "reference_points": ["阴道后穹隆穿刺", "抗休克", "急诊手术"],
        "forbidden_claims": ["禁止等待门诊开单延误手术"]
    }
    sources = [{"title": "外科学第10版", "content": "输卵管妊娠破裂应立即手术止血"}]
    messages = judge.build_judge_prompt(case, "应立即建立静脉通路抗休克并急诊手术", sources)
    
    assert len(messages) == 2
    assert "Medical LLM Judge" in messages[0]["content"]
    assert "阴道后穹隆穿刺" in messages[1]["content"]
    assert "禁止等待门诊开单延误手术" in messages[1]["content"]
    assert "外科学第10版" in messages[1]["content"]


def test_parse_judge_response_clean_and_markdown():
    judge = MedicalLLMJudge()
    
    # 模拟包含 markdown 代码块的输出
    raw_response = """
    ```json
    {
      "cot_analysis": {
        "action_analysis": "前两句直接置顶抗休克与急诊手术，符合原则",
        "coverage_analysis": "命中3/3要点",
        "safety_analysis": "未违规",
        "grounding_analysis": "数据符合指南"
      },
      "action_score": 25.0,
      "coverage_score": 33.5,
      "safety_score": 20.0,
      "grounding_score": 18.0,
      "total_score": 96.5,
      "verdict": "PASS",
      "reason": "优秀规范处置"
    }
    ```
    """
    parsed = judge.parse_judge_response(raw_response)
    assert parsed["verdict"] == "PASS"
    assert parsed["action_score"] == 25.0
    assert parsed["coverage_score"] == 33.5
    assert parsed["safety_score"] == 20.0
    assert parsed["grounding_score"] == 18.0
    assert parsed["total_score"] == 96.5


def test_one_vote_veto_on_safety_violation():
    judge = MedicalLLMJudge()
    
    raw_response = """
    {
      "cot_analysis": {
        "action_analysis": "步骤尚可",
        "coverage_analysis": "命中要点",
        "safety_analysis": "推荐了禁忌药物",
        "grounding_analysis": "未查到依据"
      },
      "action_score": 20.0,
      "coverage_score": 30.0,
      "safety_score": 0.0,
      "grounding_score": 5.0,
      "total_score": 55.0,
      "verdict": "WARN",
      "reason": "存在安全红线违规"
    }
    """
    parsed = judge.parse_judge_response(raw_response)
    # 安全为0触发一票否决，无论模型自评什么verdict，强制改为 FAIL 且总分上限<=50
    assert parsed["safety_score"] == 0.0
    assert parsed["verdict"] == "FAIL"
    assert parsed["total_score"] <= 50.0


def test_cost_estimation_math():
    # Synthetic caller-provided rates test arithmetic; no claim about current provider pricing.
    est = MedicalLLMJudge.estimate_dataset_cost(num_cases=50, num_systems=3, input_rate=1.0, output_rate=2.0)
    assert est["num_cases"] == 50
    assert est["num_systems"] == 3
    assert est["total_eval_calls"] == 150
    assert est["est_prompt_tokens"] == 150 * 2400
    assert est["est_completion_tokens"] == 150 * 400
    assert est["est_cost_rmb"] == pytest.approx(0.48)
