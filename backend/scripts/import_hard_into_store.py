# -*- coding: utf-8 -*-
import json
from pathlib import Path
import sys

ROOT = Path("e:/medical agent")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config import load_settings
from backend.app.knowledge import BGEEmbedding, KnowledgeStore

settings = load_settings()
ks = KnowledgeStore(settings.knowledge_database, BGEEmbedding(settings.embedding_cache))

# 1. 导入指南
with open(ROOT / "backend/knowledge/medical/sources.jsonl", "r", encoding="utf-8") as f:
    med = [json.loads(l) for l in f if l.strip()]

hard_med = [m for m in med if m.get("id", "").startswith("cn-guideline-")]
docs = []
for m in hard_med:
    text_val = m.get("content") or m.get("text") or ""
    if not text_val.strip():
        continue
    docs.append({
        "id": m["id"],
        "version": "2026.1",
        "title": m.get("title", m["id"]),
        "text": text_val,
        "url": f"local://medical/{m['id']}",
        "synthetic": False
    })

# 2. 导入教材
with open(ROOT / "backend/knowledge/textbooks/sources.jsonl", "r", encoding="utf-8") as f:
    tb = [json.loads(l) for l in f if l.strip()]

hard_tb = [t for t in tb if t.get("id", "").startswith("tb-")]
for t in hard_tb:
    text_val = t.get("content") or t.get("text") or ""
    if not text_val.strip():
        continue
    docs.append({
        "id": t["id"],
        "version": "2026.1",
        "title": t.get("title", t["id"]),
        "text": text_val,
        "url": f"local://textbooks/{t['id']}",
        "synthetic": False
    })

print(f"准备导入 {len(docs)} 篇高难专科指南与教材切片...")
res = ks.import_documents(docs, skip_unchanged=True)
print("导入结果:", res)

# 验证检索
test_queries = [
    "冠脉支架 消化道出血",
    "嗜铬细胞瘤 普萘洛尔 禁忌",
    "重症肌无力 氨基糖苷类",
    "DKA 胰岛素 补钾",
    "MAOI 5-羟色胺综合征 洗脱期"
]
print("\n=== 检索召回验证 ===")
for q in test_queries:
    hits = ks.search(q, limit=2)
    print(f"\nQuery: {q}")
    for h in hits:
        print(f"  -> [{h['score']:.4f}] {h.get('title')}")
