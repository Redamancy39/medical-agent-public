# -*- coding: utf-8 -*-
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))
sys.stdout.reconfigure(encoding="utf-8")

from app.knowledge import BGEEmbedding, KnowledgeStore, LocalReranker

def main():
    emb = BGEEmbedding(ROOT / "backend/data/models")
    rerank = LocalReranker("D:/rag_project/models/reranker/bge-reranker-v2-m3")
    store = KnowledgeStore(ROOT / "backend/data/knowledge_medical_v1.db", emb, rerank)

    queries = [
        ("血脂总纲-超高危靶标", "超高危 ASCVD LDL-C 目标值 1.0 极高危 1.4 PCSK9抑制剂 他汀"),
        ("基层2025-转诊指征", "基层高血压 2025 紧急转诊 180/120 撕裂样背痛 随访间隔"),
        ("精准医疗-基因多态性", "高血压 药物基因组学 CYP2D6 美托洛尔 慢代谢 心动过缓 BDKRB1 干咳"),
        ("体检共识-白大衣排查", "健康体检 首次测血压偏高 140/90 严禁直接单次诊断 休息15分钟 ABPM"),
        ("食养-高血压减盐", "高血压食养指南 每日食盐 5g 补钾 绿叶蔬菜 DASH饮食 燕麦"),
        ("食养-血脂饱和脂肪", "高脂血症食养 饱和脂肪酸 7% 胆固醇 200mg 植物固醇 燕麦葡聚糖"),
        ("食养-糖尿病进餐顺序", "糖尿病食养 低GI 进餐顺序 先喝汤蔬菜肉蛋后主食 餐后血糖"),
        ("食养-肥胖能量缺口", "肥胖食养指南 能量缺口 500-750kcal 蛋白质供能比 严禁极度节食")
    ]

    print("=== Tier 1 第一组与第二组新指南专病探测 ===")
    all_ok = True
    for name, q in queries:
        hits = store.search(q, 2)
        top = hits[0]
        score = top.get("rerank_score", 0.0)
        doc_id = top.get("document_id", "")
        sec = top.get("section", "")
        print(f"[{name}] Top-1: [{doc_id}] score={score:.4f} | 章节: {sec}")
        if score < 0.6:
            all_ok = False

    print("\n全部专病探测通过:", all_ok)
    store.close()

if __name__ == "__main__":
    main()
