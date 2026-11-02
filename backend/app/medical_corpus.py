"""Source-bound editorial views. Evaluation answers never enter this corpus."""
import hashlib
import json
from pathlib import Path

MEDICAL_ROOT = Path(__file__).resolve().parents[1] / 'knowledge/medical'

def load_documents(root=MEDICAL_ROOT):
    root = Path(root).resolve()
    sources = [json.loads(line) for line in (root / 'sources.jsonl').read_text(encoding='utf-8').splitlines()]
    editorial = json.loads((root / 'editorial-sections.json').read_text(encoding='utf-8'))
    documents, errors = [], []
    for source in sources:
        sid = source.get('id')
        if not sid or source.get('status') != 'accepted' or not (source.get('allowed_use') or {}).get('local_ingest'):
            continue
        if sid not in editorial:
            continue
        path = (root / source.get('source_path', f"raw/{sid}.txt")).resolve()
        if not path.exists() or not path.is_relative_to(root / 'raw'): continue
        raw = path.read_text(encoding='utf-8')
        if source.get('source_sha256') and hashlib.sha256(raw.encode()).hexdigest() != source['source_sha256']:
            continue
        text, sections = '', []
        for section in editorial.get(sid, []):
            spans = []
            for quote in section['quotes']:
                start = raw.lower().find(quote.lower())
                if start < 0:
                    errors.append(sid + ': ' + quote)
                else:
                    spans.append({'start': start, 'end': start + len(quote), 'quote': raw[start:start+len(quote)]})
            body = section['heading'] + '\n' + section['text'] + '\n英文依据：' + '\n'.join(s['quote'] for s in spans)
            if len(body) > 900: raise ValueError('EDITORIAL_SECTION_TOO_LONG: ' + sid)
            start = len(text)
            text += body
            sections.append({'start': start, 'end': len(text), 'text': body, 'section': section['heading'], 'source_spans': spans})
            text += '\n\n'
        version = source['source_sha256'][:12] + '-zh-' + hashlib.sha256(text.encode()).hexdigest()[:12]
        documents.append({'id': sid, 'version': version, 'title': source['title_zh'], 'url': source['url'],
            'text': text, 'sections': sections, 'synthetic': False, 'content_kind': 'medical_editorial_excerpt',
            'publisher': source['publisher'], 'language': 'zh-CN-editorial', 'source_language': source['source_language'],
            'jurisdiction': source['source_jurisdiction'], 'source_family_id': source['source_family_id'],
            'source_sha256': source['source_sha256'], 'provenance_status': source['provenance_status'],
            'clinical_review_status': 'not_reviewed', 'editorial_status': 'Codex_editorial_not_official_translation',
            'topic': source['topic'], 'publication_date': source['publication_date'], 'fetched_at': source['fetched_at'],
            'license': source['license'], 'license_url': source['license_url'], 'attribution': source['attribution']})
    if errors: raise ValueError('EVIDENCE_QUOTES_NOT_FOUND\n' + '\n'.join(errors))
    missing_editorial = [k for k in editorial if k not in {s['id'] for s in sources}]
    if missing_editorial: raise ValueError('SOURCE_EDITORIAL_SET_MISMATCH: ' + ','.join(missing_editorial))
    return documents

def corpus_hash(documents):
    return hashlib.sha256(json.dumps(documents, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

TOPIC_ZH_MAP = {
    'respiratory_medicine': '呼吸内科',
    'gastroenterology': '消化内科',
    'emergency_medicine': '急症与急救',
    'obstetrics_gynecology': '妇产科',
    'pediatrics': '儿科',
    'hypertension': '心血管与高血压',
    'cardiovascular': '心血管内科',
    'type2_diabetes': '内分泌与糖尿病',
    'endocrinology': '内分泌代谢科',
    'neurology': '神经内科',
    'oncology': '肿瘤早筛与预防',
    'infection_control': '感染与抗感染原则',
    'shared': '慢病共病与健康管理',
}

def get_catalog_overview(root=MEDICAL_ROOT):
    root = Path(root).resolve()
    sources = [json.loads(line) for line in (root / 'sources.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    editorial = json.loads((root / 'editorial-sections.json').read_text(encoding='utf-8'))
    items = []
    for s in sources:
        sid = s['id']
        sec_list = editorial.get(sid, [])
        topic_en = s.get('topic', 'general')
        items.append({
            'id': sid,
            'title': s.get('title_zh') or s.get('title'),
            'title_en': s.get('title'),
            'topic': topic_en,
            'topic_zh': TOPIC_ZH_MAP.get(topic_en, '综合医学'),
            'jurisdiction': s.get('source_jurisdiction', 'INT'),
            'publisher': s.get('publisher', ''),
            'publication_date': s.get('publication_date', ''),
            'url': s.get('url', ''),
            'attribution': s.get('attribution', ''),
            'license': s.get('license', ''),
            'section_count': len(sec_list),
            'sections': [{'heading': sec.get('heading', ''), 'text': sec.get('text', ''), 'quotes': sec.get('quotes', [])} for sec in sec_list]
        })
    return {
        'total_documents': len(items),
        'total_sections': sum(it['section_count'] for it in items),
        'items': items,
    }

