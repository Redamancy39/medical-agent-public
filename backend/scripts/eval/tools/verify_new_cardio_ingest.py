# -*- coding: utf-8 -*-
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from app.knowledge import BGEEmbedding, KnowledgeStore, LocalReranker

def main():
    emb = BGEEmbedding(ROOT / "data/models")
    rerank = LocalReranker("D:/rag_project/models/reranker/bge-reranker-v2-m3")

    store = KnowledgeStore(ROOT / "data/knowledge_medical_v1.db", emb, rerank)

    queries = [
        ("家庭血压切点", "家庭自测血压 诊断标准 135/85 上臂式电子血压计 早晚测量"),
        ("动态血压夜间", "动态血压 ABPM 24小时 130/80 夜间 120/70 反杓型 脑卒中"),
        ("一级预防阿司匹林", "心血管一级预防 70岁以上老年人 阿司匹林 出血禁忌 极高危40-70岁"),
        ("三高共管降压首选", "高血压合并糖尿病 血脂异常 三高共管 ACEI ARB 130/80 LDL-C 1.4"),
        ("依从性单片复方SPC", "高血压服药依从性 单片复方制剂 SPC 漏服补服 双倍剂量禁忌 踝部水肿抵消"),
        ("容量超负荷利尿剂", "高血压容量负荷过重 难治性 严格限盐5g 袢利尿剂 螺内酯 低钾血症"),
        ("房颤冠心病抗栓时程", "房颤合并冠心病 PCI术后 三联抗栓转双联 NOAC 氯吡格雷 1个月 PPI护胃"),
        ("妊娠期抗栓安全", "妊娠期抗栓 华法林致畸 胚胎病 绝对禁用 低分子肝素 首选 子痫前期阿司匹林")
    ]

    print("=== Tier 1 新扩充心血管指南专病检索探测 ===")
    all_ok = True
    for name, q in queries:
        hits = store.search(q, 3)
        top = hits[0]
        score = top.get("rerank_score", 0.0)
        doc_id = top.get("document_id", "")
        sec = top.get("section", "")
        print(f"[{name}] Top-1: [{doc_id}] score={score:.4f} | 章节: {sec}")
        if score < 0.6:
            all_ok = False

    print("\n全部探测通过:", all_ok)
    store.close()

if __name__ == "__main__":
    main()
