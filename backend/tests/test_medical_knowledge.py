from app.knowledge import HashEmbedding, KnowledgeStore
from app.medical_corpus import load_documents
from app.agent import Source

def test_medical_section_positions_and_provenance_are_preserved(tmp_path):
    doc = load_documents()[0]
    with KnowledgeStore(tmp_path / 'medical.db', HashEmbedding()) as knowledge:
        first = knowledge.import_documents([doc])
        assert len(first['chunk_ids']) == len(doc['sections']) == 2
        assert knowledge.import_documents([doc])['chunk_ids'] == first['chunk_ids']
        hits = knowledge.search('收缩压舒张压', 2, threshold=-1)
        assert len(hits) == 2
        for hit in hits:
            Source.model_validate(hit)
            assert hit['content'] == doc['text'][hit['start']:hit['end']]
            assert hit['source_sha256'] == doc['source_sha256']
            assert hit['section'] and hit['source_spans']
            assert hit['clinical_review_status'] == 'not_reviewed' and hit['verified'] is False
            assert hit['content_kind'] == 'medical_editorial_excerpt'

def test_corpus_binding_and_source_families():
    docs = load_documents()
    nlm_docs = [d for d in docs if d['id'].startswith('nlm-')]
    assert len(nlm_docs) == len({d['source_family_id'] for d in nlm_docs}) == 20
    assert sum(len(d['sections']) for d in nlm_docs) == 40
    assert all(d['url'].startswith('https://medlineplus.gov/') for d in nlm_docs)
    assert len(docs) >= 20
    assert len(docs) == len({d['source_family_id'] for d in docs})
