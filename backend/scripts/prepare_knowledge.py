"""Explicitly download BGE once, then import only owned synthetic documents."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.knowledge import BGEEmbedding, KnowledgeStore, LocalReranker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--download-model', action='store_true')
    parser.add_argument('--rerank', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    embedding = BGEEmbedding(root / 'data/models', allow_download=args.download_model)
    documents = json.loads((root / 'knowledge/synthetic-documents.json').read_text(encoding='utf-8'))
    reranker = LocalReranker('D:/rag_project/models/reranker/bge-reranker-v2-m3') if args.rerank else None
    with KnowledgeStore(root / 'data/knowledge_v3.db', embedding, reranker) as knowledge:
        result = knowledge.import_documents(documents)
        print(json.dumps({'embedding': result['embedding'], 'documents': result['documents'],
                          'chunks': knowledge.count(), 'retrieval_hits': len(knowledge.search('样本登记草稿确认取消'))}))


if __name__ == '__main__':
    main()
