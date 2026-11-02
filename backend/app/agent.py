from copy import deepcopy
import json
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from pydantic_core import PydanticCustomError

ROLES = Literal['consultation_agent', 'research_agent', 'diagnostic_agent']


def source_identity(document):
    # Scores belong to a query; they are not immutable document content.
    return tuple(document.get(k) for k in ('source', 'content', 'document_id', 'version', 'url', 'start', 'end',
                                         'source_sha256', 'raw_source_sha256'))


def source_documents(state):
    documents = [d for o in state['observations'] for d in o['result'].get('documents', [])]
    documents += [d for result in state.get('dependency_results', []) if result['status'] == 'completed' for d in result['sources']]
    return documents


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Task(Contract):
    model_config = ConfigDict(extra='ignore', str_strip_whitespace=True)
    task_id: str = Field(default_factory=lambda: str(uuid4()), pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    agent_id: ROLES
    description: str = Field(min_length=1, max_length=1000)
    depends_on: list[str] = Field(default_factory=list, max_length=3)
    require_sources: bool = False


class Plan(Contract):
    model_config = ConfigDict(extra='ignore', str_strip_whitespace=True)
    tasks: list[Task] = Field(min_length=1, max_length=4)
    reason: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode='after')
    def valid_dag(self):
        ids = {task.task_id for task in self.tasks}
        if len(ids) != len(self.tasks):
            raise PydanticCustomError('plan_task_id_duplicate', '任务ID重复')
        done = set()
        for task in self.tasks:
            if len(set(task.depends_on)) != len(task.depends_on):
                raise PydanticCustomError('plan_dependency_duplicate', '任务依赖重复')
            if not set(task.depends_on) <= ids:
                raise PydanticCustomError('plan_dependency_missing', '任务依赖不存在')
        while len(done) < len(ids):
            ready = {task.task_id for task in self.tasks if task.task_id not in done and set(task.depends_on) <= done}
            if not ready:
                raise PydanticCustomError('plan_dependency_cycle', '依赖存在循环')
            done |= ready
        return self


class Synthesis(Contract):
    answer: str = Field(min_length=1, max_length=4000)
    task_ids: list[str] = Field(min_length=1, max_length=4)
    source_ids: list[str] = Field(default_factory=list, max_length=20)


class ToolCall(Contract):
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=64)
    name: str
    arguments: dict


class Decision(Contract):
    answer: str | None = Field(default=None, min_length=1, max_length=4000)
    tool_calls: list[ToolCall] = Field(default_factory=list, max_length=5)
    source_ids: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode='after')
    def one_action(self):
        if bool(self.answer) == bool(self.tool_calls):
            raise ValueError('必须返回最终答案或工具调用中的一种')
        if len({call.id for call in self.tool_calls}) != len(self.tool_calls):
            raise ValueError('工具调用ID不可重复')
        return self


class SearchArgs(Contract):
    query: str = Field(min_length=1, max_length=500)
    max_results: StrictInt = Field(default=5, ge=1, le=5)


class Source(Contract):
    id: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=1000)
    verified: Literal[False] = False
    title: str | None = Field(default=None, max_length=300)
    url: str | None = Field(default=None, max_length=1500)
    document_id: str | None = None
    version: str | None = None
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=0)
    score: float | None = Field(default=None, ge=-1.001, le=1.001)
    score_kind: str | None = None
    content_kind: str | None = None
    rerank_score: float | None = Field(default=None, ge=0, le=1)
    reranker: str | None = None
    publisher: str | None = None
    language: str | None = None
    source_language: str | None = None
    jurisdiction: str | None = None
    source_family_id: str | None = None
    source_sha256: str | None = None
    raw_source_sha256: str | None = None
    encoding: str | None = None
    offset_basis: str | None = None
    provenance_status: str | None = None
    clinical_review_status: str | None = None
    editorial_status: str | None = None
    topic: str | None = None
    publication_date: str | None = None
    fetched_at: str | None = None
    license: str | None = None
    license_url: str | None = None
    attribution: str | None = None
    section: str | None = None
    source_spans: list[dict] = Field(default_factory=list, max_length=10)
    tier: str | None = None
    book: str | None = None
    edition: str | None = None
    chapter: str | None = None
    year: int | str | None = None


class ToolResult(Contract):
    success: bool
    documents: list[Source] = Field(default_factory=list, max_length=5)
    safe_error_code: str | None = None
    status: Literal['completed', 'no_match', 'failed'] = 'completed'


class FakeModel:
    def summarize(self, previous, messages):
        text = previous + '\n' + '\n'.join(f"[{m['seq']} {m['role']}] {m['content']}" for m in messages)
        return {'content': '【离线摘要】' + text[-2800:]}

    def reply(self, question):
        return '【离线模拟】已记录本轮问题；本阶段用于验证会话流程，尚未调用医疗模型。'

    def plan(self, state):
        if any(word in state['question'] for word in ('多任务', '多专家', '三个专家')):
            return {'tasks': [
                {'task_id': 'research', 'agent_id': 'research_agent', 'description': '检索样本登记合成资料', 'require_sources': True},
                {'task_id': 'consultation', 'agent_id': 'consultation_agent', 'description': '解释样本登记流程'},
                {'task_id': 'review', 'agent_id': 'diagnostic_agent', 'description': '检查前置任务字段要求', 'depends_on': ['research']},
            ]}
        return {'tasks': [{'agent_id': 'research_agent', 'description': state['question'][:1000]}]}

    def synthesize(self, state):
        usable = [r for r in state['task_results'] if r['status'] == 'completed']
        return {'answer': '【离线模拟汇总】\n' + '\n'.join(r['task_id'] + '：' + r['answer'] for r in usable),
                'task_ids': [r['task_id'] for r in usable],
                'source_ids': list(dict.fromkeys(s['id'] for r in usable for s in r['sources']))}

    def decide(self, state):
        if state['agent_id'] == 'research_agent' and not state['observations']:
            name = 'deep_research' if '联网' in state['question'] else 'search_knowledge'
            return {'tool_calls': [{'name': name, 'arguments': {'query': state['question'][:500]}}]}
        ids = [doc['id'] for observation in state['observations'] for doc in observation['result'].get('documents', [])]
        return {'answer': self.reply(state['question']), 'source_ids': ids}


class FakeMemory:
    def __init__(self, store=None):
        self.items = []
        self.store = store

    def search(self, user_id, query):
        rows = [{k: value[k] for k in ('id', 'content')} for value in self.items if value['user_id'] == user_id]
        if self.store:
            rows += self.list_scoped(user_id)
        return deepcopy(rows[:3])

    def list_scoped(self, user_id):
        from sqlalchemy import select
        from .models import FakeMemoryBlob
        with self.store.sessions() as db:
            return [{'id': row.id, 'content': row.content, 'metadata': json.loads(row.metadata_json)}
                    for row in db.scalars(select(FakeMemoryBlob).where(FakeMemoryBlob.user_id == user_id))]

    def add(self, user_id, content, metadata):
        from .models import FakeMemoryBlob
        with self.store.sessions.begin() as db:
            row = FakeMemoryBlob(user_id=user_id, content=content, metadata_json=json.dumps(metadata))
            db.add(row)
            db.flush()
            return {'status': 'completed', 'id': row.id}

    def update(self, user_id, mid, content, metadata):
        from .models import FakeMemoryBlob
        from .providers import ProviderError
        with self.store.sessions.begin() as db:
            row = db.get(FakeMemoryBlob, mid)
            if row is None or row.user_id != user_id:
                raise ProviderError('REMOTE_NOT_FOUND')
            row.content, row.metadata_json = content, json.dumps(metadata)

    def delete(self, user_id, mid):
        from .models import FakeMemoryBlob
        from .providers import ProviderError
        with self.store.sessions.begin() as db:
            row = db.get(FakeMemoryBlob, mid)
            if row is None or row.user_id != user_id:
                raise ProviderError('REMOTE_NOT_FOUND')
            db.delete(row)


class FakeTools:
    names = {'search_knowledge', 'deep_research', 'search_history', 'search_similar_cases'}

    def allowed(self, name, role):
        return name in self.names and (name != 'deep_research' or role == 'research_agent')

    def enabled_names(self, role):
        return [name for name in sorted(self.names) if self.allowed(name, role)]

    def execute(self, name, args, state):
        if name == 'search_history':
            documents = [{'id': m['id'], 'source': 'session_history', 'content': m['content'][:1000], 'verified': False}
                         for m in state['context']['history'] if args['query'] in m['content']]
        elif name == 'search_similar_cases':
            documents = [{'id': m['id'], 'source': 'fake_memory', 'content': m['content'][:1000], 'verified': False}
                         for m in state['context']['memories']]
        else:
            documents = [{'id': 'demo-sop-1', 'source': 'synthetic_demo', 'verified': False,
                          'content': '合成测试资料：样本登记需字段校验、可编辑草稿和确认；此条仅用于验证检索链路。'}]
        return {'success': True, 'documents': documents[:args['max_results']]}
