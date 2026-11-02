# -*- coding: utf-8 -*-
import csv
import sys
import urllib.request
import urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2].parent
DOCS_DIR = ROOT / "docs/research/cardio-zh-20261027"

with open(DOCS_DIR / "公开全文优先下载_104份.csv", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

candidates = []
for r in rows:
    code = r["编号"]
    doc_type = r["文献类型"]
    if code in ["CV-007", "CV-025"]:
        continue
    if doc_type in ["指南", "专家共识", "专家建议", "标准/服务规范"]:
        candidates.append(r)

print(f"Testing URL connectivity for {len(candidates)} candidate documents...")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

results = []
for r in candidates:
    code = r["编号"]
    title = r["文献名称"]
    url = r.get("已核实PDF") or r.get("推荐获取链接") or r.get("已核实HTML") or ""
    status = "unknown"
    size = 0
    err_msg = ""
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            content_type = resp.headers.get("Content-Type", "")
            chunk = resp.read(8192)
            size = len(chunk)
            status = f"OK ({resp.status}, {content_type.split(';')[0]})"
    except Exception as e:
        status = "FAILED"
        err_msg = str(e)[:60]
    
    print(f"[{code}] {title[:25]}... -> {status} {err_msg}")
    results.append({
        "code": code,
        "title": title,
        "url": url,
        "status": status,
        "err": err_msg
    })

ok_count = sum(1 for r in results if r["status"].startswith("OK"))
print(f"\nConnectivity test finished: {ok_count}/{len(candidates)} accessible.")
