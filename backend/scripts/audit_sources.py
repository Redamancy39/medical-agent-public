# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path

# Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
sources_path = ROOT / "backend/knowledge/medical/sources.jsonl"
sources = [json.loads(l) for l in sources_path.read_text(encoding="utf-8").splitlines() if l.strip()]

print(f"Total sources: {len(sources)}")
print("-" * 110)
print(f"{'ID':35s} | {'Date':10s} | {'Title':30s} | {'URL'}")
print("-" * 110)

inconsistencies = []

for s in sources:
    sid = s["id"]
    date = str(s.get("publication_date") or "NONE")
    title = s.get("title_zh") or s.get("title", "")
    url = s.get("url", "")
    publisher = s.get("publisher", "")
    print(f"{sid:35s} | {date:10s} | {title[:28]:30s} | {url[:40]}")

    # Check inconsistencies
    # 1. Date is null
    if date == "NONE":
        inconsistencies.append((sid, "Missing publication_date"))

    # 2. Check if year in title matches publication_date year
    import re
    years_in_title = re.findall(r'20\d\d', title)
    if years_in_title and date != "NONE":
        title_year = years_in_title[0]
        date_year = date[:4]
        if title_year != date_year:
            inconsistencies.append((sid, f"Year mismatch: title has {title_year} but date is {date_year}"))

    # 3. Check fake/placeholder URLs
    if "xxgk/getSearchList.htm" in url or "example.com" in url or "stroke.shtml" in url:
        inconsistencies.append((sid, f"Placeholder/generic URL: {url}"))

print("\n" + "=" * 80)
print(f"Inconsistencies detected ({len(inconsistencies)} issues):")
print("=" * 80)
for sid, reason in inconsistencies:
    print(f"  [{sid}]: {reason}")
