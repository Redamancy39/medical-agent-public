"""Small provider views; canonical state retains complete provenance for validation."""
import json
import re


def requested_answer_limit(question):
    limits = [int(n) for n in re.findall(r'(?:不超过|最多|至多)\s*(\d{1,4})\s*(?:个)?(?:中文)?字', question)]
    return min(limits) if limits and min(limits) > 0 else None


def document_context(document):
    fields = ('id', 'document_id', 'title', 'content', 'url', 'content_kind', 'jurisdiction', 'section',
              'tier', 'book', 'edition', 'year', 'publisher', 'publication_date', 'chapter')
    result = {k: document[k] for k in fields if k in document}
    if document.get('source_spans'):
        spans = document['source_spans']
        result['source_spans'] = [{k: s[k] for k in ('start', 'end', 'quote')} for s in spans
            if not any(other['start'] <= s['start'] and other['end'] >= s['end']
                and (other['start'], other['end']) != (s['start'], s['end']) for other in spans)]
    return result


def dependency_context(results):
    sources = {s['id']: s for r in results for s in r.get('sources', [])}
    return {'tasks': [{'task_id': r['task_id'], 'agent_id': r['agent_id'], 'answer': r['answer'],
        'source_ids': [s['id'] for s in r.get('sources', [])]} for r in results],
        'sources': [document_context(s) for s in sources.values()]}


def tool_context(message):
    """Preserve the tool protocol and result status; omit repeated audit-only fields."""
    if message['role'] != 'tool': return message
    try:
        result = json.loads(message['content'])
    except (ValueError, TypeError):
        return message
    if not isinstance(result, dict) or not isinstance(result.get('documents'), list): return message
    return {**message, 'content': json.dumps({**result,
        'documents': [document_context(d) for d in result['documents']]}, ensure_ascii=False)}


def answer_scope(question, task_count=1):
    """Soft generation guidance; never truncate approved facts to meet an inferred limit."""
    explicit = requested_answer_limit(question)
    detailed = bool(re.search(r'详细|全面|系统地|逐步推导|多阶段', question)) or task_count > 1
    maximum = explicit or (850 if detailed else 350)
    return {'answer_max_chars': maximum, 'answer_target_chars': min(max(1, int(maximum*.8)), 600 if detailed else 220),
        'scope_mode': 'expanded' if detailed else 'focused'}


def review_context(packet):
    drafts, keys, claims = [], {}, []
    for claim in packet['claims']:
        ids = []
        for draft in claim.get('original_draft_spans', [claim]):
            key = (draft['index'], draft['start'], draft['end'], draft['text'])
            if key not in keys:
                keys[key] = len(drafts)
                drafts.append({'text': draft['text']})
            ids.append(keys[key])
        claims.append({'index': claim['index'], 'text': claim['text'], 'draft_ids': ids,
            **{k: claim[k] for k in ('preserved_facts', 'repair_targets') if k in claim}})
    return {'question': packet['question'], 'claims': claims, 'draft_spans': drafts,
        'evidence': [{k: e[k] for k in ('id', 'document_id', 'quote')} for e in packet['evidence']],
        'policy_rules': packet['policy_rules'], 'corpus_scope': packet['corpus_scope'],
        'require_scope_review': packet.get('require_scope_review', False),
        'answer_max_chars': requested_answer_limit(packet['question'])}
