"""Stage original TXT files; optional local candidate index, never the formal KB."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
from app.medical_ingestion import TxtIngestion, candidate_documents, _json_write

FILENAMES = ('01_lifestyle_hypertension.txt', '02_lifestyle_diabetes.txt',
             '20_guideline_hypertension.txt', '21_guideline_diabetes.txt')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--files', nargs='+', type=Path)
    parser.add_argument('--index-candidates', action='store_true', help='Build separate unverified candidate Milvus; local models only')
    parser.add_argument('--rerank', action='store_true')
    parser.add_argument('--query', default='高血压生活方式与测量条件')
    args = parser.parse_args()
    paths = args.files or [ROOT.parent / 'medix-agent-swarm/knowledge/data/documents' / f for f in FILENAMES]
    intake_root = ROOT / 'knowledge/medical-local'
    report = TxtIngestion(intake_root).stage(paths)
    print(json.dumps({'mode': 'txt_candidate_intake', **report['summary'], 'formal_kb': 'unchanged'}, ensure_ascii=False))
    if not args.index_candidates:
        return
    from app.knowledge import BGEEmbedding, KnowledgeStore, LocalReranker
    docs = candidate_documents(report)
    if not docs:
        raise RuntimeError('NO_CANDIDATE_DOCUMENTS')
    embedding = BGEEmbedding(ROOT / 'data/models')
    reranker = LocalReranker('D:/rag_project/models/reranker/bge-reranker-v2-m3') if args.rerank else None
    path = ROOT / 'data/knowledge_medical_candidates_v1.db'
    with KnowledgeStore(path, embedding, reranker) as store:
        first = store.import_documents(docs, skip_unchanged=True)
        repeated = store.import_documents(docs, skip_unchanged=True)
        assert first['chunk_ids'] == repeated['chunk_ids'] and repeated['skipped_documents'] == len(docs)
        hits = store.search(args.query, 5)
        result = {'mode': 'unverified_candidate_kb', 'documents_this_batch': len(docs),
            'chunks_this_batch': first['chunks'], 'collection_chunks': store.count(),
            'skipped_unchanged_documents': first['skipped_documents'], 'idempotent_import': True,
            'embedding': embedding.name, 'reranker': reranker.name if reranker else None,
            'probe_hits': len(hits), 'clinical_review': 'not_run', 'formal_kb': 'unchanged', 'hits': hits}
    _json_write(intake_root / 'index-report.json', result)
    for record in report['records']:
        if record.get('document'):
            record['stages'].append({'stage': 'candidate_index', 'status': 'completed',
                                     'admission_status': 'pending_source_review'})
    _json_write(intake_root / 'last-report.json', report)
    print(json.dumps({k: v for k, v in result.items() if k != 'hits'}, ensure_ascii=False))


if __name__ == '__main__': main()
