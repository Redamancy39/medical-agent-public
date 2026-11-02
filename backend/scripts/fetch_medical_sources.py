"""Collect only NLM's reusable topic summaries and medical-test text. No model calls."""
import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from lxml import html

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1] / 'knowledge/medical'
POLICY = 'https://medlineplus.gov/about/using/usingcontent/'

def text_blocks(node):
    blocks = []
    for item in node.xpath('.//h2|.//h3|.//p|.//ul|.//ol|.//table'):
        # A parent list/table is one block, preserving row headers and conditions.
        if any(a.tag in ('ul', 'ol', 'table') for a in item.iterancestors() if a is not node):
            continue
        if item.tag == 'table':
            value = '\n'.join(' | '.join(' '.join(cell.text_content().split()) for cell in row.xpath('./th|./td'))
                              for row in item.xpath('.//tr'))
        elif item.tag in ('ul', 'ol'):
            # NLM also uses nested ul siblings directly under ul, not only
            # inside li. Preserve those qualifying risk factors too.
            value = '\n'.join('- ' + ' '.join(child.text_content().split()) for child in item
                              if child.tag in ('li', 'ul', 'ol'))
        else:
            value = ' '.join(item.text_content().split())
        if value: blocks.append(value)
    return '\n\n'.join(blocks)

def extract_body(raw, kind):
    tree = html.fromstring(raw)
    if kind == 'topic_summary':
        nodes = tree.xpath('//*[@id="topic-summary"]')
    elif kind == 'medical_test':
        nodes = tree.xpath('//article//div[@class="mp-content"]')
    else:
        raise ValueError('UNSUPPORTED_CONTENT_KIND')
    if not nodes:
        raise ValueError('PERMITTED_BODY_NOT_FOUND')
    body = '\n\n'.join(text_blocks(node) for node in nodes)
    if len(body) < 300:
        raise ValueError('PERMITTED_BODY_TOO_SHORT')
    title = ' '.join(tree.xpath('//h1')[0].text_content().split())
    return title, body

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fetch', action='store_true', help='At most 21 public HTTP requests; no redirects/retries')
    parser.add_argument('--only', nargs='+', help='Refresh only these catalog IDs, keeping other snapshots')
    args = parser.parse_args()
    if not args.fetch:
        print('not_run: pass --fetch to collect the fixed 20 NLM sources')
        return
    catalog = json.loads((ROOT / 'catalog.json').read_text(encoding='utf-8'))
    assert len(catalog) == 20 and len({r['id'] for r in catalog}) == 20
    (ROOT / 'raw').mkdir(parents=True, exist_ok=True)
    existing = ROOT / 'sources.jsonl'
    records = {r['id']: r for r in [json.loads(line) for line in existing.read_text(encoding='utf-8').splitlines()]} if args.only and existing.exists() else {}
    if args.only and not set(args.only) <= {r['id'] for r in catalog}: raise ValueError('UNKNOWN_SOURCE_ID')
    selected = [r for r in catalog if not args.only or r['id'] in args.only]
    with httpx.Client(timeout=20, trust_env=False, follow_redirects=False) as client:
        policy = client.get(POLICY); policy.raise_for_status()
        policy_text = ' '.join(html.fromstring(policy.text).xpath('//*[@id="mplus-content"]')[0].text_content().split())
        assert all(s in policy_text for s in ['Summaries on health topic pages', 'Medical test information', 'public domain'])
        (ROOT / 'reuse-policy.txt').write_text(policy_text, encoding='utf-8')
        for item in selected:
            row = {**item, 'url': 'https://medlineplus.gov/' + item['path'], 'publisher': 'U.S. National Library of Medicine',
                'source_family_id': item['id'], 'source_language': 'en-US', 'source_jurisdiction': 'US',
                'scope': 'general_public_information; project targets adult hypertension/type2 diabetes',
                'license': 'US-federal-public-domain-specified-NLM-content', 'license_url': POLICY,
                'attribution': 'Source: MedlinePlus, National Library of Medicine.',
                'clinical_review_status': 'not_reviewed', 'publication_date': None,
                'fetched_at': datetime.now(timezone.utc).isoformat()}
            try:
                response = client.get(row['url']); response.raise_for_status()
                if len(response.content) > 2_000_000: raise ValueError('BODY_LIMIT')
                title, body = extract_body(response.text, item['kind'])
                sha = hashlib.sha256(body.encode()).hexdigest()
                relative = 'raw/' + item['id'] + '-' + sha[:12] + '.txt'
                target = ROOT / relative
                if not target.exists(): target.write_text(body, encoding='utf-8')
                row.update(status='accepted', title=title, source_sha256=sha, source_path=relative,
                    extracted_chars=len(body), provenance_status='official_url_and_permitted_body_checked',
                    allowed_use={'local_ingest': True, 'llm_context': True, 'redistribution_with_attribution': True})
            except Exception as error:
                row.update(status='failed', safe_error_code=type(error).__name__)
            records[item['id']] = row
            print(item['id'] + ': ' + row['status'], flush=True)
            time.sleep(.25)
    ordered = [records[item['id']] for item in catalog if item['id'] in records]
    (ROOT / 'sources.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in ordered), encoding='utf-8')
    result = {'sources': len(ordered), 'accepted': sum(r['status'] == 'accepted' for r in ordered), 'http_requests_this_batch': 1 + len(selected)}
    history = ROOT / 'collection-history.jsonl'
    with history.open('a', encoding='utf-8') as log: log.write(json.dumps({'at': datetime.now(timezone.utc).isoformat(), **result}) + '\n')
    (ROOT / 'collection-report.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))
    if result['accepted'] != 20: raise SystemExit(2)

if __name__ == '__main__': main()
