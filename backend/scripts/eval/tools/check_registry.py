# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[4]
reg = json.loads((ROOT / "backend/knowledge/textbooks/books_registry.json").read_text(encoding="utf-8"))

print("=== Tier 2 经典教材登记册状态全览 ===")
for b in reg["textbooks"]:
    status = b.get("status")
    status_zh = {
        "ingested": "已入库 (Batch 1/2)",
        "planned_batch3": "待入库 (Batch 3 临床专科)",
        "planned_batch4": "待入库 (Batch 4 基础医学)"
    }.get(status, status)
    print(f"[{b['book_id']}] 《{b['title']}》（{b['edition']} {b['year']}）| 状态: {status_zh}")
    print(f"  主编: {b['chief_editors']} | 分类: {b['category']}")
    print(f"  重点规划篇章: {b['focus_chapters']}\n")
