# -*- coding: utf-8 -*-
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.multitier_retrieval import MultiTierKnowledgeService

def main():
    service = MultiTierKnowledgeService()
    print("Tier Stats:", service.get_tier_stats())
    
    test_queries = [
        "急腹症 膈下游离气体 剖腹探查指征 板状腹",
        "不明原因发热 FUO 诊断标准 体温调定点 PGE2",
        "SGLT2抑制剂 管球反馈 入球小动脉收缩 肾小球囊内压",
        "破伤风 痉挛毒素 甘氨酸 GABA 抑制性递质 苦笑面容"
    ]
    
    for q in test_queries:
        print(f"\n--- 查询: {q} ---")
        hits = service.search_textbooks(q, limit=2)
        for i, h in enumerate(hits, 1):
            score = h.get("rerank_score", 0.0)
            print(f"  [{i}] 《{h['book']}》（{h['edition']}）: {h['title']} (Rerank={score:.4f})")
            print(f"      篇章: {h.get('part', '')} > {h.get('chapter', '')}")
            print(f"      摘录: {h['content'][:120]}...")
            
    service.close()

if __name__ == "__main__":
    main()
