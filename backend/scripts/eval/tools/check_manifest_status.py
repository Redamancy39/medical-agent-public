# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[4]

manifest_file = ROOT / "docs/research/cardio-zh-20261027/download_manifest.json"
manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

ingested_codes = {"CV-007", "CV-025", "CV-002", "CV-003", "CV-026", "CV-009", "CV-010", "CV-049", "CV-090", "CV-063"}

already_in = [m for m in manifest if m["code"] in ingested_codes]
ready_to_ingest = [m for m in manifest if m["code"] not in ingested_codes and m["chars_count"] > 500]

print(f"=== 1. 已实际入库的文献 ({len(already_in)} 篇) ===")
for m in already_in:
    print(f"  [已入库] [{m['code']}] 《{m['title']}》({m['year']}) | {m.get('platform', '')}")

print(f"\n=== 2. 已完整下载提取、且质量极高的【现成待入库文献】 ({len(ready_to_ingest)} 篇) ===")
for i, m in enumerate(ready_to_ingest, 1):
    print(f"  {i:2d}. [{m['code']}] [{m['doc_type']}] ({m['year']}) 《{m['title']}》 (字数: {m['chars_count']:,}) | {m.get('platform', '')}")
