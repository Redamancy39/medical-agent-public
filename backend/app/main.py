import logging
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, OperationalError

from .config import load_settings
from .database import Store
from .models import Conversation, ExecutionEvent, MemoryFact, MemoryJob, Message, ProviderCall, Run, SessionSummary, User
import json
from .providers import DeepSeekModel, Gateway, Mem0Memory, PubMedSearch
from .knowledge import BGEEmbedding, KnowledgeStore, LocalReranker
from .medical_corpus import get_catalog_overview
from .runtime_tools import RuntimeTools
from .schemas import AuthInput, ChatInput, MemoryEdit, MessageOut, MessagePage, ResumeInput, RunOut, SessionInput, SessionOut, SessionPage, TokenOut, UserOut, SessionLearningStateOut
from .security import HASHER, issue_token, password_matches, verify_token
from .service import ApiError, owned_session, run_output
from .agent import FakeModel
from .workflow import SingleAgentFlow
from .registration import RegistrationService, Prepare, Revision, Edit, Confirm, PROJECTS, SAMPLE_TYPES, STORAGES

logger = logging.getLogger('medical_backend')
bearer = HTTPBearer(auto_error=False)


def create_app(settings=None, *, transport=None):
    settings = settings or load_settings()
    if settings.deepseek_enabled and not settings.deepseek_api_key.get_secret_value() or settings.mem0_enabled and not settings.mem0_api_key.get_secret_value():
        raise RuntimeError('离线配置未提供所启用provider的密钥；请检查后端配置')
    store = Store(settings.database_path)

    @asynccontextmanager
    async def lifespan(app):
        store.initialize()
        external = settings.deepseek_enabled or settings.mem0_enabled or settings.web_search_enabled
        gateway = Gateway(store, settings, transport) if external else None
        app.state.gateway = gateway
        if settings.deepseek_enabled:
            app.state.model = DeepSeekModel(gateway, settings)
        memory = Mem0Memory(gateway, settings) if settings.mem0_enabled else None
        tools = None
        if external or settings.knowledge_enabled:
            knowledge = KnowledgeStore(settings.knowledge_database, BGEEmbedding(settings.embedding_cache),
                LocalReranker(settings.reranker_path, device=settings.reranker_device) if settings.reranker_enabled else None) if settings.knowledge_enabled else None
            tools = RuntimeTools(knowledge, PubMedSearch(gateway) if settings.web_search_enabled else None)
        app.state.flow = SingleAgentFlow(store, settings, app.state.model, memory=memory, tools=tools)
        app.state.flow.maintenance.kick()
        try:
            yield
        finally:
            app.state.flow.close()
            if gateway:
                gateway.close()
            store.engine.dispose()

    app = FastAPI(title='Medical Agent · LangGraph', version='0.7.0', lifespan=lifespan)
    app.state.store, app.state.settings, app.state.model = store, settings, FakeModel()
    registration = RegistrationService(store)
    dummy_hash = HASHER.hash('local-dummy-password-not-a-user-account')
    app.add_middleware(CORSMiddleware, allow_origins=['http://127.0.0.1:5178', 'http://localhost:5178'],
                       allow_methods=['GET', 'POST'], allow_headers=['Authorization', 'Content-Type'])

    @app.middleware('http')
    async def correlate(request, call_next):
        request.state.trace_id = str(uuid4())
        try:
            response = await call_next(request)
        except Exception as error:
            # Catch before ServerErrorMiddleware re-raises to server logging.
            logger.error('internal_error request_id=%s type=%s', request.state.trace_id, type(error).__name__)
            response = error_response(request, 500, 'INTERNAL_ERROR', '本轮处理未能可靠保存，请稍后重试')
        response.headers['X-Request-ID'] = request.state.trace_id
        return response

    def error_response(request, status, code, message, **details):
        return JSONResponse(status_code=status, content={
            'error': {'code': code, 'message': message, **details},
            'request_id': getattr(request.state, 'trace_id', str(uuid4())),
        }, headers={'WWW-Authenticate': 'Bearer'} if status == 401 else None)

    @app.exception_handler(ApiError)
    async def api_error(request, error):
        return error_response(request, error.status, error.code, error.message)

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request, error):
        fields = [{'location': '.'.join(map(str, item['loc'])), 'type': item['type']} for item in error.errors()]
        return error_response(request, 422, 'VALIDATION_ERROR', '输入字段不符合要求', fields=fields)

    @app.exception_handler(OperationalError)
    async def database_unavailable(request, error):
        logger.warning('database_unavailable request_id=%s', request.state.trace_id)
        return error_response(request, 503, 'DATABASE_UNAVAILABLE', '数据库暂时不可用，请稍后重试')

    def get_db():
        with store.sessions() as db:
            yield db

    def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if credentials is None:
            raise ApiError(401, 'AUTH_REQUIRED', '请先登录')
        try:
            user_id = verify_token(credentials.credentials, settings)
        except (InvalidTokenError, ValueError):
            raise ApiError(401, 'INVALID_TOKEN', '登录凭证无效或已过期') from None
        with store.sessions() as db:
            user = db.get(User, user_id)
            if user is None or not user.active:
                raise ApiError(401, 'INVALID_TOKEN', '登录凭证无效或用户已停用')
            return UserOut.model_validate(user)

    @app.get('/health', tags=['基础'])
    def health(db=Depends(get_db)):
        db.execute(text('SELECT 1'))
        reranker = getattr(getattr(app.state.flow.tools, 'knowledge', None), 'reranker', None)
        return {'status': 'ok', 'database': 'ok', 'mode': 'cloud_real' if settings.deepseek_enabled else (
                    'hybrid' if settings.mem0_enabled or settings.knowledge_enabled or settings.web_search_enabled else 'offline_fake'),
                'external_calls_enabled': settings.deepseek_enabled or settings.mem0_enabled or settings.web_search_enabled,
                'providers': {'model': 'deepseek' if settings.deepseek_enabled else 'fake',
                              'memory': 'mem0' if settings.mem0_enabled else 'fake',
                              'knowledge': 'milvus_bge' if settings.knowledge_enabled else 'fake',
                              'web': 'pubmed' if settings.web_search_enabled else 'disabled',
                              'reranker': 'local_bge_v2_m3' if settings.reranker_enabled else 'disabled',
                              'reranker_device': getattr(reranker, 'device', None)},
                'workflow': 'langgraph_task_dag', 'graph_version': app.state.flow.version,
                'knowledge_profile': settings.knowledge_profile}

    @app.get('/knowledge/catalog', tags=['知识库'])
    def knowledge_catalog():
        return get_catalog_overview()

    @app.post('/auth/register', status_code=201, response_model=UserOut, tags=['本地认证'])
    def register(body: AuthInput, db=Depends(get_db)):
        user = User(username=body.username, password_hash=HASHER.hash(body.password))
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise ApiError(409, 'USERNAME_EXISTS', '该用户名已注册') from None
        return user

    @app.post('/auth/login', response_model=TokenOut, tags=['本地认证'])
    def login(body: AuthInput, db=Depends(get_db)):
        user = db.scalar(select(User).where(User.username == body.username))
        valid = password_matches(user.password_hash if user else dummy_hash, body.password)
        if user is None or not valid or not user.active:
            raise ApiError(401, 'INVALID_CREDENTIALS', '用户名或密码不正确')
        return TokenOut(access_token=issue_token(user.id, settings), expires_in=settings.token_minutes * 60)

    @app.get('/auth/me', response_model=UserOut, tags=['本地认证'])
    def me(user=Depends(current_user)):
        return user

    @app.post('/sessions', status_code=201, response_model=SessionOut, tags=['会话'])
    def create_session(body: SessionInput, user=Depends(current_user), db=Depends(get_db)):
        conversation = Conversation(user_id=user.id, title=body.title)
        db.add(conversation)
        db.commit()
        return conversation

    @app.get('/sessions', response_model=SessionPage, tags=['会话'])
    def list_sessions(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), user=Depends(current_user), db=Depends(get_db)):
        scope = Conversation.user_id == user.id
        items = db.scalars(select(Conversation).where(scope).order_by(Conversation.updated_at.desc(), Conversation.id).limit(limit).offset(offset)).all()
        total = db.scalar(select(func.count()).select_from(Conversation).where(scope))
        return SessionPage(items=[SessionOut.model_validate(item) for item in items], total=total)

    @app.get('/sessions/{session_id}', response_model=SessionOut, tags=['会话'])
    def get_session(session_id: UUID, user=Depends(current_user), db=Depends(get_db)):
        return owned_session(db, str(session_id), user.id)

    @app.get('/sessions/{session_id}/learning-state', response_model=SessionLearningStateOut, tags=['会话'])
    def learning_state(session_id: UUID, user=Depends(current_user), db=Depends(get_db)):
        owned_session(db, str(session_id), user.id)
        from .models import SessionLearningState
        row = db.get(SessionLearningState, str(session_id))
        return SessionLearningStateOut(
            learning_goal=row.learning_goal if row else '心血管与慢病循证知识学习',
            completed_topics=json.loads(row.completed_topics_json) if row else [],
            unresolved_questions=json.loads(row.unresolved_questions_json) if row else [],
            next_steps=json.loads(row.next_steps_json) if row else [],
            last_topic=row.last_topic if row else None,
            last_entities=json.loads(row.last_entities_json) if row else [],
            updated_at=row.updated_at if row else timestamp()
        )

    @app.get('/sessions/{session_id}/messages', response_model=MessagePage, tags=['会话'])
    def history(session_id: UUID, after_seq: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), user=Depends(current_user), db=Depends(get_db)):
        owned_session(db, str(session_id), user.id)
        items = db.scalars(select(Message).where(Message.session_id == str(session_id), Message.seq > after_seq).order_by(Message.seq).limit(limit + 1)).all()
        has_more = len(items) > limit
        items = items[:limit]
        return MessagePage(items=[MessageOut.model_validate(item) for item in items], has_more=has_more,
                           next_after_seq=items[-1].seq if items else after_seq)

    @app.get('/sessions/{session_id}/runs', response_model=list[RunOut], tags=['运行记录'])
    def session_runs(session_id: UUID, limit: int = Query(10, ge=1, le=50), user=Depends(current_user), db=Depends(get_db)):
        owned_session(db, str(session_id), user.id)
        items = db.scalars(select(Run).where(Run.session_id == str(session_id)).order_by(Run.created_at.desc()).limit(limit)).all()
        return [run_output(run) for run in items]

    @app.post('/sessions/{session_id}/chat', response_model=RunOut, tags=['离线模拟对话'])
    def chat(session_id: UUID, body: ChatInput, user=Depends(current_user)):
        return app.state.flow.submit(user.id, str(session_id), body)

    @app.get('/runs/{run_id}', response_model=RunOut, tags=['运行记录'])
    def get_run(run_id: UUID, user=Depends(current_user), db=Depends(get_db)):
        run = db.scalar(select(Run).where(Run.id == str(run_id), Run.user_id == user.id))
        if run is None:
            raise ApiError(404, 'RUN_NOT_FOUND', '运行记录不存在或不可访问')
        return run_output(run)

    @app.get('/runs/{run_id}/events', tags=['运行记录'])
    def events(run_id: UUID, user=Depends(current_user), db=Depends(get_db)):
        app.state.flow.owned_run(db, str(run_id), user.id)
        items = db.scalars(select(ExecutionEvent).where(ExecutionEvent.run_id == str(run_id)).order_by(ExecutionEvent.id)).all()
        return {'items': [{'stage': item.stage.split(':', 1)[0],
                           'task_id': item.stage.split(':', 1)[1] if ':' in item.stage else None,
                           'status': item.status, 'created_at': item.created_at} for item in items]}

    @app.post('/runs/{run_id}/resume', response_model=RunOut, tags=['运行记录'])
    def resume(run_id: UUID, body: ResumeInput, user=Depends(current_user)):
        return app.state.flow.resume(user.id, str(run_id), body)

    @app.post('/runs/{run_id}/cancel', response_model=RunOut, tags=['运行记录'])
    def cancel(run_id: UUID, user=Depends(current_user)):
        return app.state.flow.cancel(user.id, str(run_id))

    @app.get('/runs/{run_id}/providers', tags=['运行记录'])
    def provider_calls(run_id: UUID, user=Depends(current_user), db=Depends(get_db)):
        app.state.flow.owned_run(db, str(run_id), user.id)
        rows = db.scalars(select(ProviderCall).where(ProviderCall.run_id == str(run_id)).order_by(ProviderCall.created_at)).all()
        return {'items': [{'provider': r.provider, 'operation': r.operation, 'status': r.status,
                          'http_status': r.http_status, 'safe_error_code': r.safe_error_code,
                          'elapsed_seconds': r.elapsed_seconds, 'usage': json.loads(r.usage_json)} for r in rows]}

    @app.get('/sessions/{session_id}/summary', tags=['记忆维护'])
    def summary(session_id: UUID, user=Depends(current_user), db=Depends(get_db)):
        owned_session(db, str(session_id), user.id)
        row = db.get(SessionSummary, str(session_id))
        return {'status': row.status if row else 'empty', 'content': row.content if row else None,
                'covered_until_seq': row.covered_until_seq if row else 0, 'version': row.version if row else 0}

    @app.get('/memories', tags=['记忆维护'])
    def memories(user=Depends(current_user), db=Depends(get_db)):
        return {'items': [{'id': row.id, 'key': row.key, 'content': row.content, 'status': row.status,
                           'version': row.version, 'synced_version': row.synced_version,
                           'entity_type': getattr(row, 'entity_type', 'self')}
                          for row in db.scalars(select(MemoryFact).where(MemoryFact.user_id == user.id))]}

    @app.post('/memories/{fact_id}', tags=['记忆维护'])
    def edit_memory(fact_id: UUID, body: MemoryEdit, user=Depends(current_user)):
        return app.state.flow.maintenance.edit(user.id, str(fact_id), body.operation, body.content)

    @app.get('/maintenance/jobs', tags=['记忆维护'])
    def jobs(user=Depends(current_user), db=Depends(get_db)):
        rows = db.scalars(select(MemoryJob).where(MemoryJob.user_id == user.id).order_by(MemoryJob.created_at.desc()).limit(100))
        return {'items': [{'id': row.id, 'run_id': row.run_id, 'action': row.action, 'status': row.status,
                           'attempts': row.attempts, 'safe_error_code': row.safe_error_code} for row in rows]}

    @app.post('/maintenance/retry', tags=['记忆维护'])
    def retry_maintenance(user=Depends(current_user)):
        app.state.flow.maintenance.drain(user.id, retry=True)
        return {'status': 'processed_bounded_batch'}

    @app.get('/registration-options', tags=['模拟登记'])
    def registration_options(user=Depends(current_user)):
        return {'projects': PROJECTS, 'sample_types': SAMPLE_TYPES, 'storages': STORAGES, 'business_mode': 'synthetic_sql'}

    @app.post('/sessions/{session_id}/registration-drafts', tags=['模拟登记'])
    def prepare_registration(session_id: UUID, body: Prepare, user=Depends(current_user)):
        return registration.execute(user.id, 'prepare', str(session_id), body)

    @app.get('/sessions/{session_id}/registration-drafts', tags=['模拟登记'])
    def session_drafts(session_id: UUID, user=Depends(current_user)):
        return registration.drafts(user.id, str(session_id))

    @app.get('/registration-drafts/{draft_id}', tags=['模拟登记'])
    def get_draft(draft_id: UUID, user=Depends(current_user)):
        return registration.get(user.id, str(draft_id))

    @app.get('/registration-drafts/{draft_id}/audit', tags=['模拟登记'])
    def draft_audit(draft_id: UUID, user=Depends(current_user)):
        return registration.audit(user.id, str(draft_id))

    @app.post('/registration-drafts/{draft_id}/edit', tags=['模拟登记'])
    def edit_draft(draft_id: UUID, body: Edit, user=Depends(current_user)):
        return registration.execute(user.id, 'edit', str(draft_id), body)

    @app.post('/registration-drafts/{draft_id}/review', tags=['模拟登记'])
    def review_draft(draft_id: UUID, body: Revision, user=Depends(current_user)):
        return registration.execute(user.id, 'review', str(draft_id), body)

    @app.post('/registration-drafts/{draft_id}/confirm', tags=['模拟登记'])
    def confirm_draft(draft_id: UUID, body: Confirm, user=Depends(current_user)):
        return registration.execute(user.id, 'confirm', str(draft_id), body)

    @app.post('/registration-drafts/{draft_id}/cancel', tags=['模拟登记'])
    def cancel_draft(draft_id: UUID, body: Revision, user=Depends(current_user)):
        return registration.execute(user.id, 'cancel', str(draft_id), body)

    @app.get('/registration-records', tags=['模拟登记'])
    def registration_records(user=Depends(current_user)):
        return registration.records(user.id)

    return app
