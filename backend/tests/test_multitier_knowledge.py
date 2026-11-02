# -*- coding: utf-8 -*-
import pytest
from pathlib import Path
from app.knowledge import KnowledgeStore, BGEEmbedding, HashEmbedding
from app.agent import Source
from app.medical_quality import source_catalog
from app.medical_reviewer import build_packet
from app.prompt_context import document_context


def test_textbooks_catalog_registration():
    catalog = source_catalog()
    assert 'tb-cardio-athero-pathophys' in catalog
    item = catalog['tb-cardio-athero-pathophys']
    assert item['book'] == '内科学'
    assert item['edition'] == '第10版'
    assert item['year'] == 2024
    assert len(item['raw']) > 500
    assert item['editorial_version'].endswith('-tb-10th')


def test_textbook_citation_in_reviewer_packet():
    catalog = source_catalog()
    tb_item = catalog['tb-cardio-athero-pathophys']
    quote = 'Atherosclerosis, AS'
    assert quote in tb_item['raw']
    start = tb_item['raw'].find(quote)
    end = start + len(quote)

    tb_source = {
        'id': 'tb-cardio-test-01',
        'source': 'milvus_local',
        'document_id': 'tb-cardio-athero-pathophys',
        'content': tb_item['raw'][start:end],
        'version': tb_item['editorial_version'],
        'source_sha256': tb_item['source_sha256'],
        'start': start,
        'end': end,
        'source_spans': [{'start': start, 'end': end, 'quote': quote}],
        'tier': 'Tier 2: 经典医学教材',
        'book': '内科学',
        'edition': '第10版',
        'year': 2024,
    }
    Source.model_validate(tb_source)
    doc_ctx = document_context(tb_source)
    assert doc_ctx['year'] == 2024
    assert doc_ctx['book'] == '内科学'

    packet = build_packet('动脉粥样硬化的概念？', '动脉粥样硬化（Atherosclerosis, AS）是多种致病因素引起的大中动脉病变。', [tb_source])
    assert any(e['document_id'] == 'tb-cardio-athero-pathophys' for e in packet['evidence'])


def test_knowledge_store_multitier_integration(tmp_path):
    with KnowledgeStore(tmp_path / 'fixture.db', HashEmbedding()) as store:
        assert store.textbook_client is None
        hits = store.search('高血压', limit=2, threshold=-1)
        assert isinstance(hits, list)
