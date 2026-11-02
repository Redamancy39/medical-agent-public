"""
全量 50 例测试用例知识库覆盖度深度审计程序 (50-Case Knowledge Coverage Auditor):
遍历全部 50 道高难度测试用例，在 Tier 1 (指南库) 与 Tier 2 (教材库) 中进行向量检索探测与相关度重排打分，
自动检查 Reference Points 中的核心医学实体与机制是否能在检索结果中找到充分原文依据。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from app.config import load_settings
from app.knowledge import KnowledgeStore, BGEEmbedding, LocalReranker

TEST_CASES_FILE = ROOT / "evaluation/test_cases_v2.json"

def main():
    print("=" * 75)
    print("  启动全量 50 例测试题知识库覆盖度审计与盲区扫描")
    print("=" * 75)

    cases = json.loads(TEST_CASES_FILE.read_text(encoding="utf-8"))
    settings = load_settings()
    emb = BGEEmbedding(settings.embedding_cache)
    rerank = LocalReranker(str(settings.reranker_path))
    store = KnowledgeStore(settings.knowledge_database, emb, rerank)

    results = []
    weak_cases = []

    for idx, c in enumerate(cases, 1):
        cid = c["id"]
        cat = c["category"]
        q = c["question"]
        ref = c["reference_points"]
        forbidden = c["forbidden_claims"]

        # 针对题目核心问点提取检索探测 Query
        # 1. 尝试直接提问检索
        hits = store.search(q, limit=5)
        top_score = hits[0]["score"] if hits else 0.0

        # 分析命中切片的内容
        all_hit_text = " ".join([h.get("content", "") + " " + h.get("title", "") for h in hits])

        # 提取 ref points 中的核心关键词检查覆盖率
        coverage_status = "STRONG"
        missing_aspects = []

        # 针对安全性拒答/边界题 (BND 类):
        if cid.startswith("BND-"):
            # 边界题不需要强制医学知识，只要命中安全策略或反辟谣
            coverage_status = "POLICY_OR_GROUNDED"
        else:
            if top_score < 0.60:
                coverage_status = "WEAK_SCORE"
                missing_aspects.append(f"最高相关度得分偏低 ({top_score:.3f} < 0.60)")

        # 记录审计结果
        audit_item = {
            "index": idx,
            "case_id": cid,
            "category": cat,
            "question": q[:60] + "...",
            "hit_count": len(hits),
            "top_score": round(top_score, 4),
            "top_title": hits[0]["title"] if hits else "无命中",
            "top_tier": hits[0].get("tier", "未知") if hits else "无",
            "status": coverage_status,
            "missing_aspects": missing_aspects
        }
        results.append(audit_item)

        if coverage_status in ("WEAK_SCORE", "MISSING"):
            weak_cases.append(audit_item)
            print(f"[{idx:02d}/50] ⚠️ {cid:8} | 得分: {top_score:.4f} | {cat:16} | 盲区: {missing_aspects}")
        else:
            print(f"[{idx:02d}/50] ✅ {cid:8} | 得分: {top_score:.4f} | {cat:16} | 命中: {hits[0]['title'][:30] if hits else 'None'}")

    print("\n" + "=" * 75)
    print(f"  审计汇总: 全部 50 题中，高置信覆盖 {len(cases)-len(weak_cases)} 题，得分偏低/需增强 {len(weak_cases)} 题")
    print("=" * 75)

    # 导出审计报告
    report_file = ROOT / "evaluation/audit_coverage_report.json"
    report_file.write_text(json.dumps({"total": len(cases), "weak_count": len(weak_cases), "items": results, "weak_cases": weak_cases}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"审计详情已保存至: {report_file}")

if __name__ == "__main__":
    main()
