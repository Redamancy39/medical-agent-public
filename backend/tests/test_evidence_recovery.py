from fastapi.testclient import TestClient
from app.agent import source_documents
from app.main import create_app
from test_api import settings, login, session
from test_graph import ask, call
from test_multitask import task


def test_recheck_keeps_retrieved_documents_and_original_budget(settings):
    app = create_app(settings.model_copy(update={'maintenance_enabled': False}))
    app.state.model.plan = lambda s: {'tasks': [task('explain', require_sources=True),
        task('scope', dependencies=['explain'])]}
    def decide(s):
        if s['task_id'] == 'scope': return {'answer': 'scope'}
        if s.get('refinement'):
            return {'answer': 'supported', 'source_ids': [d['id'] for d in source_documents(s)]}
        if not s['observations']: return {'tool_calls': [call(query='synthetic evidence')]}
        return {'answer': 'first answer omitted citations', 'source_ids': []}
    app.state.model.decide = decide
    with TestClient(app) as client:
        headers = login(client)
        result = ask(client, headers, session(client, headers), '多任务').json()
        assert result['result_status'] == 'completed'
        assert result['model_calls'] == 6 and result['tool_calls'] == 1
        assert result['sources'] and result['refinement_count'] == 1
        diagnostics = result['evidence_diagnostics']
        assert diagnostics[0]['retrieved_count'] > 0
        assert any(d['stage'] == 'citation_selection' and d['selected_count'] == 0 for d in diagnostics)
