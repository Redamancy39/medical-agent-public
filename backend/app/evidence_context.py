"""Bounded original context for retrieved medical chunks; never modifies the KB."""
from copy import deepcopy
import hashlib
import re

from .medical_quality import check_anchor, source_catalog


def expand_medical_evidence(documents, catalog=None, *, query=''):
    result = deepcopy(documents)
    if catalog is None:
        if not any(d.get('document_id') for d in result): return result
        try:
            catalog = source_catalog()
        except Exception:
            return result
    for doc in result:
        original = catalog.get(doc.get('document_id'))
        if original is None: continue
        if not doc.get('source_sha256') and original.get('source_sha256'):
            doc['source_sha256'] = original['source_sha256']
        if not doc.get('version') and original.get('editorial_version'):
            doc['version'] = original['editorial_version']

        if (doc.get('source_sha256') != original.get('source_sha256')
                or hashlib.sha256(original['raw'].encode()).hexdigest() != original.get('source_sha256')):
            raise ValueError('SOURCE_CONTEXT_VERSION_INVALID')

        start, end = doc.get('start'), doc.get('end')
        ed_text = original.get('editorial_text', '')
        if (type(start) is not int or type(end) is not int
                or not 0 <= (start or 0) < (end or 0) <= len(ed_text)
                or doc.get('content') != ed_text[(start or 0):(end or 0)]):
            found_idx = ed_text.find(doc.get('content', ''))
            if found_idx >= 0:
                doc['start'] = found_idx
                doc['end'] = found_idx + len(doc.get('content', ''))
                start, end = doc['start'], doc['end']
            else:
                continue

        spans = doc.setdefault('source_spans', [])
        for span in spans:
            check_anchor({**span, 'document_id': doc['document_id'],
                'source_sha256': doc['source_sha256']}, catalog)
        paragraphs = list(re.finditer(r'[^\n]+(?:\n(?!\n)[^\n]+)*', original['raw']))
        wanted = []
        for span in list(spans):
            for i, paragraph in enumerate(paragraphs):
                if not paragraph.start() <= span['start'] < paragraph.end(): continue
                wanted.append(paragraph)
                # The section introduction often states the measured quantity/time
                # while the retrieved anchor only names a later use or exception.
                heading = next((j for j in range(i, -1, -1)
                    if paragraphs[j].group().strip().endswith('?')), None)
                if heading is not None and heading+1 < len(paragraphs): wanted.append(paragraphs[heading+1])
                break
        # Select bounded context only within the already retrieved, hash-checked source.
        # Chinese guides must not lose a requested table merely because its anchor
        # fell in a different paragraph from the vector hit.
        terms = set(re.findall(r'[a-zA-Z]{3,}', query.lower()))
        for phrase in re.findall(r'[\u4e00-\u9fff]+', query):
            terms.update(phrase[i:i+n] for n in (2, 3) for i in range(len(phrase)-n+1))
        ranked = sorted(((sum(term in p.group().lower() for term in terms), i, p)
            for i, p in enumerate(paragraphs) if len(p.group()) <= 1800), key=lambda row: (-row[0], row[1]))
        if ranked and ranked[0][0]:
            wanted = [p for score, _, p in ranked[:3] if score >= ranked[0][0] * .5] + wanted
        used = 0
        for paragraph in wanted:
            span = {'start': paragraph.start(), 'end': paragraph.end(), 'quote': paragraph.group()}
            if span in spans or len(span['quote']) > 1800: continue
            if len(spans) >= 10 or used+len(span['quote']) > 2400: continue
            spans.append(span); used += len(span['quote'])
    return result
