"""Synthetic registration: SQL is authoritative; models cannot confirm or write."""
import hashlib
import json
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from langsmith.run_helpers import tracing_context
from pydantic import Field, StrictBool, StrictInt, field_validator
from sqlalchemy import func, select, text

from .models import RegistrationAction, RegistrationDraft, RegistrationRecord, User, timestamp
from .schemas import Input
from .service import ApiError, owned_session

PROJECTS = ['DEMO-A', 'DEMO-B']
SAMPLE_TYPES = ['组织', '血液', '唾液']
STORAGES = ['DEMO-B 区域', 'DEMO-C 区域']


class Fields(Input):
    project: str = Field(default='', max_length=40)
    sample_type: str = Field(default='', max_length=20)
    quantity: StrictInt | None = None
    received_at: str = Field(default='', max_length=20)
    storage: str = Field(default='', max_length=40)
    note: str = Field(default='', max_length=300)


class Prepare(Input):
    text: str = Field(min_length=1, max_length=2000)
    request_id: UUID


class Revision(Input):
    revision: int = Field(ge=1, strict=True)
    request_id: UUID


class Edit(Revision):
    fields: Fields


class Confirm(Revision):
    confirmation_token: str = Field(min_length=32, max_length=128)
    explicit_confirm: StrictBool

    @field_validator('explicit_confirm')
    @classmethod
    def require_explicit_confirmation(cls, value):
        if not value:
            raise ValueError('需要明确确认')
        return value


def validate(fields):
    issues = {}
    if fields['project'] not in PROJECTS:
        issues['project'] = '请选择DEMO-A或DEMO-B演示项目'
    if fields['sample_type'] not in SAMPLE_TYPES:
        issues['sample_type'] = '请选择组织、血液或唾液'
    if fields['quantity'] is None or not 1 <= fields['quantity'] <= 20:
        issues['quantity'] = '数量须为1–20整数'
    try:
        if date.fromisoformat(fields['received_at']).isoformat() != fields['received_at']:
            raise ValueError()
    except ValueError:
        issues['received_at'] = '请填写有效的YYYY-MM-DD接收日期'
    if fields['storage'] not in STORAGES:
        issues['storage'] = '请选择DEMO-B或DEMO-C区域'
    return issues


def extract(raw):
    def unique(values, default=''):
        values = set(values)
        return next(iter(values)) if len(values) == 1 else default
    text_value = raw.upper()
    project_spans = re.findall(r'项目\s*[:：]?\s*([^，,；;\n]+)', text_value)
    projects = [p for span in project_spans for p in re.findall(r'DEMO-[A-Z]', span)]
    projects += re.findall(r'(DEMO-[A-Z])\s*(?:研究)?项目', text_value)
    quantities = re.findall(r'(-?\d+(?:\.\d+)?)\s*(?:份|个|管)', raw)
    quantity = unique(quantities, None)
    quantity = int(quantity) if quantity and re.fullmatch(r'-?\d+', quantity) else None
    dates = re.findall(r'\d{4}-\d{2}-\d{2}', raw)
    if not dates and '今天' in raw:
        dates = [datetime.now(timezone(timedelta(hours=8))).date().isoformat()]
    return Fields(project=unique(projects), sample_type=unique(t for t in SAMPLE_TYPES if t in raw),
                  quantity=quantity, received_at=unique(dates),
                  storage=unique(s + ' 区域' for s in re.findall(r'(DEMO-[A-Z])\s*(?:区域|区)', text_value))).model_dump()


class PrepareState(TypedDict):
    text: str
    fields: dict
    issues: dict


class RegistrationService:
    def __init__(self, store):
        self.store = store
        graph = StateGraph(PrepareState)
        graph.add_node('extract_fields', lambda s: {'fields': extract(s['text'])})
        graph.add_node('validate_fields', lambda s: {'issues': validate(s['fields'])})
        graph.add_edge(START, 'extract_fields')
        graph.add_edge('extract_fields', 'validate_fields')
        graph.add_edge('validate_fields', END)
        self.graph = graph.compile()

    @staticmethod
    def output(db, row):
        record = db.scalar(select(RegistrationRecord).where(RegistrationRecord.draft_id == row.id))
        return {'draft': {'id': row.id, 'session_id': row.session_id, 'revision': row.revision,
                         'status': row.status, 'fields': json.loads(row.fields_json), 'issues': json.loads(row.issues_json),
                         'workflow': 'registration_graph_v1', 'created_at': row.created_at, 'updated_at': row.updated_at},
                'record': RegistrationService.record_output(record) if record else None, 'replayed': False}

    @staticmethod
    def record_output(row):
        return {'id': row.id, 'draft_id': row.draft_id, 'revision': row.revision, 'fields': json.loads(row.fields_json),
                'sample_ids': json.loads(row.sample_ids_json), 'created_at': row.created_at, 'business_mode': 'synthetic_sql'}

    @staticmethod
    def owned(db, user_id, draft_id):
        row = db.scalar(select(RegistrationDraft).where(RegistrationDraft.id == draft_id, RegistrationDraft.user_id == user_id))
        if row is None:
            raise ApiError(404, 'DRAFT_NOT_FOUND', '草稿不存在或不可访问')
        owned_session(db, row.session_id, user_id)
        return row

    def execute(self, user_id, action, target, body):
        payload = body.model_dump(mode='json')
        fingerprint = hashlib.sha256(json.dumps([action, target, payload], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        # Serialize all business mutations before reading state. The write, audit
        # receipt and terminal draft change commit together; no cloud call here.
        with self.store.sessions() as db:
            db.execute(text('BEGIN IMMEDIATE'))
            user = db.get(User, user_id)
            if user is None or not user.active:
                raise ApiError(401, 'INVALID_TOKEN', '用户已停用')
            owned_session(db, target, user_id) if action == 'prepare' else self.owned(db, user_id, target)
            receipt = db.scalar(select(RegistrationAction).where(RegistrationAction.user_id == user_id,
                                                               RegistrationAction.request_id == str(body.request_id)))
            if receipt:
                if receipt.fingerprint != fingerprint:
                    raise ApiError(409, 'IDEMPOTENCY_CONFLICT', '请求标识已用于另一项登记操作')
                return json.loads(receipt.response_json) | {'replayed': True}
            if action == 'prepare':
                count = db.scalar(select(func.count()).select_from(RegistrationDraft).where(RegistrationDraft.user_id == user_id))
                if count >= 200:
                    raise ApiError(409, 'DEMO_DRAFT_LIMIT', '当前账号已达200份演示草稿上限')
                with tracing_context(enabled=False):
                    state = self.graph.invoke({'text': body.text})
                row = RegistrationDraft(user_id=user_id, session_id=target, fields_json=json.dumps(state['fields'], ensure_ascii=False),
                                        issues_json=json.dumps(state['issues'], ensure_ascii=False),
                                        status='incomplete' if state['issues'] else 'ready')
                db.add(row)
                db.flush()
            else:
                row = self.owned(db, user_id, target)
                if body.revision != row.revision:
                    raise ApiError(409, 'STALE_DRAFT', '草稿版本已变化，请刷新并重新核对')
                if action == 'confirm' and row.status == 'completed':
                    if not row.confirmation_hash or not secrets.compare_digest(row.confirmation_hash, hashlib.sha256(body.confirmation_token.encode()).hexdigest()):
                        raise ApiError(409, 'CONFIRMATION_INVALID', '确认凭据已失效')
                    result = self.output(db, row) | {'replayed': True}
                    self.save_receipt(db, user_id, row, body, fingerprint, action, result)
                    db.commit()
                    return result
                if row.status in ('completed', 'cancelled'):
                    raise ApiError(409, 'DRAFT_CLOSED', '已完成或取消的草稿不能再次修改')
                if action == 'edit':
                    fields = body.fields.model_dump()
                    issues = validate(fields)
                    row.fields_json, row.issues_json = json.dumps(fields, ensure_ascii=False), json.dumps(issues, ensure_ascii=False)
                    row.revision += 1
                    row.status, row.confirmation_hash = ('incomplete' if issues else 'ready'), None
                elif action == 'cancel':
                    row.status, row.confirmation_hash = 'cancelled', None
                elif action in ('review', 'confirm'):
                    if validate(json.loads(row.fields_json)):
                        raise ApiError(422, 'DRAFT_INCOMPLETE', '请先补全并校验草稿字段')
                    if action == 'review':
                        token = secrets.token_urlsafe(36)
                        row.confirmation_hash = hashlib.sha256(token.encode()).hexdigest()
                        row.status = 'awaiting_confirmation'
                    else:
                        digest = hashlib.sha256(body.confirmation_token.encode()).hexdigest()
                        if row.status != 'awaiting_confirmation' or not row.confirmation_hash or not secrets.compare_digest(row.confirmation_hash, digest):
                            raise ApiError(409, 'CONFIRMATION_INVALID', '请先核对当前版本，再明确确认')
                        count = db.scalar(select(func.count()).select_from(RegistrationRecord).where(RegistrationRecord.user_id == user_id))
                        if count >= 100:
                            raise ApiError(409, 'DEMO_RECORD_LIMIT', '当前账号已达100批演示记录上限')
                        fields = json.loads(row.fields_json)
                        db.add(RegistrationRecord(draft_id=row.id, user_id=user_id, revision=row.revision, fields_json=row.fields_json,
                            sample_ids_json=json.dumps(['SYN-' + row.id + '-' + str(i+1).zfill(2) for i in range(fields['quantity'])])))
                        row.status = 'completed'
                row.updated_at = timestamp()
                db.flush()
            result = self.output(db, row)
            if action == 'review':
                result['confirmation_token'] = token
            self.save_receipt(db, user_id, row, body, fingerprint, action, result)
            db.commit()
            return result

    @staticmethod
    def save_receipt(db, user_id, row, body, fingerprint, action, result):
        db.add(RegistrationAction(user_id=user_id, draft_id=row.id, request_id=str(body.request_id),
                                  fingerprint=fingerprint, action=action, response_json=json.dumps(result, ensure_ascii=False)))

    def get(self, user_id, draft_id):
        with self.store.sessions() as db:
            return self.output(db, self.owned(db, user_id, draft_id))

    def drafts(self, user_id, session_id):
        with self.store.sessions() as db:
            owned_session(db, session_id, user_id)
            rows = db.scalars(select(RegistrationDraft).where(RegistrationDraft.user_id == user_id,
                RegistrationDraft.session_id == session_id).order_by(RegistrationDraft.created_at.desc()).limit(200))
            return {'items': [self.output(db, row)['draft'] for row in rows]}

    def records(self, user_id):
        with self.store.sessions() as db:
            return {'items': [self.record_output(row) for row in db.scalars(select(RegistrationRecord).where(
                RegistrationRecord.user_id == user_id).order_by(RegistrationRecord.created_at.desc()).limit(100))]}

    def audit(self, user_id, draft_id):
        with self.store.sessions() as db:
            self.owned(db, user_id, draft_id)
            return {'items': [{'action': row.action, 'revision': json.loads(row.response_json)['draft']['revision'],
                               'request_id': row.request_id, 'created_at': row.created_at} for row in db.scalars(
                select(RegistrationAction).where(RegistrationAction.user_id == user_id, RegistrationAction.draft_id == draft_id)
                .order_by(RegistrationAction.created_at, RegistrationAction.id))]}
