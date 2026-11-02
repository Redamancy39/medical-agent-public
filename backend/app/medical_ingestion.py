"""TXT intake adapted from rag-agent's staged design; no cloud or clinical claims."""
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

POLICY_VERSION = 'medical-txt-intake-v1'
PROJECT_ROOT = Path(__file__).resolve().parents[2]
HEADING = re.compile(r'(?m)^(?:[一二三四五六七八九十]+、[^\n]+|#{1,6}\s+[^\n]+|【[^\n】]+】[^\n]*)')


class IngestionError(ValueError):
    pass


@dataclass
class DocumentBlock:
    start: int
    end: int
    text: str
    section: str
    source_spans: list


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_txt(path):
    path = Path(path)
    if path.suffix.lower() != '.txt': raise IngestionError('FILE_TYPE_UNSUPPORTED')
    if path.stat().st_size > 2_000_000: raise IngestionError('FILE_TOO_LARGE')
    raw = path.read_bytes()
    encodings = ('utf-8-sig',) if raw.startswith(b'\xef\xbb\xbf') else ('utf-8', 'gb18030')
    for encoding in encodings:
        try:
            decoded = raw.decode(encoding, errors='strict')
            break
        except UnicodeDecodeError:
            continue
    else:
        raise IngestionError('TEXT_DECODE_FAILED')
    if any(ord(c) < 32 and c not in '\r\n\t' for c in decoded) or '\ufffd' in decoded:
        raise IngestionError('TEXT_CONTROL_CHARACTERS')
    text = decoded.replace('\r\n', '\n').replace('\r', '\n')
    if not text.strip(): raise IngestionError('TEXT_EMPTY')
    if len(text) > 200000: raise IngestionError('TEXT_TOO_LARGE')
    return {'text': text, 'encoding': encoding, 'raw_source_sha256': sha256(raw),
            'source_sha256': sha256(text.encode('utf-8')), 'raw': raw,
            'offset_basis': 'decoded_text_lf_unicode'}


def section_blocks(text, size=900):
    if not 100 <= size <= 1000: raise IngestionError('CHUNK_SIZE_INVALID')
    headings = list(HEADING.finditer(text))
    boundaries = sorted({0, len(text), *[h.start() for h in headings]})
    result = []
    for start, end in zip(boundaries, boundaries[1:]):
        body = text[start:end]
        if not body.strip(): continue
        section = next((h.group().strip() for h in headings if h.start() == start), '文档说明')
        # Paragraphs are atomic: never silently cut a unit, table row or condition.
        spans = [(start + m.start(), start + m.end()) for m in re.finditer(r'\S[\s\S]*?(?=\n[ \t]*\n|\Z)', body)]
        atoms = []
        for a, b in spans:
            if atoms and _standalone_heading(text[atoms[-1][0]:atoms[-1][1]]):
                atoms[-1] = (atoms[-1][0], b)
            else:
                atoms.append((a, b))
        current = None
        for a, b in atoms:
            if b-a > size: raise IngestionError('ATOMIC_BLOCK_TOO_LONG')
            if current is not None and b-current[0] > size:
                result.append(_block(text, *current, section))
                current = None
            current = (current[0] if current else a, b)
        if current is not None: result.append(_block(text, *current, section))
    if not result: raise IngestionError('CHUNKS_EMPTY')
    return result


def _standalone_heading(text):
    return '\n' not in text and bool(re.match(r'^(?:\d+[.、]|[一二三四五六七八九十]+、|#{1,6}\s|【)', text))


def _block(text, start, end, section):
    quote = text[start:end]
    return asdict(DocumentBlock(start, end, quote, section, [{'start': start, 'end': end, 'quote': quote}]))


def _json_write(path, value):
    temporary = path.with_name(path.name + '.' + uuid4().hex + '.new')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def _snapshot(path, data):
    if path.exists():
        if path.read_bytes() != data: raise IngestionError('SNAPSHOT_HASH_CONFLICT')
        return
    path.write_bytes(data)


class TxtIngestion:
    def __init__(self, root):
        self.root = Path(root).resolve()
        if any(self.root.is_relative_to(PROJECT_ROOT / n) for n in ('medix-agent-swarm', 'MediX-R1')):
            raise IngestionError('REFERENCE_DIRECTORY_READ_ONLY')

    def stage(self, paths):
        for name in ('raw', 'text', 'reports'): (self.root / name).mkdir(parents=True, exist_ok=True)
        manifest_path = self.root / 'manifest.json'
        old = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {'records': []}
        prior = {r['document']['id']: r for r in old['records'] if r.get('document')}
        records, seen = [], {}
        for value in paths:
            path, stages = Path(value).resolve(), []
            record = {'filename': path.name, 'stages': stages, 'safe_error_code': None}
            try:
                parsed = read_txt(path)
                digest = parsed['raw_source_sha256']
                stages.append({'stage': 'file_probe', 'status': 'completed', 'encoding': parsed['encoding']})
                content_digest = parsed['source_sha256']
                if content_digest in seen:
                    record.update(status='duplicate', duplicate_of=seen[content_digest], raw_source_sha256=digest)
                    records.append(record)
                    continue
                document_id = 'local-txt-' + sha256(str(path).encode('utf-8'))[:16]
                seen[content_digest] = document_id
                sections = section_blocks(parsed['text'])
                stages.append({'stage': 'parse_and_chunk', 'status': 'completed', 'chunks': len(sections)})
                flags = ['source_url_missing', 'publication_version_unverified', 'reuse_terms_unverified']
                text = parsed['text']
                publisher = re.search(r'(?m)^发布机构[:：]\s*(.+)', text)
                references = text.split('参考来源：')[-1] if '参考来源：' in text else ''
                if publisher and references and publisher.group(1).strip() not in references:
                    flags.append('publisher_claim_inconsistent')
                short_chunks = sum(len(s['text']) < 80 for s in sections)
                if short_chunks: flags.append('short_chunks_need_context_review')
                stages.append({'stage': 'quality_check', 'status': 'needs_review', 'flags': flags, 'short_chunks': short_chunks})
                version = digest[:12] + '-' + POLICY_VERSION
                raw_path, text_path = 'raw/' + digest + '.txt', 'text/' + digest + '.txt'
                _snapshot(self.root / raw_path, parsed['raw'])
                _snapshot(self.root / text_path, text.encode('utf-8'))
                document = {'id': document_id, 'version': version, 'title': text.splitlines()[0][:300],
                    'text': text, 'sections': sections, 'url': 'local://medical-candidate/' + document_id,
                    'synthetic': False, 'content_kind': 'medical_candidate_excerpt',
                    'publisher': None, 'publication_date': None, 'jurisdiction': None,
                    'language': 'zh-CN', 'source_language': 'zh-CN', 'source_family_id': 'text-' + content_digest,
                    'source_sha256': parsed['source_sha256'], 'raw_source_sha256': digest,
                    'encoding': parsed['encoding'], 'offset_basis': parsed['offset_basis'],
                    'provenance_status': 'pending_source_review', 'clinical_review_status': 'not_reviewed',
                    'editorial_status': 'original_project_text_unverified', 'license': None, 'license_url': None,
                    'attribution': '用户提供的原项目TXT；出处待核对'}
                previous = prior.get(document_id, {})
                # Verify immutable snapshots before declaring an unchanged version.
                unchanged = previous.get('document') == document
                record.update(document=document, raw_snapshot=raw_path, text_snapshot=text_path,
                    status='unchanged' if unchanged else 'staged', admission_status='pending_source_review',
                    quality_flags=flags, claimed_publisher=publisher.group(1).strip() if publisher else None)
                stages.append({'stage': 'source_admission', 'status': 'pending_source_review'})
                prior[document_id] = record
            except (IngestionError, OSError) as error:
                code = str(error) if isinstance(error, IngestionError) else 'FILE_READ_OR_WRITE_FAILED'
                record.update(status='failed', safe_error_code=code)
                stages.append({'stage': 'intake', 'status': 'failed', 'safe_error_code': code})
            records.append(record)
        summary = {'files': len(records), 'documents': sum('document' in r for r in records),
            'failed': sum(r['status'] == 'failed' for r in records),
            'duplicates': sum(r['status'] == 'duplicate' for r in records),
            'unchanged': sum(r['status'] == 'unchanged' for r in records), 'admitted': 0}
        report = {'policy_version': POLICY_VERSION, 'created_at': datetime.now(timezone.utc).isoformat(),
                  'summary': summary, 'records': records, 'clinical_review': 'not_run'}
        _json_write(manifest_path, {'policy_version': POLICY_VERSION, 'records': list(prior.values())})
        _json_write(self.root / 'reports' / (uuid4().hex + '.json'), report)
        _json_write(self.root / 'last-report.json', report)
        return report


def candidate_documents(report):
    return [r['document'] for r in report['records'] if r.get('document') and r.get('admission_status') == 'pending_source_review']
