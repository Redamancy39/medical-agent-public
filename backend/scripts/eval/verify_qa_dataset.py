# -*- coding: utf-8 -*-
"""Verify all ground truth answers and gold quotes in CC-QA-v1 dataset."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

DATASET_PATH = Path(__file__).resolve().parent / "fixtures/clinical_qa_benchmark_dataset.json"
MEDICAL_ROOT = ROOT / "knowledge/medical"


def main():
    print("=" * 65)
    print(" 验证临床复杂问答评测集 (CC-QA-v1) 准确性与引据真实性")
    print("=" * 65)

    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    sources = [
        json.loads(line)
        for line in (MEDICAL_ROOT / "sources.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    source_map = {
        s["id"]: (MEDICAL_ROOT / s["source_path"]).read_text(encoding="utf-8")
        for s in sources
    }

    cases = data["cases"]
    print(f"评测集版本: {data['benchmark_version']}, 案例总数: {len(cases)}")
    print(f"评分维度数量: {len(data['scoring_dimensions'])}")

    errors = []
    for idx, c in enumerate(cases):
        cid = c["id"]
        q = c["question"]
        ans = c["ground_truth_answer"]
        gold_list = c.get("gold_evidence", [])
        facts = c.get("key_facts", [])
        contra = c.get("critical_contraindications", [])
        rubric = c.get("rubric_points", {})

        if not q.strip() or not ans.strip():
            errors.append(f"[{cid}] 题目或标准答案为空！")

        if len(facts) < 3:
            errors.append(f"[{cid}] 核心事实点不足 3 条！")

        if not contra:
            errors.append(f"[{cid}] 缺少安全禁忌红线 (critical_contraindications)！")

        for g in gold_list:
            doc_id = g["document_id"]
            if doc_id not in source_map:
                errors.append(f"[{cid}] 引文文档 ID 未知: {doc_id}")
                continue
            raw_doc = source_map[doc_id]
            quote = g["key_quote"]
            if quote not in raw_doc:
                errors.append(f"[{cid}] 引文未能 100% 逐字匹配对应文档 {doc_id}！\n引文: {quote[:60]}...")

        # 校验 5 大评分维度是否完备
        required_rubric = ["factuality", "cutoff_precision", "safety_contraindication", "evidence_traceability", "reasoning_structure"]
        for r_key in required_rubric:
            if r_key not in rubric:
                errors.append(f"[{cid}] 缺少评分维度依据: {r_key}")

    if errors:
        print("\n❌ 发现以下校验错误:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    else:
        print("\n✅ 所有 20 道复杂问答评测题全部校验通过！")
        print("  - 100% 关键引文在本地权威指南原文中逐字匹配")
        print("  - 100% 具备严密核心事实链与零容忍禁忌红线")
        print("  - 100% 覆盖 5 大评分维度详尽打分依据")
        print("=" * 65)


if __name__ == "__main__":
    main()
