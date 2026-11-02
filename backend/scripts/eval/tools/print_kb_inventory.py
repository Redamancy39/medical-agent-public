# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[3]

# 1. 统计 Tier 1
t1_sources_file = ROOT / "knowledge/medical/sources.jsonl"
t1_editorial_file = ROOT / "knowledge/medical/editorial-sections.json"

t1_sources = [json.loads(line) for line in t1_sources_file.read_text(encoding="utf-8").splitlines() if line.strip()]
t1_editorial = json.loads(t1_editorial_file.read_text(encoding="utf-8"))

print("=== Tier 1 核心临床指南库 ===")
print(f"总文档数: {len(t1_sources)} 篇")
t1_chunks_count = sum(len(secs) for secs in t1_editorial.values())
print(f"总切片数: {t1_chunks_count} 块")

en_docs = [s for s in t1_sources if s["id"].startswith("nlm-")]
cn_docs = [s for s in t1_sources if s["id"].startswith("cn-")]
print(f"  - 英文 NLM 基础科普参考: {len(en_docs)} 篇")
print(f"  - 中文国家级临床指南与共识: {len(cn_docs)} 篇")

print("\n--- 中文国家权威临床指南/共识清单 (33 篇) ---")
for i, s in enumerate(cn_docs, 1):
    sid = s["id"]
    sec_count = len(t1_editorial.get(sid, []))
    name = s.get("title_zh") or s.get("title")
    pub = s.get("publisher", "").split("/")[0].strip()
    print(f"  {i:2d}. [{sid}] 《{name}》 ({sec_count} 切片) | {pub}")

# 2. 统计 Tier 2
t2_sources_file = ROOT / "knowledge/textbooks/sources.jsonl"
t2_sources = [json.loads(line) for line in t2_sources_file.read_text(encoding="utf-8").splitlines() if line.strip()]
t2_registry_file = ROOT / "knowledge/textbooks/books_registry.json"
t2_registry = json.loads(t2_registry_file.read_text(encoding="utf-8"))

print("\n=== Tier 2 经典医学教科书大部头库 ===")
books_ingested = [b for b in t2_registry["textbooks"] if b.get("status") == "ingested"]
print(f"已入库大部头教材: {len(books_ingested)} 本 (人卫版 第10版 2024年)")
for b in books_ingested:
    print(f"  * 《{b['title']}》({b['edition']}) - 主编: {b['chief_editors']}")

print(f"已入库长篇机制与鉴别章节: {len(t2_sources)} 篇")
t2_chunks_count = sum(s.get("chunks_count", 0) for s in t2_sources)
print(f"总切片数: {t2_chunks_count} 块")

print("\n--- 教科书长章节清单 (19 篇) ---")
for i, s in enumerate(t2_sources, 1):
    print(f"  {i:2d}. [《{s['book']}》{s['edition']}] {s['title']} ({s['chunks_count']} 切片)")
