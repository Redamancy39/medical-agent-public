"""Offline source review. Valid anchors do not imply medical correctness."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from .medical_corpus import MEDICAL_ROOT, load_documents, corpus_hash
from .medical_evaluation import DATASET_ROOT, validate_dataset


TEXTBOOK_ROOT = Path(__file__).resolve().parents[1] / 'knowledge/textbooks'


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def source_catalog(documents=None, include_textbooks=True):
    documents = load_documents() if documents is None else documents
    lookup = {d['id']: d for d in documents}
    catalog = {}
    for line in (MEDICAL_ROOT / 'sources.jsonl').read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        s = json.loads(line)
        source_id = s.get('id')
        if not source_id:
            continue
        source_path = s.get('source_path')
        raw_text = ''
        if source_path and (MEDICAL_ROOT / source_path).exists():
            raw_text = (MEDICAL_ROOT / source_path).read_text(encoding='utf-8')
        elif 'content' in s:
            raw_text = s['content']
        doc = lookup.get(source_id, {})
        catalog[source_id] = {
            **s,
            'raw': raw_text,
            'editorial_version': doc.get('version', s.get('version', s.get('source_sha256', '')[:12])),
            'editorial_text': doc.get('text', raw_text),
            'url': s.get('url') or f"local://medical/{source_id}"
        }
    if include_textbooks and (TEXTBOOK_ROOT / 'sources.jsonl').exists():
        for line in (TEXTBOOK_ROOT / 'sources.jsonl').read_text(encoding='utf-8').splitlines():
            if not line.strip(): continue
            tb = json.loads(line)
            source_path = tb.get('source_path')
            raw_text = ''
            if source_path and (TEXTBOOK_ROOT / source_path).exists():
                raw_text = (TEXTBOOK_ROOT / source_path).read_text(encoding='utf-8')
            elif 'content' in tb:
                raw_text = tb['content']
            tb_version = tb.get('source_sha256', '')[:12] + '-tb-10th'
            catalog[tb['id']] = {
                **tb,
                'raw': raw_text,
                'editorial_version': tb_version,
                'editorial_text': raw_text,
                'url': tb.get('url') or f"local://textbooks/internal_med_10th/{tb['id']}"
            }
    return catalog


def anchor(source_id, quote, catalog=None):
    catalog = source_catalog() if catalog is None else catalog
    raw = catalog[source_id]['raw']
    if raw.count(quote) != 1 or not quote.strip(): raise ValueError('QUOTE_NOT_UNIQUE')
    start = raw.index(quote)
    return {'document_id': source_id, 'source_sha256': catalog[source_id]['source_sha256'],
            'start': start, 'end': start + len(quote), 'quote': quote}


def check_anchor(item, catalog):
    source = catalog.get(item['document_id'])
    if source is None: raise ValueError('UNKNOWN_SOURCE')
    start, end = item['start'], item['end']
    if (type(start) is not int or type(end) is not int or not 0 <= start < end <= len(source['raw'])
            or source['raw'][start:end] != item['quote'] or not item['quote'].strip()
            or item['source_sha256'] != source['source_sha256']):
        raise ValueError('EVIDENCE_ANCHOR_INVALID')


def in_spans(evidence, sources):
    return any(s.get('document_id') == evidence['document_id']
               and s.get('source_sha256') == evidence['source_sha256']
               and any(p['start'] <= evidence['start'] and p['end'] >= evidence['end']
                       for p in s.get('source_spans', [])) for s in sources)


def validate_item(item, sources, catalog, rules):
    kind, status = item['kind'], item['support_status']
    if kind not in ('medical_fact', 'project_behavior', 'corpus_scope', 'editorial', 'unclassified'):
        raise ValueError('REVIEW_KIND_INVALID')
    if status not in ('pending', 'supported', 'partially_supported', 'unsupported', 'contradicted'):
        raise ValueError('REVIEW_STATUS_INVALID')
    if kind == 'unclassified' and status != 'pending': raise ValueError('REVIEW_KIND_REQUIRED')
    if item.get('professional_review') != 'pending': raise ValueError('PROFESSIONAL_REVIEW_NOT_PERFORMED')
    evidence = item.get('evidence', [])
    for e in evidence: check_anchor(e, catalog)
    if not set(item.get('policy_rules', [])) <= rules: raise ValueError('UNKNOWN_POLICY_RULE')
    if kind == 'medical_fact' and status in ('supported', 'partially_supported', 'contradicted') and not evidence:
        raise ValueError('MEDICAL_EVIDENCE_REQUIRED')
    if kind == 'project_behavior' and status == 'supported' and not item.get('policy_rules'):
        raise ValueError('POLICY_EVIDENCE_REQUIRED')
    if status != 'pending' and not item.get('note', '').strip(): raise ValueError('REVIEW_NOTE_REQUIRED')
    citation = ('not_applicable' if kind != 'medical_fact' else 'pending' if status == 'pending'
                else 'no_support_found' if not evidence else
                'bound' if all(in_spans(e, sources) for e in evidence) else 'citation_gap')
    return {**item, 'anchor_status': 'passed' if evidence else 'not_applicable', 'citation_status': citation}


def context():
    documents = load_documents()
    cases = {c['id']: c for c in validate_dataset(documents=documents) if c['split'] == 'dev'}
    manifest_sha = hashlib.sha256((DATASET_ROOT / 'manifest.json').read_bytes()).hexdigest()
    rules = set(json.loads((DATASET_ROOT / 'policy.json').read_text(encoding='utf-8'))['rules'])
    return cases, source_catalog(documents), rules, {'schema_version': 'medical-quality-review-v1',
        'dataset_manifest_sha256': manifest_sha, 'corpus_sha256': corpus_hash(documents),
        'reviewer': 'Codex_source_review_not_clinician', 'clinical_review': 'not_run'}


def check_version(bundle, expected):
    for key in ('schema_version', 'dataset_manifest_sha256', 'corpus_sha256'):
        if bundle.get(key) != expected[key]: raise ValueError('REVIEW_BASELINE_CHANGED')
    if bundle.get('clinical_review') != 'not_run': raise ValueError('PROFESSIONAL_REVIEW_NOT_PERFORMED')


def metrics(items):
    statuses = Counter(i['support_status'] for i in items)
    facts = [i for i in items if i['kind'] == 'medical_fact']
    reviewed = [i for i in facts if i['support_status'] != 'pending']
    return {'items': len(items), 'support_status_counts': dict(statuses),
        'citation_status_counts': dict(Counter(i['citation_status'] for i in items)),
        'medical_items': len(facts), 'reviewed_medical_items': len(reviewed),
        'supported_fraction_among_reviewed_medical_items':
            sum(i['support_status'] == 'supported' for i in reviewed) / len(reviewed) if reviewed else None,
        'clinical_accuracy': None, 'clinical_review': 'not_run'}


def review_reference_points(bundle):
    cases, catalog, rules, expected = context()
    check_version(bundle, expected)
    seen, rows = set(), []
    for item in bundle['items']:
        case = cases.get(item['case_id'])
        if case is None: raise ValueError('REVIEW_DEV_ONLY')
        index = item['point_index']
        if type(index) is not int or not 0 <= index < len(case['reference_points']): raise ValueError('POINT_INDEX_INVALID')
        key = (case['id'], index)
        if key in seen: raise ValueError('REVIEW_DUPLICATE')
        seen.add(key)
        if item['text'] != case['reference_points'][index]: raise ValueError('REFERENCE_POINT_CHANGED')
        rows.append(validate_item(item, case['gold_evidence'], catalog, rules))
    # Missing reviews remain pending; they never silently disappear from the denominator.
    for case in cases.values():
        for index, text in enumerate(case['reference_points']):
            if (case['id'], index) not in seen:
                rows.append(validate_item({'case_id': case['id'], 'point_index': index, 'text': text,
                    'kind': 'unclassified', 'support_status': 'pending', 'professional_review': 'pending'},
                    case['gold_evidence'], catalog, rules))
    return {'summary': {'dev_cases': len(cases), **metrics(rows)}, 'items': rows, **expected}


def claim_spans(answer):
    # Chinese punctuation only: preserve decimals, units, inequality signs and URLs.
    return [{'start': m.start(), 'end': m.end(), 'text': m.group()}
            for m in re.finditer(r'[^。！？；\n]+[。！？；]?', answer) if m.group().strip()]


def answer_template(report):
    cases, _, _, expected = context()
    rows = []
    for row in report['rows']:
        if row['case_id'] not in cases: raise ValueError('REVIEW_DEV_ONLY')
        result = row['result']
        rows.append({'case_id': row['case_id'], 'run_id': result['run_id'],
            'answer_sha256': digest(result['answer']), 'claims': [
                {**span, 'kind': 'unclassified', 'support_status': 'pending', 'evidence': [],
                 'policy_rules': [], 'note': '', 'professional_review': 'pending'}
                for span in claim_spans(result['answer'])]})
    return {**expected, 'rows': rows}


def review_answers(report, bundle):
    cases, catalog, rules, expected = context()
    check_version(bundle, expected)
    reviews = {r['case_id']: r for r in bundle['rows']}
    if len(reviews) != len(bundle['rows']): raise ValueError('REVIEW_DUPLICATE')
    actual_ids = [r['case_id'] for r in report['rows']]
    if len(set(actual_ids)) != len(actual_ids): raise ValueError('REPORT_DUPLICATE_CASE')
    if not set(reviews) <= set(actual_ids): raise ValueError('REVIEW_CASE_NOT_IN_REPORT')
    rows = []
    for row in report['rows']:
        if row['case_id'] not in cases: raise ValueError('REVIEW_DEV_ONLY')
        result, review = row['result'], reviews.get(row['case_id'])
        source_ids = set()
        for source in result['sources']:
            original = catalog.get(source.get('document_id'))
            if (original is None or source.get('version') != original['editorial_version']
                    or source.get('source_sha256') != original['source_sha256']):
                raise ValueError('CITED_SOURCE_VERSION_INVALID')
            if source['id'] in source_ids: raise ValueError('CITED_SOURCE_DUPLICATE')
            source_ids.add(source['id'])
            start, end = source.get('start'), source.get('end')
            if (type(start) is not int or type(end) is not int
                    or not 0 <= start < end <= len(original['editorial_text'])
                    or source.get('content') != original['editorial_text'][start:end]):
                raise ValueError('CITED_SOURCE_CONTENT_INVALID')
            for span in source.get('source_spans', []):
                check_anchor({**span, 'document_id': source['document_id'], 'source_sha256': source['source_sha256']}, catalog)
        answer = result['answer']
        if review is None:
            review = answer_template({'rows': [row]})['rows'][0]
        if review['run_id'] != result['run_id'] or review['answer_sha256'] != digest(answer):
            raise ValueError('ANSWER_CHANGED')
        covered, claims = set(), []
        for claim in review['claims']:
            start, end = claim['start'], claim['end']
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(answer):
                raise ValueError('CLAIM_SPAN_INVALID')
            if answer[start:end] != claim['text'] or not claim['text'].strip(): raise ValueError('CLAIM_SPAN_INVALID')
            positions = set(range(start, end))
            if covered & positions: raise ValueError('CLAIM_OVERLAP')
            covered |= positions
            claims.append(validate_item(claim, result['sources'], catalog, rules))
        if any(not char.isspace() and i not in covered for i, char in enumerate(answer)):
            raise ValueError('ANSWER_REVIEW_GAP')
        rows.append({'case_id': row['case_id'], 'run_id': result['run_id'], 'answer_sha256': digest(answer),
            'result_status': result['result_status'], 'claims': claims})
    all_claims = [c for r in rows for c in r['claims']]
    return {**expected, 'summary': {'observed_dev_cases': len(rows), 'total_dev_cases': len(cases),
        'unobserved_dev_cases': len(cases)-len(rows), **metrics(all_claims)}, 'rows': rows}


POLICY_ONLY_CLAUSE = re.compile(
    r'(?:抱歉[，,]?)?(?:我|本系统)?(?:无法|不能|拒绝)(?:提供|协助|帮助)'
    r'(?:未授权的?|未经授权的?)?'
    r'(?:(?:HIS|医院信息系统|系统)(?:爆破|暴力破解|攻击|入侵|绕过认证)(?:脚本|代码|方法)'
    r'|(?:他人|其他用户)的(?:病历|隐私|账号|记忆|个人信息)'
    r'|(?:伪造|虚构)的(?:论文|DOI|引用|医学证据))')


def is_policy_or_refusal(answer: str, question: str = '') -> bool:
    """Only complete, allowlisted non-medical refusal clauses are exempt.

    A disclaimer or a refusal word never exempts adjacent clinical content.
    Unrecognized wording follows normal evidence review rather than guessing intent.
    """
    clauses = [c.strip() for c in re.split(r'[。！？\n]', answer or '') if c.strip()]
    return bool(clauses) and all(POLICY_ONLY_CLAUSE.fullmatch(c) for c in clauses)
