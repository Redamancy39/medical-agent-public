from fastapi.testclient import TestClient

from app.config import Settings, BACKEND_ROOT
from app.main import create_app
from app.agent import Plan
from test_api import settings, login, session
from test_graph import ask


def test_profile_uses_separate_database(settings):
    medical = settings.model_copy(update={'knowledge_profile': 'medical'})
    assert medical.knowledge_database == BACKEND_ROOT / 'data/knowledge_medical_v1.db'
    assert settings.knowledge_database == BACKEND_ROOT / 'data/knowledge_v3.db'
    assert medical.model_copy(update={'knowledge_path': settings.database_path}).knowledge_database == settings.database_path
    assert Plan.model_validate({'tasks': [{'agent_id': 'research_agent', 'description': '解释'}]}).reason is None


def test_plain_medical_question_reaches_lead_and_reason_persists(settings):
    app = create_app(settings.model_copy(update={'knowledge_profile': 'medical', 'maintenance_enabled': False}))
    seen = []
    def plan(state):
        seen.append(state['question'])
        return {'reason': '一个知识解释目标足够', 'tasks': [{'agent_id': 'consultation_agent', 'description': '解释收缩压'}]}
    app.state.model.plan = plan
    with TestClient(app) as client:
        assert client.get('/health').json()['knowledge_profile'] == 'medical'
        headers = login(client)
        result = ask(client, headers, session(client, headers), '收缩压是什么？').json()
        assert seen == ['收缩压是什么？']
        assert result['plan_status'] == 'completed' and result['task_count'] == 1
        assert result['plan_reason'] == '一个知识解释目标足够'
        assert result['knowledge_profile'] == 'medical'
        saved = client.get('/runs/' + result['run_id'], headers=headers).json()
        assert saved['plan_reason'] == result['plan_reason']
