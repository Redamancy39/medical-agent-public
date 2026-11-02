# -*- coding: utf-8 -*-
import csv
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]

sources = []
with open(ROOT / "knowledge/medical/sources.jsonl", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            d = json.loads(line)
            if d["id"].startswith("cn-"):
                sources.append(d)

print("=== 现有系统库内的 25 篇中文指南精确标题 ===")
for s in sources:
    print(f"[{s['id']}] {s.get('title_zh') or s.get('title')}")

rows_104 = list(csv.DictReader(open(ROOT.parent / "docs/research/cardio-zh-20261027/公开全文优先下载_104份.csv", encoding="utf-8-sig")))

exact_same = []
for r in rows_104:
    r_name = r["文献名称"].strip()
    for s in sources:
        s_name = (s.get("title_zh") or s.get("title") or "").strip()
        # 精确或高度匹配
        if r_name == s_name or (r_name in s_name and len(r_name) > 8) or ("高血压防治指南(2024" in r_name and "高血压防治指南" in s_name) or ("心力衰竭诊断和治疗指南" in r_name and "心力衰竭" in s_name):
            exact_same.append((r, s))
            break

print(f"\n=== 104 份中与现有库中【直接同款/已具备】的文献 (共 {len(exact_same)} 份) ===")
for r, s in exact_same:
    print(f"[{r['编号']}] 《{r['文献名称']}》({r['年份']}) <---> [{s['id']}] {s.get('title_zh')}")

print(f"\n104 份中真正【完全未下载、物理未入库】的文献数量: {len(rows_104) - len(exact_same)} 份")
