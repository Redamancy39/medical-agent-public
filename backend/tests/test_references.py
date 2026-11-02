import pytest
from test_api import app, client, login, session, settings
from test_graph import ask, call


def test_same_chunk_different_query_scores_is_not_a_source_conflict(client, app):
    app.state.model.decide = lambda s: ({'tool_calls': [call(query='a'), call(query='b')]} if not s['observations']
                                       else {'answer': '同一资料', 'source_ids': ['same']})
    app.state.flow.tools.execute = lambda name, args, s: {'success': True, 'documents': [
        {'id': 'same', 'document_id': 'sop', 'source': 'milvus_local', 'content': '相同原文', 'verified': False,
         'score': 0.5 if args['query'] == 'a' else 0.6, 'rerank_score': 0.8 if args['query'] == 'a' else 0.7}]}
    headers = login(client)
    result = ask(client, headers, session(client, headers), '检索').json()
    assert result['result_status'] == 'completed' and len(result['sources']) == 1


@pytest.mark.parametrize('chunks,expected', [(1, 'completed'), (2, 'failed')])
def test_document_alias_resolves_only_when_one_chunk_is_observed(client, app, chunks, expected):
    app.state.model.decide = lambda s: ({'tool_calls': [call(query='x')]} if not s['observations']
                                       else {'answer': '引用文档', 'source_ids': ['sop']})
    app.state.flow.tools.execute = lambda *args: {'success': True, 'documents': [
        {'id': 'chunk-' + str(i), 'document_id': 'sop', 'source': 'milvus_local', 'content': str(i), 'verified': False}
        for i in range(chunks)]}
    headers = login(client)
    result = ask(client, headers, session(client, headers), '检索').json()
    assert result['result_status'] == expected
    if chunks == 1:
        assert result['sources'][0]['id'] == 'chunk-0'
    else:
        assert result['safe_error_code'] == 'OUTPUT_INVALID'
