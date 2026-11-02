"""Validate frozen source bindings and measure retrieval, not clinical accuracy."""
import hashlib
import json
from collections import Counter
from pathlib import Path

from .medical_corpus import load_documents, corpus_hash

DATASET_ROOT = Path(__file__).resolve().parents[1] / 'evaluation/medical-v1'


def validate_dataset(root=DATASET_ROOT, documents=None):
    root = Path(root)
    documents = load_documents() if documents is None else documents
    documents = [d for d in documents if d['id'].startswith('nlm-')]
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    if manifest['corpus_sha256'] != corpus_hash(documents):
        raise ValueError('DATASET_CORPUS_CHANGED')
    if manifest['policy_sha256'] != hashlib.sha256((root / 'policy.json').read_bytes()).hexdigest():
        raise ValueError('DATASET_POLICY_CHANGED')
    rules = json.loads((root / 'policy.json').read_text(encoding='utf-8'))['rules']
    lookup = {d['id']: d for d in documents}
    cases, families, ids, questions = [], {}, set(), set()
    for split in ('dev', 'test'):
        path = root / (split + '.jsonl')
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest['files_sha256'][path.name]:
            raise ValueError('DATASET_FILE_CHANGED')
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
        if len(rows) != {'dev': 20, 'test': 40}[split]:
            raise ValueError('DATASET_SPLIT_COUNT')
        for case in rows:
            if case['id'] in ids or case['question'].strip() in questions:
                raise ValueError('DATASET_DUPLICATE')
            ids.add(case['id']); questions.add(case['question'].strip())
            if case['split'] != split or case['force_topology'] is not False:
                raise ValueError('DATASET_ROUTING_OVERRIDE')
            if families.setdefault(case['family_id'], split) != split:
                raise ValueError('DATASET_FAMILY_LEAKAGE')
            if not case['expected_actions'] or not set(case['expected_actions']) <= {'answer', 'clarify', 'unknown', 'boundary', 'urgent'}:
                raise ValueError('DATASET_ACTION_INVALID')
            if not set(case['policy_rules']) <= set(rules):
                raise ValueError('DATASET_POLICY_INVALID')
            if not case['gold_evidence'] and not case['policy_rules']:
                raise ValueError('DATASET_NO_REFERENCE')
            if case['clinical_review'] != 'not_reviewed':
                raise ValueError('DATASET_REVIEW_STATUS')
            for gold in case['gold_evidence']:
                doc = lookup.get(gold['document_id'])
                if doc is None or (gold['document_version'], gold['source_sha256'], gold['url']) != (doc['version'], doc['source_sha256'], doc['url']):
                    raise ValueError('DATASET_GOLD_VERSION')
                section = next((s for s in doc['sections'] if s['start'] == gold['editorial_start'] and s['end'] == gold['editorial_end']), None)
                if section is None or section['section'] != gold['section'] or not gold['source_spans'] or any(s not in section['source_spans'] for s in gold['source_spans']):
                    raise ValueError('DATASET_GOLD_SPAN')
            cases.append(case)
    expected = {'basic': 20, 'scenario': 10, 'comparison': 10, 'unknown': 10, 'safety': 10}
    if len(cases) != 60 or dict(Counter(c['category'] for c in cases)) != expected:
        raise ValueError('DATASET_CATEGORY_COUNT')
    if manifest['total'] != 60 or manifest['split_counts'] != {'dev': 20, 'test': 40} or manifest['category_counts'] != expected or manifest['topic_counts'] != dict(Counter(c['topic'] for c in cases)):
        raise ValueError('DATASET_MANIFEST_COUNT')
    if manifest['router'] != 'real_lead_auto_no_topology_override' or manifest['test_frozen'] is not True:
        raise ValueError('DATASET_MANIFEST_ROUTING')
    return cases


def supports(hit, gold):
    return (hit['document_id'] == gold['document_id'] and hit['version'] == gold['document_version']
            and hit.get('source_sha256') == gold['source_sha256']
            and hit['start'] <= gold['editorial_start'] and hit['end'] >= gold['editorial_end']
            and all(span in hit.get('source_spans', []) for span in gold['source_spans']))


def retrieval_score(case, hits):
    gold = case['gold_evidence']
    if not gold:
        return {'eligible': False, 'hit_at_5': None, 'reciprocal_rank': None, 'support_coverage': None}
    covered = [any(supports(h, g) for h in hits[:5]) for g in gold]
    rank = next((i for i, h in enumerate(hits[:5], 1) if any(supports(h, g) for g in gold)), None)
    return {'eligible': True, 'hit_at_5': int(any(covered)), 'reciprocal_rank': 1 / rank if rank else 0,
            'support_coverage': sum(covered) / len(gold)}
