"""Build a separate medical KB from checked public sources; local models only."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding='utf-8')
from app.medical_corpus import load_documents, corpus_hash
from app.knowledge import BGEEmbedding, KnowledgeStore, LocalReranker

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--rerank', action='store_true')
    args = parser.parse_args()
    documents = load_documents()
    root = Path(__file__).resolve().parents[1]
    if args.check_only:
        print({'sources': len(documents), 'sections': sum(len(d['sections']) for d in documents), 'status': 'source_binding_checked_not_clinical_review'})
        return
    embedding = BGEEmbedding(root / 'data/models')
    reranker = LocalReranker('D:/rag_project/models/reranker/bge-reranker-v2-m3') if args.rerank else None
    with KnowledgeStore(root / 'data/knowledge_medical_v1.db', embedding, reranker) as knowledge:
        first = knowledge.import_documents(documents)
        again = knowledge.import_documents(documents)
        assert first['chunk_ids'] == again['chunk_ids']
        count = knowledge.count()
        assert count == sum(len(d['sections']) for d in documents)
        hits = knowledge.search('高血压收缩压舒张压区别', 5)
        report = {'status': 'passed', 'documents': len(documents), 'chunks': count, 'corpus_sha256': corpus_hash(documents),
                  'embedding': embedding.name, 'reranker': reranker.name if reranker else None,
                  'idempotent_import': True, 'probe_hits': len(hits), 'clinical_review': 'not_reviewed'}
        (root / 'knowledge/medical/build-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False))

if __name__ == '__main__': main()
