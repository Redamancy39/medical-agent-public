# -*- coding: utf-8 -*-
import csv
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2].parent
DOCS_DIR = ROOT / "docs/research/cardio-zh-20261027"

with open(DOCS_DIR / "公开全文优先下载_104份.csv", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

# 排除完全同款的 CV-007 (高血压2024修订版) 和 CV-025 (心衰2024)
candidates = []
for r in rows:
    code = r["编号"]
    doc_type = r["文献类型"]
    if code in ["CV-007", "CV-025"]:
        continue
    # 指南、专家共识、专家建议、标准/服务规范
    if doc_type in ["指南", "专家共识", "专家建议", "标准/服务规范"]:
        candidates.append(r)

print(f"Total candidates in Tier 1 & Tier 2: {len(candidates)}")
for i, r in enumerate(candidates, 1):
    link = r.get("已核实PDF") or r.get("推荐获取链接") or r.get("已核实HTML") or ""
    print(f"{i}. [{r['编号']}] [{r['优先级']}] ({r['年份']}) 《{r['文献名称']}》 | 类型: {r['文献类型']} | 平台: {r.get('发布/刊载平台', '')}")
    print(f"   Link: {link[:100]}...")
