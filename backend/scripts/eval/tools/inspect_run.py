# -*- coding: utf-8 -*-
import json

with open('run_details_utf8.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

trace = d.get('review_trace', [])
if trace:
    print("=== DRAFT SPANS IN ROUND 1 ===")
    for span in trace[0].get('draft_spans', []):
        print(f"[{span.get('index')}] {span.get('text')}")
