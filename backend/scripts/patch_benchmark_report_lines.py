import sys
from pathlib import Path

p = Path("e:/medical agent/backend/scripts/eval/run_full_50_cases_llm_judge_benchmark.py")
content = p.read_text(encoding="utf-8")

old_text = """    md_lines = [
        "# 50 例全场景测试集 LLM-as-a-Judge 独立双盲评测综合报告",
        "",
        "## 一、 评测规范与环境说明",
        f"- **测试样本总量**：全量 50 例高难度综合评测题 (涵盖 7 大临床类别、40+ 细分专科方向，测试集严格冻结)；",
        f"- **评审模型**：DeepSeek-Chat (`temperature=0.0` 确定性推理)；",
        f"- **四维独立量规**：临床行动力 (25分) + 知识覆盖度 (35分) + 安全合规 (20分) + 循证忠实度 (20分)；",
        f"- **防偏见机制**：双盲匿名打乱、反长度套话偏见 (Anti-Verbosity Bias)、CoT 证据链逐项比对；",
        f"- **总评估样本数**：50 题 × 3 对比架构 = 150 组独立裁判对决，消耗 Token: {total_prompt_tokens + total_completion_tokens:,}。",
        "",
        "## 二、 总体大盘量化结果对比 (N = 50)",
        "",
        "| 对比模型架构 | 综合评分 (100分) | 临床行动力 (25分) | 知识覆盖度 (35分) | 安全合规 (20分) | 循证忠实度 (20分) | 综合 PASS 率 (≥85分) | 安全拦截率 (≥15分) | 平均响应耗时 |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        f"| **1. Zero-shot Direct** | {s_z.get('mean_total',0)} | {s_z.get('mean_action',0)} | {s_z.get('mean_coverage',0)} | {s_z.get('mean_safety',0)} | {s_z.get('mean_grounding',0)} | {s_z.get('pass_rate',0)}% | {s_z.get('safety_pass_rate',0)}% | {s_z.get('mean_latency',0)}s |",
        f"| **2. Naive RAG (Fixed)** | {s_n.get('mean_total',0)} | {s_n.get('mean_action',0)} | {s_n.get('mean_coverage',0)} | {s_n.get('mean_safety',0)} | {s_n.get('mean_grounding',0)} | {s_n.get('pass_rate',0)}% | {s_n.get('safety_pass_rate',0)}% | {s_n.get('mean_latency',0)}s |",
        f"| **3. Ours (多智能体系统)** | **{s_o.get('mean_total',0)}** | **{s_o.get('mean_action',0)}** | **{s_o.get('mean_coverage',0)}** | **{s_o.get('mean_safety',0)}** | **{s_o.get('mean_grounding',0)}** | **{s_o.get('pass_rate',0)}%** | **{s_o.get('safety_pass_rate',0)}%** | **{s_o.get('mean_latency',0)}s** |",
        "",
        "## 三、 7 大细分临床类别表现对比",
        "",
        "| 临床测试类别 | 题目数 | Zero-shot 均分 (通过率) | Naive RAG 均分 (通过率) | Ours 多智能体系统 均分 (通过率) | 优势架构 |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |"
    ]"""

new_text = """    n_cases = len(cases)
    md_lines = [
        f"# {n_cases} 例全场景测试集 LLM-as-a-Judge 独立双盲评测综合报告",
        "",
        "## 一、 评测规范与环境说明",
        f"- **测试样本总量**：全量 {n_cases} 例高难度综合评测题 (涵盖 8 大核心类别、50+ 细分专科方向，测试集严格冻结)；",
        f"- **评审模型**：DeepSeek-Chat (`temperature=0.0` 确定性推理)；",
        f"- **四维独立量规**：临床行动力 (25分) + 知识覆盖度 (35分) + 安全合规 (20分) + 循证忠实度 (20分)；",
        f"- **防偏见机制**：双盲匿名打乱、反长度套话偏见 (Anti-Verbosity Bias)、CoT 证据链逐项比对；",
        f"- **总评估样本数**：{n_cases} 题 × 3 对比架构 = {len(eval_tasks)} 组独立裁判对决，消耗 Token: {total_prompt_tokens + total_completion_tokens:,}。",
        "",
        f"## 二、 总体大盘量化结果对比 (N = {n_cases})",
        "",
        "| 对比模型架构 | 综合评分 (100分) | 临床行动力 (25分) | 知识覆盖度 (35分) | 安全合规 (20分) | 循证忠实度 (20分) | 综合 PASS 率 (≥85分) | 安全拦截率 (≥15分) | 平均响应耗时 |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        f"| **1. Zero-shot Direct** | {s_z.get('mean_total',0)} | {s_z.get('mean_action',0)} | {s_z.get('mean_coverage',0)} | {s_z.get('mean_safety',0)} | {s_z.get('mean_grounding',0)} | {s_z.get('pass_rate',0)}% | {s_z.get('safety_pass_rate',0)}% | {s_z.get('mean_latency',0)}s |",
        f"| **2. Naive RAG (Fixed)** | {s_n.get('mean_total',0)} | {s_n.get('mean_action',0)} | {s_n.get('mean_coverage',0)} | {s_n.get('mean_safety',0)} | {s_n.get('mean_grounding',0)} | {s_n.get('pass_rate',0)}% | {s_n.get('safety_pass_rate',0)}% | {s_n.get('mean_latency',0)}s |",
        f"| **3. Ours (多智能体系统)** | **{s_o.get('mean_total',0)}** | **{s_o.get('mean_action',0)}** | **{s_o.get('mean_coverage',0)}** | **{s_o.get('mean_safety',0)}** | **{s_o.get('mean_grounding',0)}** | **{s_o.get('pass_rate',0)}%** | **{s_o.get('safety_pass_rate',0)}%** | **{s_o.get('mean_latency',0)}s** |",
        "",
        "## 三、 细分临床专科表现对比",
        "",
        "| 临床测试类别 | 题目数 | Zero-shot 均分 (通过率) | Naive RAG 均分 (通过率) | Ours 多智能体系统 均分 (通过率) | 优势架构 |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |"
    ]"""

assert old_text in content, "old_text not found"
p.write_text(content.replace(old_text, new_text), encoding="utf-8")
print("Successfully patched report generation in benchmark script!")
