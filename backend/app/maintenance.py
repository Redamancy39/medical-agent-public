"""Durable, user-scoped maintenance. SQL answer + jobs commit together.

Only explicit stable preferences/background enter memory; assistant output never
does. Unknown add outcomes reconcile first and never blindly repeat the write.
"""
import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from uuid import uuid4

from sqlalchemy import select
from langsmith.run_helpers import tracing_context

from .models import Conversation, MemoryFact, MemoryJob, Message, Run, SessionSummary, timestamp
from .providers import ProviderError, call_scope
from .service import ApiError


def preferences(text):
    if not re.search(r'我(?:喜欢|不喜欢|偏好|更喜欢|长期|是|确诊|患有|有)|以后|请记住|纠正|病例讨论|假设案例', text):
        return {}
    values = {}
    for key, pattern in [('answer_language', r'(中文|英文)'), ('answer_style', r'(简洁|详细)')]:
        matches = list(re.finditer(pattern, text))
        if matches:
            match = matches[-1]
            prefix = text[max(0, match.start()-12):match.start()]
            negative = bool(re.search(r'(?:不(?:要|再|喜欢|希望|用)?|别|避免)[^，。；]{0,6}$', prefix))
            values[key] = '用户偏好' + ('回答语言：' if key == 'answer_language' else '回答风格：') + ('避免' if negative else '') + match.group()

    is_hypo = bool(re.search(r'假设|假如|模拟|病例讨论|虚拟患者', text))
    is_third_party = bool(re.search(r'我(?:父亲|母亲|爸|妈|爷爷|奶奶|外公|外婆|爱人|老公|老婆|朋友|同事|亲戚|家属|孩子|儿子|女儿)', text))

    if not is_hypo and not is_third_party:
        match = re.search(r'我是([^。；\n]{0,60}(?:研究生|科研人员|医生|护士|学生|住院医|临床医生|进修医))', text)
        if match:
            values['occupation'] = '用户明确背景：' + match.group(1)
        match = re.search(r'我长期(?:目标是|希望)([^。；\n]{1,120})', text)
        if match:
            values['research_goal'] = '用户持续目标：' + match.group(1)
        match = re.search(r'我(?:患有|确诊|有)([^。；\n]{1,60}(?:高血压|冠心病|心衰|心力衰竭|房颤|糖尿病|高脂血症|痛风))', text)
        if match:
            values['user_health_profile'] = '用户本人健康背景：' + match.group(1)
    elif is_third_party:
        match = re.search(r'(我(?:父亲|母亲|爸|妈|爷爷|奶奶|外公|外婆|爱人|老公|老婆|朋友|同事|家属|孩子)[^。；\n]{1,80})', text)
        if match and re.search(r'请记住|病史|有|患有|过敏', text):
            values['third_party_info'] = '他人/家属信息：' + match.group(1)
    elif is_hypo:
        match = re.search(r'(?:假设|假如|模拟|病例讨论)[^。；\n]{0,20}(一名?[^。；\n]{1,80})', text)
        if match and re.search(r'请记住|设定', text):
            values['case_hypothetical'] = '假设案例设定：' + match.group(1)
    return values


def eligible_messages(db, session_id, exclude_run=None):
    statement = select(Message).join(Run, Run.id == Message.run_id).where(
        Message.session_id == session_id, Run.run_status.in_(['finished', 'failed', 'cancelled', 'timed_out']))
    if exclude_run:
        statement = statement.where(Run.id != exclude_run)
    return list(db.scalars(statement.order_by(Message.seq)))


def obsolete_message_ids(db, user_id):
    result = set()
    for fact in db.scalars(select(MemoryFact).where(MemoryFact.user_id == user_id)):
        ids = json.loads(fact.source_message_ids_json)
        result.update(mid for mid in ids if fact.status == 'deleted' or mid != fact.current_source_message_id)
    return result


def redact_messages(rows, obsolete):
    obsolete_runs = {row.run_id for row in rows if row.id in obsolete}
    return [{'id': row.id, 'seq': row.seq, 'role': row.role,
             'content': '[该轮的长期偏好已由用户纠正或撤回，不应继续采用。]' if row.id in obsolete or row.role == 'assistant' and row.run_id in obsolete_runs else row.content}
            for row in rows]


class Maintenance:
    def __init__(self, store, settings, model, memory):
        self.store, self.settings, self.model, self.memory = store, settings, model, memory
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='memory-maintenance')
        self.lock, self.future = Lock(), None

    def close(self):
        self.pool.shutdown(wait=True, cancel_futures=False)

    def _job(self, db, run, action, *, fact=None, covered=0):
        key = hashlib.sha256(json.dumps([run.id, action, fact.id if fact else None,
                                        fact.version if fact else covered]).encode()).hexdigest()
        if db.scalar(select(MemoryJob.id).where(MemoryJob.operation_key == key)):
            return
        db.add(MemoryJob(operation_key=key, user_id=run.user_id, session_id=run.session_id, run_id=run.id,
                         fact_id=fact.id if fact else None, action=action, content=fact.content if fact else '',
                         version=fact.version if fact else 0, covered_until_seq=covered,
                         remote_id=fact.remote_id if fact else None))

    def _invalidate_summaries(self, db, user_id):
        for summary in db.scalars(select(SessionSummary).where(SessionSummary.user_id == user_id)):
            summary.content, summary.covered_until_seq, summary.input_hash = '', 0, ''
            summary.status, summary.version = 'invalidated', summary.version + 1

    def _change(self, db, run, fact, content, source_id=None):
        if content is not None and fact.status == 'active' and fact.content == content:
            return False
        fact.version += 1
        fact.status = 'deleted' if content is None else 'active'
        if content is not None:
            fact.content = content
        ids = json.loads(fact.source_message_ids_json)
        if source_id and source_id not in ids:
            ids.append(source_id)
        fact.source_message_ids_json, fact.updated_at = json.dumps(ids), timestamp()
        fact.current_source_message_id = source_id
        # Cancel only writes that have definitely not started. Processing/unknown
        # old writes must finish reconciliation and clean up their own remote IDs.
        for job in db.scalars(select(MemoryJob).where(MemoryJob.fact_id == fact.id, MemoryJob.status.in_(['pending', 'failed']))):
            job.status = 'superseded'
        self._invalidate_summaries(db, run.user_id)
        self._job(db, run, 'delete' if content is None else ('update' if fact.remote_id else 'add'), fact=fact)
        return True

    def enqueue(self, db, run, question):
        if not self.settings.maintenance_enabled or run.result_status not in ('completed', 'partial'):
            return 'skipped'
        db.flush()
        user_message = db.scalar(select(Message).where(Message.run_id == run.id, Message.role == 'user').order_by(Message.seq.desc()))
        facts = {f.key: f for f in db.scalars(select(MemoryFact).where(MemoryFact.user_id == run.user_id))}
        if re.search(r'忘记.*(?:偏好|记忆)|删除.*(?:偏好|记忆)', question):
            for fact in facts.values():
                if fact.status == 'active':
                    self._change(db, run, fact, None)
        else:
            for key, content in preferences(question).items():
                entity_type = 'self'
                if key.startswith('case_') or '假设案例' in content:
                    entity_type = 'case_hypothetical'
                elif key.startswith('third_party_') or '他人' in content or '家属' in content:
                    entity_type = 'third_party'
                if key in facts:
                    facts[key].entity_type = entity_type
                    self._change(db, run, facts[key], content, user_message.id)
                else:
                    fact = MemoryFact(user_id=run.user_id, key=key, content=content,
                                      entity_type=entity_type,
                                      source_message_ids_json=json.dumps([user_message.id]), current_source_message_id=user_message.id)
                    db.add(fact)
                    db.flush()
                    self._job(db, run, 'add', fact=fact)
        rows = eligible_messages(db, run.session_id)
        users = [row.seq for row in rows if row.role == 'user']
        if len(users) > self.settings.recent_turns:
            boundary = users[-self.settings.recent_turns]
            covered = max(row.seq for row in rows if row.seq < boundary)
            summary = db.get(SessionSummary, run.session_id)
            if summary is None or summary.covered_until_seq < covered:
                self._job(db, run, 'summary', covered=covered)
        db.flush()
        return 'pending' if db.scalar(select(MemoryJob.id).where(MemoryJob.run_id == run.id, MemoryJob.status == 'pending')) else 'skipped'

    def kick(self):
        if not self.settings.maintenance_enabled:
            return
        with self.lock:
            self.future = self.pool.submit(self.drain)

    def _claim(self, job_id, retry):
        with self.store.sessions() as db:
            db.connection().exec_driver_sql('BEGIN IMMEDIATE')
            job = db.get(MemoryJob, job_id)
            if job.status == 'processing' and job.lease_until <= time.time():
                job.status = 'uncertain' if job.action == 'add' else 'failed'
            if job.lease_until > time.time() or job.status not in (['pending', 'uncertain', 'awaiting_remote', 'failed'] if retry else ['pending', 'uncertain', 'awaiting_remote']):
                db.commit()
                return None
            if job.attempts >= 5:
                job.safe_error_code = 'MAINTENANCE_BUDGET_EXCEEDED'
                db.commit()
                return None
            old_status = job.status
            job.status, job.lease_token = 'processing', str(uuid4())
            job.lease_until = time.time() + self.settings.provider_timeout_seconds * 4 + 5
            job.attempts += 1
            token = job.lease_token
            db.commit()
            return job_id, token, old_status

    def _finish(self, job_id, token, status, *, code=None, remote_id=None, event_id=None):
        with self.store.sessions() as db:
            db.connection().exec_driver_sql('BEGIN IMMEDIATE')
            job = db.get(MemoryJob, job_id)
            if job.lease_token != token:
                return
            job.status, job.safe_error_code, job.lease_until = status, code, 0
            job.lease_token, job.updated_at = None, timestamp()
            if remote_id:
                job.remote_id = remote_id
            if event_id:
                job.event_id = event_id
            if status == 'done' and job.fact_id:
                fact = db.get(MemoryFact, job.fact_id)
                if fact.version == job.version:
                    fact.remote_id = None if job.action == 'delete' else job.remote_id
                    fact.synced_version = job.version
            run = db.get(Run, job.run_id)
            metadata = json.loads(run.details_json)
            relevant = list(db.scalars(select(MemoryJob).where(MemoryJob.run_id == job.run_id,
                MemoryJob.action == 'summary' if job.action == 'summary' else MemoryJob.action != 'summary')))
            states = {row.status for row in relevant}
            aggregate = next((value for value in ('processing', 'pending', 'uncertain', 'awaiting_remote', 'failed') if value in states), 'done')
            metadata['summary_write_status' if job.action == 'summary' else 'memory_write_status'] = aggregate
            if code:
                metadata['maintenance_error_code'] = code
            run.details_json = json.dumps(metadata)
            db.commit()

    def _summary(self, job, token):
        with self.store.sessions() as db:
            summary = db.get(SessionSummary, job.session_id)
            version, covered, previous = (summary.version, summary.covered_until_seq, summary.content) if summary else (0, 0, '')
            if covered >= job.covered_until_seq:
                self._finish(job.id, token, 'done')
                return
            rows = [row for row in eligible_messages(db, job.session_id) if covered < row.seq <= job.covered_until_seq]
            messages = redact_messages(rows, obsolete_message_ids(db, job.user_id))
        input_hash = hashlib.sha256(json.dumps([previous, messages], ensure_ascii=False).encode()).hexdigest()
        # Bound each compression input; leave the job failed with original history intact.
        if sum(len(m['content']) for m in messages) + len(previous) > self.settings.max_context_chars:
            raise ProviderError('SUMMARY_INPUT_TOO_LARGE')
        output = self.model.summarize(previous, messages)
        if not isinstance(output, dict) or set(output) != {'content'} or not isinstance(output['content'], str) or not 1 <= len(output['content']) <= self.settings.summary_max_chars:
            raise ProviderError('SUMMARY_INVALID')
        with self.store.sessions() as db:
            db.connection().exec_driver_sql('BEGIN IMMEDIATE')
            latest_job = db.get(MemoryJob, job.id)
            latest = db.get(SessionSummary, job.session_id)
            if latest_job.lease_token != token or (latest.version if latest else 0) != version:
                raise ProviderError('SUMMARY_VERSION_CONFLICT')
            actual = redact_messages([r for r in eligible_messages(db, job.session_id) if covered < r.seq <= job.covered_until_seq], obsolete_message_ids(db, job.user_id))
            if hashlib.sha256(json.dumps([previous, actual], ensure_ascii=False).encode()).hexdigest() != input_hash:
                raise ProviderError('SUMMARY_INPUT_CHANGED')
            if latest is None:
                latest = SessionSummary(session_id=job.session_id, user_id=job.user_id)
                db.add(latest)
            latest.content, latest.covered_until_seq, latest.version = output['content'], job.covered_until_seq, version + 1
            latest.input_hash, latest.status, latest.updated_at = input_hash, 'ready', timestamp()
            db.commit()
        self._finish(job.id, token, 'done')

    def _memory(self, job, token, old_status):
        with self.store.sessions() as db:
            fact = db.get(MemoryFact, job.fact_id)
            stale = fact.version != job.version or (fact.status == 'deleted' and job.action != 'delete')
            entity_type = fact.entity_type if fact else 'self'
        metadata = {'operation_key': job.operation_key, 'fact_id': job.fact_id, 'version': job.version, 'entity_type': entity_type}
        mid = job.remote_id
        if old_status == 'awaiting_remote' and job.event_id:
            event = self.memory.event(job.event_id)
            if event.get('status') == 'PENDING':
                self._finish(job.id, token, 'awaiting_remote')
                return
            if event.get('status') != 'SUCCEEDED':
                raise ProviderError('MEMORY_EVENT_FAILED')
        if old_status in ('uncertain', 'awaiting_remote'):
            rows = self.memory.list_scoped(job.user_id)
            matches = [row for row in rows if row.get('metadata', {}).get('operation_key') == job.operation_key]
            if len(matches) != 1:
                self._finish(job.id, token, 'uncertain', code='MEMORY_WRITE_UNCONFIRMED')
                return
            mid = matches[0]['id']
        if stale:
            if mid and job.action == 'add':
                self.memory.delete(job.user_id, mid)
            self._finish(job.id, token, 'superseded', remote_id=mid)
            return
        if job.action == 'delete':
            if mid:
                try:
                    self.memory.delete(job.user_id, mid)
                except ProviderError as error:
                    if error.code != 'REMOTE_NOT_FOUND':
                        raise
            self._finish(job.id, token, 'done')
        elif job.action == 'update':
            self.memory.update(job.user_id, mid, job.content, metadata)
            self._finish(job.id, token, 'done', remote_id=mid)
        else:
            if mid is None:
                added = self.memory.add(job.user_id, job.content, metadata)
                if added['status'] == 'pending':
                    self._finish(job.id, token, 'awaiting_remote', event_id=added['event_id'])
                    return
                mid = added['id']
            # Confirm content in scoped storage before claiming completion/searchability.
            rows = self.memory.list_scoped(job.user_id)
            if not any(row['id'] == mid and row['content'] == job.content for row in rows):
                self._finish(job.id, token, 'uncertain', remote_id=mid, code='MEMORY_WRITE_UNCONFIRMED')
                return
            with self.store.sessions() as db:
                latest = db.get(MemoryFact, job.fact_id)
                late_stale = latest.version != job.version or latest.status != 'active'
            if late_stale:
                self.memory.delete(job.user_id, mid)
                self._finish(job.id, token, 'superseded', remote_id=mid)
                return
            self._finish(job.id, token, 'done', remote_id=mid)

    def drain(self, user_id=None, retry=False):
        with self.store.sessions() as db:
            statement = select(MemoryJob.id).where(MemoryJob.status.in_(['pending', 'uncertain', 'awaiting_remote', 'processing'] + (['failed'] if retry else [])))
            if user_id:
                statement = statement.where(MemoryJob.user_id == user_id)
            ids = list(db.scalars(statement.order_by(MemoryJob.created_at, MemoryJob.id).limit(self.settings.maintenance_batch_size)))
        for job_id in ids:
            claim = self._claim(job_id, retry)
            if not claim:
                continue
            _, token, old_status = claim
            with self.store.sessions() as db:
                job = db.get(MemoryJob, job_id)
            try:
                with call_scope(job.run_id), tracing_context(enabled=False):
                    self._summary(job, token) if job.action == 'summary' else self._memory(job, token, old_status)
            except Exception as error:
                code = error.code if isinstance(error, ProviderError) else 'MAINTENANCE_FAILED'
                unknown = job.action == 'add' and (old_status in ('uncertain', 'awaiting_remote') or code in
                    ('REMOTE_TIMEOUT', 'NETWORK_UNAVAILABLE', 'RESPONSE_INVALID', 'MEMORY_ADD_UNCONFIRMED', 'MAINTENANCE_FAILED'))
                self._finish(job_id, token, 'uncertain' if unknown else 'failed', code=code)

    def filter_memories(self, user_id, rows):
        with self.store.sessions() as db:
            facts = list(db.scalars(select(MemoryFact).where(MemoryFact.user_id == user_id)))
            jobs = list(db.scalars(select(MemoryJob).where(MemoryJob.user_id == user_id, MemoryJob.remote_id.is_not(None))))
        tracked = {f.remote_id: f for f in facts if f.remote_id}
        fact_by_id = {f.id: f for f in facts}
        historical_ids = {job.remote_id for job in jobs if job.fact_id in fact_by_id and (
            fact_by_id[job.fact_id].status == 'deleted' or job.version != fact_by_id[job.fact_id].version)}
        result = []
        for row in rows:
            fact = tracked.get(row['id'])
            if not fact and row['id'] in historical_ids:
                continue
            if fact and (fact.status != 'active' or fact.version != fact.synced_version or row['content'] != fact.content):
                continue
            # Unmanaged remote memory is background only; a deleted key cannot be
            # resurrected by a late add that has not yet been reconciled.
            fact_id = row.get('metadata', {}).get('fact_id')
            if fact_id and not any(f.id == fact_id and f.status == 'active' and f.version == row.get('metadata', {}).get('version') for f in facts):
                continue
            entity_type = fact.entity_type if fact else row.get('metadata', {}).get('entity_type', 'self')
            result.append({'id': row['id'], 'content': row['content'], 'entity_type': entity_type})
        return list({row['id']: row for row in result}.values())[:3]

    def edit(self, user_id, fact_id, operation, content=None):
        with self.store.sessions() as db:
            db.connection().exec_driver_sql('BEGIN IMMEDIATE')
            fact = db.scalar(select(MemoryFact).where(MemoryFact.id == fact_id, MemoryFact.user_id == user_id))
            if fact is None:
                raise ApiError(404, 'MEMORY_NOT_FOUND', '记忆不存在或不可访问')
            patterns = {'answer_language': r'用户偏好回答语言：(避免)?(中文|英文)',
                        'answer_style': r'用户偏好回答风格：(避免)?(简洁|详细)'}
            if operation == 'update' and fact.key in patterns and not re.fullmatch(patterns[fact.key], content):
                raise ApiError(422, 'MEMORY_VALUE_INVALID', '请保留记忆字段前缀，并填写该字段支持的偏好值')
            run = db.scalar(select(Run).where(Run.user_id == user_id, Run.finished_at.is_not(None)).order_by(Run.created_at.desc()))
            if run is None:
                raise ApiError(409, 'MEMORY_SOURCE_MISSING', '缺少记忆维护来源')
            changed = self._change(db, run, fact, None if operation == 'delete' else content)
            db.commit()
        self.kick()
        return {'status': 'pending' if changed else 'unchanged'}
