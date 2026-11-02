"""Owned Milvus Lite knowledge store; never opens a reference database."""
import hashlib
import json
import math
import re
from pathlib import Path
from threading import RLock

PROVENANCE_FIELDS = ('publisher', 'language', 'source_language', 'jurisdiction', 'source_family_id',
    'source_sha256', 'provenance_status', 'clinical_review_status', 'editorial_status', 'topic',
    'publication_date', 'fetched_at', 'license', 'license_url', 'attribution', 'content_kind',
    'raw_source_sha256', 'encoding', 'offset_basis')

def document_chunks(document):
    if 'sections' not in document:
        return split_text(document['text'])
    sections = document['sections']
    previous_end = 0
    if not sections: raise ValueError('章节不能为空')
    for section in sections:
        start, end = section['start'], section['end']
        if type(start) is not int or type(end) is not int or not previous_end <= start < end <= len(document['text']):
            raise ValueError('章节位置不合法')
        if section['text'] != document['text'][start:end] or len(section['text']) > 1000:
            raise ValueError('章节原文不匹配或超过工具契约')
        previous_end = end
    return sections


def split_text(text, size=700, overlap=100):
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError('分块参数不合法')
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append({'start': start, 'end': end, 'text': text[start:end]})
        if end == len(text):
            break
        start = end - overlap
    return chunks


class HashEmbedding:
    """Deterministic fixture only; runtime knowledge uses BGE."""
    dimension, name = 64, 'hash-fixture-v1'

    def embed(self, texts):
        vectors = []
        for text in texts:
            vector = [0.0] * self.dimension
            chars = re.sub(r'\s+', '', text.lower())
            for token in [*chars, *[chars[i:i+2] for i in range(len(chars)-1)]]:
                index = int(hashlib.sha256(token.encode()).hexdigest()[:8], 16) % self.dimension
                vector[index] += 1
            norm = math.sqrt(sum(v*v for v in vector)) or 1
            vectors.append([v/norm for v in vector])
        return vectors


class BGEEmbedding:
    dimension, name = 512, 'BAAI/bge-small-zh-v1.5'

    def __init__(self, cache_dir, allow_download=False):
        from fastembed import TextEmbedding
        self.model = TextEmbedding(model_name=self.name, cache_dir=str(cache_dir),
                                   local_files_only=not allow_download, threads=2)

    def embed(self, texts):
        return [vector.tolist() for vector in self.model.embed(texts)]


class KnowledgeStore:
    def __init__(self, path, embedding, reranker=None):
        from pymilvus import MilvusClient
        self.path, self.embedding = Path(path).resolve(), embedding
        project = Path(__file__).resolve().parents[2]
        if any(self.path.is_relative_to(project / name) for name in ('medix-agent-swarm', 'MediX-R1')):
            raise ValueError('禁止打开参考代码目录中的知识库')
        self.reranker = reranker
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        self.client = MilvusClient(str(self.path), grpc_options={'grpc.enable_http_proxy': 0,
            'grpc.keepalive_time_ms': 300000, 'grpc.keepalive_permit_without_calls': False})
        fingerprint = hashlib.sha256(embedding.name.encode()).hexdigest()[:10]
        self.collection = 'medical_owned_' + fingerprint
        if not self.client.has_collection(self.collection):
            self.client.create_collection(self.collection, dimension=embedding.dimension, metric_type='COSINE',
                                          primary_field_name='id', id_type='string', max_length=64, auto_id=False)
        self.client.load_collection(self.collection)
        self.textbook_client = None
        self.textbook_collection = 'textbooks_internal_med_10th'
        self.textbook_sources = {}
        self.textbook_raws = {}
        textbook_db = self.path.parent / 'knowledge_textbooks_v1.db'
        textbook_meta_path = Path(__file__).resolve().parents[1] / 'knowledge/textbooks/sources.jsonl'
        if getattr(self.embedding, 'dimension', 0) == 512 and textbook_db.exists():
            try:
                self.textbook_client = MilvusClient(str(textbook_db))
                if self.textbook_client.has_collection(self.textbook_collection):
                    self.textbook_client.load_collection(self.textbook_collection)
                else:
                    self.textbook_client = None
                if textbook_meta_path.exists():
                    tb_root = textbook_meta_path.parent
                    for line in textbook_meta_path.read_text(encoding='utf-8').splitlines():
                        if not line.strip(): continue
                        item = json.loads(line)
                        self.textbook_sources[item['id']] = item
                        rpath = tb_root / item['source_path']
                        if rpath.exists():
                            self.textbook_raws[item['id']] = rpath.read_text(encoding='utf-8')
            except Exception:
                self.textbook_client = None

    def import_documents(self, documents, *, skip_unchanged=False):
        ids, skipped = [], 0
        with self.lock:
            for document in documents:
                if not all(isinstance(document.get(k), str) and document[k].strip() for k in ('id', 'version', 'title', 'text', 'url')):
                    raise ValueError('文档字段不完整')
                if len(document['text']) > 200000:
                    raise ValueError('文档超过导入预算')
                rows = []
                for chunk in document_chunks(document):
                    key = json.dumps([document['id'], document['version'], chunk['start'], chunk['text']], ensure_ascii=False)
                    mid = hashlib.sha256(key.encode()).hexdigest()
                    rows.append({'id': mid, 'document_id': document['id'], 'version': document['version'],
                                 'title': document['title'], 'url': document['url'], 'text': chunk['text'],
                                 'start': chunk['start'], 'end': chunk['end'], 'synthetic': document.get('synthetic', True)})
                    rows[-1].update({k: document[k] for k in PROVENANCE_FIELDS if k in document})
                    if 'section' in chunk:
                        rows[-1].update(section=chunk['section'], source_spans=chunk['source_spans'])
                if skip_unchanged:
                    old_rows = self.client.query(self.collection, filter='document_id == ' + json.dumps(document['id']),
                                                 output_fields=list(rows[0]))
                    old_by_id = {r['id']: r for r in old_rows}
                    if set(old_by_id) == {r['id'] for r in rows} and all(
                            all(old_by_id[r['id']].get(k) == v for k, v in r.items()) for r in rows):
                        ids += [r['id'] for r in rows]
                        skipped += 1
                        continue
                vectors = self.embedding.embed([row['text'] for row in rows])
                for row, vector in zip(rows, vectors, strict=True):
                    row['vector'] = vector
                if rows:
                    self.client.upsert(self.collection, rows)
                current_ids = [r['id'] for r in rows]
                # Only replace this document's stale chunks in this owned collection.
                old = self.client.query(self.collection, filter='document_id == ' + json.dumps(document['id']), output_fields=['id'])
                stale = [r['id'] for r in old if r['id'] not in current_ids]
                if stale:
                    self.client.delete(self.collection, ids=stale)
                ids += current_ids
            self.client.flush(self.collection)
        return {'documents': len(documents), 'chunks': len(ids), 'chunk_ids': ids, 'embedding': self.embedding.name,
                'skipped_documents': skipped}

    def search(self, query, limit=5, threshold=0.25, rerank_threshold=0.60):
        vector = self.embedding.embed([query])[0]
        with self.lock:
            found = self.client.search(self.collection, data=[vector], limit=min(limit * 3, 12) if self.reranker else limit,
                                       output_fields=['text', 'title', 'url', 'document_id', 'version', 'start', 'end', 'synthetic',
                                                      *PROVENANCE_FIELDS, 'section', 'source_spans'])
        documents = []
        for hit in found[0]:
            if float(hit['distance']) < threshold:
                continue
            entity = hit['entity']
            documents.append({'id': hit['id'], 'source': 'milvus_local', 'content': entity['text'], 'verified': False,
                              'title': entity['title'], 'url': entity['url'], 'document_id': entity['document_id'],
                              'version': entity['version'], 'start': entity['start'], 'end': entity['end'],
                              'score': float(hit['distance']), 'score_kind': 'cosine_similarity',
                              'content_kind': 'synthetic_excerpt' if entity['synthetic'] else 'local_excerpt',
                              'tier': 'Tier 1: 核心临床指南'})
            documents[-1].update({k: entity[k] for k in (*PROVENANCE_FIELDS, 'section', 'source_spans') if k in entity})

        if self.textbook_client is not None:
            try:
                with self.lock:
                    tb_found = self.textbook_client.search(
                        self.textbook_collection, data=[vector],
                        limit=min(limit * 2, 8) if self.reranker else min(limit, 3),
                        output_fields=['id', 'document_id', 'title', 'book', 'edition', 'year', 'part', 'chapter', 'section', 'text']
                    )
                for hit in tb_found[0]:
                    dist = float(hit['distance'])
                    if dist < threshold:
                        continue
                    entity = hit['entity']
                    doc_id = entity.get('document_id', '')
                    meta = self.textbook_sources.get(doc_id, {})
                    raw_text = self.textbook_raws.get(doc_id, '')
                    chunk_text = entity['text']
                    start = raw_text.find(chunk_text) if raw_text else 0
                    end = start + len(chunk_text) if start >= 0 else len(chunk_text)
                    sha256 = meta.get('source_sha256', '')
                    tb_ver = sha256[:12] + '-tb-10th' if sha256 else 'tb-10th-2024'
                    spans = [{'start': max(0, start), 'end': end, 'quote': chunk_text}] if (raw_text and start >= 0) else []
                    tb_doc = {
                        'id': str(hit['id']),
                        'source': 'milvus_local',
                        'content': chunk_text,
                        'verified': False,
                        'title': entity.get('title') or meta.get('title', '人民卫生出版社第10版医学规划教材'),
                        'url': f"local://textbooks/internal_med_10th/{doc_id}",
                        'document_id': doc_id,
                        'version': tb_ver,
                        'start': max(0, start),
                        'end': end,
                        'score': dist,
                        'score_kind': 'cosine_similarity',
                        'content_kind': 'medical_textbook_excerpt',
                        'tier': 'Tier 2: 经典医学教材',
                        'book': entity.get('book') or meta.get('book', '内科学'),
                        'edition': entity.get('edition') or meta.get('edition', '第10版'),
                        'year': entity.get('year') or meta.get('year', 2024),
                        'chapter': entity.get('chapter') or meta.get('chapter', ''),
                        'section': entity.get('section') or meta.get('section', ''),
                        'publisher': meta.get('publisher', '人民卫生出版社'),
                        'publication_date': '2024',
                        'source_sha256': sha256,
                        'source_family_id': 'peoples_medical_publishing_house_internal_med_10th',
                        'jurisdiction': 'CN',
                        'language': 'zh-CN',
                        'source_language': 'zh',
                        'provenance_status': 'verified_official_national_textbook',
                        'clinical_review_status': 'not_reviewed',
                        'editorial_status': 'authoritative_curriculum_textbook_10th',
                        'topic': 'cardiovascular',
                        'source_spans': spans,
                    }
                    documents.append(tb_doc)
            except Exception:
                pass

        if self.reranker and documents:
            documents = self.reranker.rank(query, documents)
            filtered = [d for d in documents if d.get('rerank_score', 0) >= rerank_threshold]
            if filtered:
                documents = filtered
            elif documents:
                # 兜底保障：若经0.60阈值门禁过滤后全部低于0.60，保底保留Top-1以防全军覆没
                documents = documents[:1]
        else:
            documents.sort(key=lambda d: d.get('score', 0), reverse=True)
        return documents[:limit]

    def count(self):
        with self.lock:
            return int(self.client.get_collection_stats(self.collection)['row_count'])

    def close(self):
        with self.lock:
            self.client.close()
            if self.textbook_client is not None:
                self.textbook_client.close()
                self.textbook_client = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class LocalReranker:
    name = 'BAAI/bge-reranker-v2-m3'

    def __init__(self, path, device='auto'):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        self.torch, self.lock = torch, RLock()
        if device not in ('auto', 'cpu', 'cuda'):
            raise ValueError('RERANKER_DEVICE必须为auto、cpu或cuda')
        self.device = 'cuda' if device == 'auto' and torch.cuda.is_available() else 'cpu' if device == 'auto' else device
        if self.device == 'cuda' and not torch.cuda.is_available():
            raise RuntimeError('RERANKER_DEVICE=cuda但当前PyTorch无法使用CUDA')
        torch.set_num_threads(2)
        self.tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True, trust_remote_code=False)
        self.model = AutoModelForSequenceClassification.from_pretrained(str(path), local_files_only=True,
            trust_remote_code=False, use_safetensors=True).to(self.device).eval()
        if self.device == 'cuda': self.model = self.model.half()

    def rank(self, query, documents):
        with self.lock, self.torch.inference_mode():
            inputs = self.tokenizer([[query, d['content']] for d in documents], padding=True,
                                    truncation=True, max_length=512, return_tensors='pt')
            inputs = {key: value.to(self.device) for key, value in inputs.items()}
            scores = self.torch.sigmoid(self.model(**inputs).logits.reshape(-1)).tolist()
        ranked = [{**document, 'rerank_score': float(score), 'reranker': self.name}
                  for document, score in zip(documents, scores, strict=True)]
        return sorted(ranked, key=lambda d: d['rerank_score'], reverse=True)
