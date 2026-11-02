"""Persisted query DAG and bounded workers; provider selection is explicit."""
import hashlib
import json
import re
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from copy import deepcopy
from contextvars import copy_context
from threading import Lock
from typing import TypedDict
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.errors import GraphInterrupt
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from langsmith.run_helpers import tracing_context
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert

from .agent import Decision, FakeMemory, FakeTools, Plan, SearchArgs, ToolResult, source_identity, source_documents
from .models import Conversation, ExecutionEvent, MemoryFact, Message, Run, SessionLearningState, SessionSummary, timestamp
from .multitask import MultiTaskMixin
from .maintenance import Maintenance, obsolete_message_ids, redact_messages
from .providers import ProviderError, call_scope
from .contracts import ContractViolation, contract_diagnostic
from .medical_safety import urgent_policy_trigger, URGENT_MESSAGE, fabricated_evidence_request, REFUSAL_MESSAGE
from .medical_quality import is_policy_or_refusal
from .medical_reviewer import MedicalReviewerMixin
from .service import ApiError, owned_session, run_output


class State(TypedDict):
    run_id: str
    session_id: str
    user_id: str
    question: str
    context: dict
    messages: list[dict]
    observations: list[dict]
    pending_calls: list[dict]
    source_ids: list[str]
    sources: list[dict]
    agent_id: str
    plan: dict
    plan_status: str
    model_calls: int
    tool_calls: int
    worker_iterations: int
    revision: int
    outcome: str | None
    answer: str | None
    error_code: str | None
    task_results: list[dict]
    evidence_status: str
    evidence_issues: list[dict]
    refinement_count: int
    task_description: str | None


class StopFlow(Exception):
    def __init__(self, code, outcome='failed'):
        self.code, self.outcome = code, outcome


def details(run):
    return json.loads(run.details_json)


class SingleAgentFlow(MedicalReviewerMixin, MultiTaskMixin):
    version = 3

    def __init__(self, store, settings, model, memory=None, tools=None):
        self.store, self.settings, self.model = store, settings, model
        self.memory, self.tools = memory or FakeMemory(store), tools or FakeTools()
        self.maintenance = Maintenance(store, settings, model, self.memory)
        self.controls, self.locks = {}, {}
        self.lock_guard = Lock()
        self.pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='fake-provider')
        self.connection = sqlite3.connect(settings.database_path.with_name('checkpoints.db'), check_same_thread=False, timeout=5)
        self.connection.execute('PRAGMA journal_mode=WAL')
        self.saver = SqliteSaver(self.connection)
        self.worker_graph = self.build_worker_graph().compile(checkpointer=False)
        self.graph = self.build_graph().compile(checkpointer=self.saver)

    def close(self):
        self.maintenance.close()
        self.pool.shutdown(wait=False, cancel_futures=True)
        self.connection.close()
        if hasattr(self.tools, 'close'):
            self.tools.close()

    def config(self, run_id):
        return {'configurable': {'thread_id': 'run:' + run_id}, 'recursion_limit': 50}

    def snapshot(self, run_id):
        with tracing_context(enabled=False):
            return self.graph.get_state(self.config(run_id))

    def session_lock(self, session_id):
        with self.lock_guard:
            return self.locks.setdefault(session_id, Lock())

    def owned_run(self, db, run_id, user_id):
        run = db.scalar(select(Run).where(Run.id == run_id, Run.user_id == user_id))
        if run is None:
            raise ApiError(404, 'RUN_NOT_FOUND', '运行记录不存在或不可访问')
        return run

    def _claim(self, db, run):
        metadata = details(run)
        if metadata.get('lease_until', 0) > time.time():
            raise ApiError(409, 'RUN_BUSY', '该运行正在执行，请稍后查询状态')
        token = str(uuid4())
        metadata.update(lease_token=token, lease_until=time.time() + self.settings.run_timeout_seconds + 5)
        run.details_json = json.dumps(metadata)
        return token

    def _guard(self, state):
        token, deadline = self.controls[state['run_id']]
        with self.store.sessions() as db:
            run = db.get(Run, state['run_id'])
            if run.cancel_requested:
                raise StopFlow('CANCELLED', 'cancelled')
            if details(run).get('lease_token') != token:
                raise StopFlow('LEASE_LOST')
        if time.monotonic() >= deadline:
            raise StopFlow('RUN_TIMEOUT', 'timed_out')

    def _call(self, state, function, *args):
        with call_scope(state['run_id']):
            future = self.pool.submit(copy_context().run, function, *args)
        deadline = time.monotonic() + self.settings.step_timeout_seconds
        try:
            while True:
                self._guard(state)
                if time.monotonic() >= deadline:
                    raise StopFlow('STEP_TIMEOUT', 'timed_out')
                try:
                    result = future.result(timeout=0.05)
                    self._guard(state)
                    return result
                except TimeoutError:
                    continue
        except BaseException:
            future.cancel()
            raise

    def _consume(self, state, key, maximum, code):
        # Persist attempts before provider calls; checkpoint replay also consumes budget.
        with self.store.sessions() as db:
            db.connection().exec_driver_sql('BEGIN IMMEDIATE')
            run = db.get(Run, state['run_id'])
            metadata = details(run)
            if metadata.get('lease_token') != self.controls[run.id][0]:
                raise StopFlow('LEASE_LOST')
            task_id = state.get('task_id')
            count = metadata.get(key, 0) if task_id else max(metadata.get(key, 0), state[key])
            if count >= maximum:
                raise StopFlow(code)
            if task_id:
                attempts = metadata.setdefault('task_attempts', {}).setdefault(task_id, {})
                local_count = max(state[key], attempts.get(key, 0))
                local_max = self.settings.max_worker_model_calls if key == 'model_calls' else self.settings.max_worker_tool_calls
                if local_count >= local_max:
                    raise StopFlow('WORKER_' + code)
                state[key] = local_count + 1
                attempts[key] = state[key]
                attempts['worker_iterations'] = state['worker_iterations']
            else:
                state[key] = count + 1
            metadata[key] = count + 1
            run.details_json = json.dumps(metadata)
            db.commit()

    def _contract_failure(self, state, diagnostic):
        with self.store.sessions() as db:
            db.connection().exec_driver_sql('BEGIN IMMEDIATE')
            run = db.get(Run, state['run_id'])
            metadata = details(run)
            if metadata.get('lease_token') != self.controls[run.id][0]: raise StopFlow('LEASE_LOST')
            metadata.setdefault('contract_diagnostics', []).append(diagnostic)
            metadata['contract_diagnostics'] = metadata['contract_diagnostics'][-10:]
            run.details_json = json.dumps(metadata)
            db.commit()

    def _evidence_diagnostic(self, state, diagnostic):
        with self.store.sessions() as db:
            db.connection().exec_driver_sql('BEGIN IMMEDIATE')
            run = db.get(Run, state['run_id'])
            metadata = details(run)
            if metadata.get('lease_token') != self.controls[run.id][0]: raise StopFlow('LEASE_LOST')
            metadata.setdefault('evidence_diagnostics', []).append({'task_id': state.get('task_id'), **diagnostic})
            metadata['evidence_diagnostics'] = metadata['evidence_diagnostics'][-40:]
            run.details_json = json.dumps(metadata)
            db.commit()

    def _claim_contract_repair(self, state, stage):
        with self.store.sessions() as db:
            db.connection().exec_driver_sql('BEGIN IMMEDIATE')
            run = db.get(Run, state['run_id'])
            metadata = details(run)
            if metadata.get('lease_token') != self.controls[run.id][0]: raise StopFlow('LEASE_LOST')
            counts = metadata.setdefault('contract_repair_counts',
                {'worker': metadata['schema_repair_count']} if metadata.get('schema_repair_count') else {})
            if counts.get(stage, 0) >= self.settings.schema_repair_limit: return False
            counts[stage] = counts.get(stage, 0) + 1
            metadata['schema_repair_count'] = metadata.get('schema_repair_count', 0) + 1
            run.details_json = json.dumps(metadata)
            db.commit()
        return True

    def _contract_call(self, state, stage, function, validate, invalid_code):
        payload = deepcopy(state)
        while True:
            self._guard(state)
            self._consume(state, 'model_calls', self.settings.max_model_calls, 'MODEL_BUDGET_EXCEEDED')
            try:
                return validate(self._call(state, function, payload))
            except StopFlow:
                raise
            except (ValidationError, ContractViolation, ProviderError) as error:
                diagnostic = contract_diagnostic(stage, error, invalid_code)
                self._contract_failure(state, diagnostic)
                repairable = not isinstance(error, ProviderError) or error.code in (
                    'MODEL_JSON_INVALID', 'MODEL_STRUCTURED_CALL_INVALID')
                if repairable and self._claim_contract_repair(state, stage):
                    payload['contract_repair'] = diagnostic
                    continue
                raise StopFlow(error.code if isinstance(error, ProviderError) else invalid_code) from None

    def _event(self, state, stage, status='completed'):
        key = f"{state['run_id']}:{state['revision']}:{state.get('task_id', 'lead')}:{stage}:{state['model_calls']}:{state['tool_calls']}:{state['worker_iterations']}"
        with self.store.sessions() as db:
            db.connection().exec_driver_sql('BEGIN IMMEDIATE')
            run = db.get(Run, state['run_id'])
            metadata = details(run)
            if metadata.get('lease_token') != self.controls[run.id][0]:
                raise StopFlow('LEASE_LOST')
            event_stage = stage + ':' + state['task_id'] if state.get('task_id') else stage
            db.execute(insert(ExecutionEvent).values(run_id=state['run_id'], stage=event_stage, status=status, event_key=key).on_conflict_do_nothing(index_elements=['event_key']))
            metadata['stage'] = stage
            if not state.get('task_id'):
                metadata.update(plan_status=state['plan_status'], agent_id=state['agent_id'], worker_iterations=state['worker_iterations'],
                                evidence_status=state['evidence_status'], evidence_issues=state['evidence_issues'],
                                refinement_count=max(metadata.get('refinement_count', 0), state['refinement_count']))
            if state['plan']:
                metadata.update(plan_reason=state['plan'].get('reason'), knowledge_profile=self.settings.knowledge_profile,
                                task_count=len(state['plan']['tasks']),
                                planned_agent_count=len({t['agent_id'] for t in state['plan']['tasks']}))
            if state['context']:
                metadata['context_status'] = self._context_status(state['context'])
            run.details_json = json.dumps(metadata)
            db.commit()

    def _failed(self, state, error):
        usable = list({doc['id']: doc for obs in state['observations'] for doc in obs['result'].get('documents', [])}.values())
        partial = bool(usable) and error.outcome == 'failed' and error.code.endswith('EXCEEDED')
        return {'outcome': 'partial' if partial else error.outcome, 'error_code': error.code,
                'answer': ('【预算受限】' if self.settings.deepseek_enabled else '【离线模拟】') + '达到执行预算，仅返回已取得资料，尚未完成任务。' if partial else '本轮未完成，具体原因请查看运行状态。',
                'sources': usable if partial else []}

    def _node(self, name, function):
        def execute(original):
            state = deepcopy(original)
            try:
                if name != 'persist_result':
                    self._guard(state)
                update = function(state)
            except GraphInterrupt:
                raise
            except StopFlow as error:
                if error.code == 'LEASE_LOST':
                    raise ApiError(409, 'RUN_BUSY', '运行已由另一执行者接管，请查询最新状态') from None
                update = self._failed(state, error)
            except ApiError:
                raise
            except Exception:
                update = self._failed(state, StopFlow('NODE_FAILED'))
            self._event({**state, **update}, name, update.get('outcome') or 'completed')
            return {**state, **update}
        return execute

    def build_graph(self):
        graph = StateGraph(State)
        for name, function in [('safety_gate', self._safety_gate), ('load_context', self._context), ('route', self._route), ('clarify', self._clarify),
                               ('plan', self._plan), ('worker', self._worker), ('tools', self._tools),
                               ('validate_output', self._validate), ('dispatch', self._dispatch),
                               ('check_evidence', self._evidence), ('synthesize', self._synthesize),
                               ('review_answer', self._review_output), ('persist_result', self._persist)]:
            graph.add_node(name, self._node(name, function))
        graph.add_edge(START, 'safety_gate')
        graph.add_conditional_edges('safety_gate', lambda s: 'persist_result' if s['outcome'] else
                                    ('route' if s['revision'] and s['context'] else 'load_context'))
        graph.add_conditional_edges('load_context', lambda s: 'persist_result' if s['outcome'] else 'route')
        graph.add_conditional_edges('route', lambda s: 'persist_result' if s['outcome'] else ('clarify' if '请澄清' in s['question'] and s['revision'] == 0 else ('plan' if s['plan_status'] == 'pending' else 'worker')))
        graph.add_conditional_edges('clarify', lambda s: 'persist_result' if s['outcome'] else 'safety_gate')
        graph.add_conditional_edges('plan', lambda s: 'persist_result' if s['outcome'] else ('dispatch' if len(s['plan']['tasks']) > 1 else 'worker'))
        graph.add_conditional_edges('dispatch', lambda s: 'persist_result' if s['outcome'] else 'check_evidence')
        graph.add_conditional_edges('check_evidence', lambda s: 'persist_result' if s['outcome'] else (
            'check_evidence' if s['evidence_status'] == 'rechecking' else (
                'dispatch' if len(s['task_results']) < len(s['plan']['tasks']) else 'synthesize')))
        graph.add_edge('synthesize', 'review_answer')
        graph.add_conditional_edges('worker', lambda s: 'persist_result' if s['outcome'] else ('tools' if s['pending_calls'] else 'validate_output'))
        graph.add_conditional_edges('tools', lambda s: 'persist_result' if s['outcome'] else 'worker')
        graph.add_edge('validate_output', 'review_answer')
        graph.add_edge('review_answer', 'persist_result')
        graph.add_edge('persist_result', END)
        return graph

    def build_worker_graph(self):
        # Workers share the ReAct implementation, but each invocation owns its state.
        # Durable recovery is at wave/task boundaries; provider calls are read-only.
        graph = StateGraph(dict)
        for name, function in [('task_worker', self._worker), ('task_tools', self._tools), ('task_validate', self._validate)]:
            graph.add_node(name, self._node(name, function))
        graph.add_edge(START, 'task_worker')
        graph.add_conditional_edges('task_worker', lambda s: END if s['outcome'] else ('task_tools' if s['pending_calls'] else 'task_validate'))
        graph.add_conditional_edges('task_tools', lambda s: END if s['outcome'] else 'task_worker')
        graph.add_edge('task_validate', END)
        return graph

    def _safety_gate(self, state):
        if self.settings.knowledge_profile != 'medical': return {}
        urgent = urgent_policy_trigger(state['question'])
        if not urgent and not fabricated_evidence_request(state['question']): return {}
        origin, policy = ('urgent_policy', 'urgent') if urgent else ('refusal_policy', 'untrusted_sources')
        with self.store.sessions() as db:
            db.connection().exec_driver_sql('BEGIN IMMEDIATE')
            run = db.get(Run, state['run_id'])
            metadata = details(run)
            if metadata.get('lease_token') != self.controls[run.id][0]: raise StopFlow('LEASE_LOST')
            metadata.update(response_origin=origin, safety_policy=policy, reviewer_status='skipped_policy',
                citation_support_status='policy_exempt', clinical_review_status='not_run',
                task_count=0, planned_agent_count=0, distinct_agent_count=0)
            run.details_json = json.dumps(metadata)
            db.commit()
        status = 'skipped_urgent' if urgent else 'skipped_policy'
        return {'outcome': 'completed', 'answer': URGENT_MESSAGE if urgent else REFUSAL_MESSAGE, 'plan_status': 'skipped',
                'context': {'urgent_skipped': urgent, 'policy_skipped': True,
                    'memory_status': status, 'summary_status': status}}

    def _context(self, state):
        with self.store.sessions() as db:
            scope = (Message.session_id == state['session_id'], Message.run_id != state['run_id'],
                     Run.run_status.in_(['finished', 'failed', 'cancelled', 'timed_out']))
            user_sequences = db.scalars(select(Message.seq).join(Run, Message.run_id == Run.id).where(*scope, Message.role == 'user').order_by(Message.seq.desc()).limit(self.settings.recent_turns)).all()
            rows = db.scalars(select(Message).join(Run, Message.run_id == Run.id).where(*scope, Message.seq >= min(user_sequences)).order_by(Message.seq)).all() if user_sequences else []
            total = db.scalar(select(func.count()).select_from(Message).join(Run, Message.run_id == Run.id).where(*scope))
            needed_coverage = db.scalar(select(func.max(Message.seq)).join(Run, Message.run_id == Run.id).where(*scope, Message.seq < min(user_sequences))) if user_sequences else 0
            history = redact_messages(rows, obsolete_message_ids(db, state['user_id']))
            summary = db.get(SessionSummary, state['session_id'])
            summary_data = {'content': summary.content, 'covered_until_seq': summary.covered_until_seq,
                            'version': summary.version} if summary and summary.status == 'ready' else None
            # 1. 确定性加载 SQL 固定偏好 (语言、详略、角色身份)
            sql_facts = list(db.scalars(select(MemoryFact).where(MemoryFact.user_id == state['user_id'], MemoryFact.status == 'active')))
            fixed_preferences = {f.key: f.content for f in sql_facts if f.key in ('answer_language', 'answer_style', 'occupation', 'research_goal') or f.key.startswith('pref_')}
            # 2. 加载连续任务与学习状态
            from .models import SessionLearningState
            learning_row = db.get(SessionLearningState, state['session_id'])
            learning_state = {
                'learning_goal': learning_row.learning_goal if learning_row else '心血管与慢病循证知识系统学习',
                'completed_topics': json.loads(learning_row.completed_topics_json) if learning_row else [],
                'unresolved_questions': json.loads(learning_row.unresolved_questions_json) if learning_row else [],
                'next_steps': json.loads(learning_row.next_steps_json) if learning_row else [],
                'last_topic': learning_row.last_topic if learning_row else None,
                'last_entities': json.loads(learning_row.last_entities_json) if learning_row else [],
            }
        original_size = len(history)
        while sum(len(m['content']) for m in history) > self.settings.max_context_chars and history:
            next_user = next((i for i, m in enumerate(history[1:], 1) if m['role'] == 'user'), len(history))
            history = history[next_user:]
        memory_error = None
        try:
            memories = self.maintenance.filter_memories(state['user_id'], self._call(state, self.memory.search, state['user_id'], state['question']))
            memory_status = ('ready' if memories else 'empty') if self.settings.mem0_enabled else 'simulated'
        except ProviderError as error:
            memories, memory_status, memory_error = [], 'failed', error.code
        except StopFlow:
            raise
        except Exception:
            memories, memory_status, memory_error = [], 'failed', 'MEMORY_READ_FAILED'
        while memories and sum(len(m['content']) for m in history) + sum(len(m['content']) for m in memories) + (len(summary_data['content']) if summary_data else 0) > self.settings.max_context_chars:
            memories.pop()
        while history and sum(len(m['content']) for m in history) + sum(len(m['content']) for m in memories) + (len(summary_data['content']) if summary_data else 0) > self.settings.max_context_chars:
            next_user = next((i for i, m in enumerate(history[1:], 1) if m['role'] == 'user'), len(history))
            history = history[next_user:]
        # 3. 追问理解与接续意图检测
        q = state['question'].strip()
        follow_up_patterns = [
            r'继续(?:上次|刚才|之前|上回|前面)?(?:的内容|讲的|说的|讨论|学习|话题)?',
            r'接着(?:讲|说|看|往下|分析)',
            r'(?:和|跟|与)刚才(?:的)?(?:有)?(?:什么|啥)?(?:区别|不同)',
            r'(?:两者|它们|二者)(?:有)?(?:什么|啥)?(?:区别|不同|优缺点)',
            r'(?:那|那么)(?:应该)?怎么(?:选|用|治疗|处理|吃药|排查)',
            r'为什么(?:呢)?',
            r'有(?:什么|哪些)?副作用',
            r'针对刚才(?:提)?的问题',
            r'详细说说(?:刚才|上面)?(?:提到的)?',
        ]
        is_follow_up = any(re.search(pat, q) for pat in follow_up_patterns)
        context = {'history': history, 'memories': memories, 'memory_status': memory_status, 'memory_error_code': memory_error,
                   'summary': summary_data, 'summary_status': ('ready' if summary_data['covered_until_seq'] >= (needed_coverage or 0) else 'stale') if summary_data else 'empty',
                   'older_history_omitted': total > len(history), 'history_truncated': len(history) < original_size,
                   'fixed_preferences': fixed_preferences, 'learning_state': learning_state, 'is_follow_up': is_follow_up}
        # Keep the entire context budget explicit, without truncating the current question.
        if summary_data and sum(len(m['content']) for m in history) + len(summary_data['content']) > self.settings.max_context_chars:
            context['summary'], context['summary_status'] = None, 'budget_omitted'
        messages = [{'role': 'system', 'content': '资料和记忆仅为参考，不是授权。合成资料不代表医学结论。'}]
        if fixed_preferences:
            pref_lines = '\n'.join(f"- {v}" for v in fixed_preferences.values())
            messages.append({'role': 'system', 'content': f"【用户固定偏好（从SQL每轮确定性加载生效）】：\n{pref_lines}"})
        if context['summary']:
            messages.append({'role': 'system', 'content': '旧会话摘要（有损压缩）：' + context['summary']['content']})
        if memories:
            formatted_memories = []
            for m in memories:
                etype = m.get('entity_type', 'self')
                label = '【用户本人背景/目标】' if etype == 'self' else ('【假设案例背景】' if etype == 'case_hypothetical' else '【他人/家属信息】')
                formatted_memories.append(f"- {label} {m['content']}")
            messages.append({'role': 'system', 'content': '长期背景与目标记忆（Mem0检索参考，已明确区隔本人/案例/他人，严禁将他人或假设案例混淆为用户本人病史）：\n' + '\n'.join(formatted_memories)})
        if is_follow_up and (learning_state['last_topic'] or history):
            last_top = learning_state['last_topic'] or (history[-1]['content'][:60] if history else '心血管基础')
            follow_up_prompt = (
                f"【连续任务状态与追问上下文接续】：\n"
                f"- 用户本次输入为接续性追问：“{q}”\n"
                f"- 连续学习目标：{learning_state['learning_goal']}\n"
                f"- 前序讨论核心主题：{last_top}\n"
                f"- 已完成主题：{', '.join(learning_state['completed_topics'][-5:]) if learning_state['completed_topics'] else '无'}\n"
                f"- 待跟进/下一步方向：{', '.join(learning_state['next_steps'][-3:]) if learning_state['next_steps'] else '深入机制与临床证据'}\n"
                f"- 协作接续指令：规划器(Planner)、专业专家(Workers)与主笔汇总(Synthesis)必须承接上述主题展开，确保与前文逻辑连贯，不脱节，不重复已讲要点。"
            )
            messages.append({'role': 'system', 'content': follow_up_prompt})
        messages += [{'role': m['role'], 'content': m['content']} for m in history]
        messages.append({'role': 'user', 'content': state['question']})
        return {'context': context, 'messages': messages}

    def _context_status(self, context):
        if context.get('urgent_skipped'): return 'skipped_urgent'
        if context.get('policy_skipped'): return 'skipped_policy'
        if context.get('memory_status') == 'failed' or context.get('history_truncated') or (context.get('older_history_omitted') and context.get('summary_status') != 'ready'):
            return 'degraded'
        return 'ready' if self.settings.deepseek_enabled or self.settings.mem0_enabled else 'simulated'

    def _route(self, state):
        complex_query = self.settings.knowledge_profile == 'medical' or any(word in state['question'] for word in ('检索', '查询', '研究', '联网', '多任务', '多专家', '三个专家'))
        return {'plan_status': 'pending' if complex_query else 'skipped', 'agent_id': 'consultation_agent'}

    def _clarify(self, state):
        prompt = ('' if self.settings.deepseek_enabled else '【离线模拟】') + '请补充你希望查询或解释的具体问题。'
        with self.store.sessions() as db:
            db.connection().exec_driver_sql('BEGIN IMMEDIATE')
            run = db.get(Run, state['run_id'])
            exists = db.scalar(select(ExecutionEvent.id).where(ExecutionEvent.event_key == run.id + ':clarification_prompt'))
            if not exists:
                conversation = db.get(Conversation, run.session_id)
                db.add(Message(session_id=run.session_id, run_id=run.id, seq=conversation.next_seq, role='assistant', content=prompt))
                conversation.next_seq += 1
                run.run_status, run.answer = 'awaiting_input', prompt
                db.add(ExecutionEvent(run_id=run.id, stage='clarify', status='awaiting_input', event_key=run.id + ':clarification_prompt'))
            db.commit()
        clarification = interrupt({'prompt': prompt})
        return {'question': state['question'] + '\n用户补充：' + clarification, 'revision': state['revision'] + 1,
                'messages': state['messages'] + [{'role': 'assistant', 'content': prompt}, {'role': 'user', 'content': clarification}]}

    def _plan(self, state):
        try:
            plan = self._contract_call(state, 'plan', self.model.plan, Plan.model_validate, 'PLAN_INVALID')
        except StopFlow as error:
            if error.outcome != 'failed' or error.code == 'LEASE_LOST': raise
            return {'plan_status': 'failed', **self._failed(state, error)}
        except ProviderError as error:
            return {'plan_status': 'failed', **self._failed(state, StopFlow(error.code))}
        except Exception:
            return {'plan_status': 'failed', **self._failed(state, StopFlow('PLAN_INVALID'))}
        return {'plan': plan.model_dump(), 'plan_status': 'completed', 'agent_id': plan.tasks[0].agent_id,
                'task_description': plan.tasks[0].description if len(plan.tasks) == 1 else None}

    def _tool_offer(self, state):
        with self.store.sessions() as db:
            metadata = details(db.get(Run, state['run_id']))
        models = max(0, self.settings.max_model_calls - metadata.get('model_calls', 0))
        tools = max(0, self.settings.max_tool_calls - metadata.get('tool_calls', 0))
        if state.get('task_id'):
            models = min(models, max(0, self.settings.max_worker_model_calls - state['model_calls']))
            tools = min(tools, max(0, self.settings.max_worker_tool_calls - state['tool_calls']))
        iterations = max(0, self.settings.max_worker_iterations - state['worker_iterations'])
        # A tool result needs another model turn to become an answer. Do not
        # advertise operations that cannot fit; actual execution still rechecks
        # durable global/worker budgets, including concurrent consumption.
        allowed = self.tools.enabled_names(state['agent_id']) if models and tools and iterations else []
        return {'allowed_tools': allowed, 'remaining_model_calls': models, 'remaining_tool_calls': tools,
                'remaining_iterations': iterations}

    def _worker(self, state):
        if state['worker_iterations'] >= self.settings.max_worker_iterations:
            raise StopFlow('ITERATION_BUDGET_EXCEEDED')
        state['worker_iterations'] += 1
        self._consume(state, 'model_calls', self.settings.max_model_calls, 'MODEL_BUDGET_EXCEEDED')
        try:
            payload = deepcopy(state)
            payload.update(self._tool_offer(state))
            raw = self._call(state, self.model.decide, payload)
        except StopFlow:
            raise
        except ProviderError as error:
            with self.store.sessions() as db:
                db.connection().exec_driver_sql('BEGIN IMMEDIATE')
                run = db.get(Run, state['run_id'])
                metadata = details(run)
                if metadata.get('lease_token') != self.controls[run.id][0]:
                    raise StopFlow('LEASE_LOST')
                metadata['provider_contract_details'] = error.details
                counts = metadata.setdefault('contract_repair_counts',
                    {'worker': metadata['schema_repair_count']} if metadata.get('schema_repair_count') else {})
                repair = error.code in ('MODEL_DECISION_INVALID', 'MODEL_JSON_INVALID') and counts.get('worker', 0) < self.settings.schema_repair_limit
                if repair:
                    counts['worker'] = counts.get('worker', 0) + 1
                    metadata['schema_repair_count'] = metadata.get('schema_repair_count', 0) + 1
                run.details_json = json.dumps(metadata)
                db.commit()
            if repair:
                self._consume(state, 'model_calls', self.settings.max_model_calls, 'MODEL_BUDGET_EXCEEDED')
                payload['format_repair'] = True
                payload.update(self._tool_offer(state))
                try:
                    raw = self._call(state, self.model.decide, payload)
                except ProviderError as second:
                    raise StopFlow(second.code) from None
            else:
                raise StopFlow(error.code) from None
        except Exception:
            raise StopFlow('MODEL_FAILED') from None
        try:
            decision = Decision.model_validate(raw)
        except ValidationError:
            raise StopFlow('OUTPUT_INVALID') from None
        return {'pending_calls': [call.model_dump() for call in decision.tool_calls],
                'answer': decision.answer, 'source_ids': decision.source_ids}

    def _tools(self, state):
        messages = state['messages'] + [{'role': 'assistant', 'content': None, 'tool_calls': [
            {'id': c['id'], 'type': 'function', 'function': {'name': c['name'], 'arguments': json.dumps(c['arguments'])}}
            for c in state['pending_calls']]}]
        state['messages'] = messages
        for call in state['pending_calls']:
            failure = None
            try:
                self._guard(state)
                if not self.tools.allowed(call['name'], state['agent_id']):
                    raise StopFlow('TOOL_NOT_ALLOWED')
                try:
                    args = SearchArgs.model_validate(call['arguments']).model_dump()
                except ValidationError:
                    raise StopFlow('TOOL_ARGUMENTS_INVALID') from None
                self._consume(state, 'tool_calls', self.settings.max_tool_calls, 'TOOL_BUDGET_EXCEEDED')
                try:
                    result = ToolResult.model_validate(self._call(state, self.tools.execute, call['name'], args, deepcopy(state))).model_dump()
                except StopFlow:
                    raise
                except ProviderError as error:
                    raise StopFlow(error.code) from None
                except Exception:
                    raise StopFlow('TOOL_FAILED') from None
                if not result['success']:
                    raise StopFlow('TOOL_FAILED')
                state['observations'].append({'call_id': call['id'], 'name': call['name'], 'result': result})
            except StopFlow as error:
                failure = error
                result = {'success': False, 'documents': [], 'safe_error_code': error.code}
            messages.append({'role': 'tool', 'tool_call_id': call['id'], 'content': json.dumps(result, ensure_ascii=False)})
            self._evidence_diagnostic(state, {'stage': 'retrieval', 'tool': call['name'],
                'query_sha256': hashlib.sha256(str(call['arguments'].get('query', '')).encode()).hexdigest(),
                'status': result.get('status', 'failed' if failure else 'completed'),
                'retrieved_count': len(result.get('documents', [])),
                'retrieved_ids': [d['id'] for d in result.get('documents', [])],
                'safe_error_code': result.get('safe_error_code')})
            if failure:
                # Pair remaining calls with explicit unexecuted results as well.
                remaining = state['pending_calls'][state['pending_calls'].index(call) + 1:]
                messages += [{'role': 'tool', 'tool_call_id': c['id'], 'content': json.dumps({'success': False, 'safe_error_code': 'NOT_EXECUTED'})} for c in remaining]
                return {'pending_calls': [], **self._failed(state, failure)}
        return {'pending_calls': []}

    def _validate(self, state):
        documents = {}
        for doc in source_documents(state):
            if doc['id'] in documents and source_identity(documents[doc['id']]) != source_identity(doc):
                raise StopFlow('SOURCE_CONFLICT')
            documents[doc['id']] = doc
        aliases = {}
        for doc in documents.values():
            if doc.get('document_id'):
                aliases.setdefault(doc['document_id'], []).append(doc['id'])
            if doc['source'] == 'pubmed' and doc['id'].startswith('pubmed-'):
                aliases.setdefault(doc['id'][7:], []).append(doc['id'])
        resolved = [key if key in documents else aliases[key][0] if len(aliases.get(key, [])) == 1 else key for key in state['source_ids']]
        self._evidence_diagnostic(state, {'stage': 'citation_selection', 'retrieved_count': len(documents),
            'selected_count': len(resolved), 'selected_ids': [k for k in resolved if k in documents],
            'unknown_count': sum(k not in documents for k in resolved),
            'refinement': bool(state.get('refinement'))})
        if not state['answer'] or any(source_id not in documents for source_id in resolved):
            raise StopFlow('OUTPUT_INVALID')
        tasks = state['plan'].get('tasks', [])
        if not state.get('task_id') and len(tasks) == 1 and tasks[0]['require_sources'] and not state['source_ids']:
            if not is_policy_or_refusal(state.get('answer', ''), state.get('question', '')):
                raise StopFlow('EVIDENCE_MISSING')
        return {'outcome': 'completed', 'source_ids': resolved, 'sources': [documents[key] for key in dict.fromkeys(resolved)]}

    def _persist(self, state):
        with self.store.sessions() as db:
            db.connection().exec_driver_sql('BEGIN IMMEDIATE')
            run = db.get(Run, state['run_id'])
            metadata = details(run)
            if metadata.get('lease_token') != self.controls[run.id][0]:
                raise ApiError(409, 'RUN_BUSY', '运行所有权已变化，请查询最新状态')
            if run.cancel_requested:
                state.update(self._failed(state, StopFlow('CANCELLED', 'cancelled')))
            if run.finished_at is None:
                conversation = db.get(Conversation, run.session_id)
                db.add(Message(session_id=run.session_id, run_id=run.id, seq=conversation.next_seq, role='assistant', content=state['answer']))
                conversation.next_seq += 1
                conversation.updated_at = timestamp()
            run.run_status = 'finished' if state['outcome'] in ('completed', 'partial') else state['outcome']
            run.result_status, run.answer, run.safe_error_code = state['outcome'], state['answer'], state['error_code']
            run.finished_at = timestamp()
            metadata.update(graph_version=self.version, plan_status=state['plan_status'], agent_id=state['agent_id'],
                            plan_reason=state['plan'].get('reason'), knowledge_profile=self.settings.knowledge_profile,
                            sources=state['sources'], worker_iterations=state['worker_iterations'],
                            context_status=self._context_status(state['context']))
            if state['task_results']:
                metadata.update(task_results=state['task_results'],
                                worker_iterations=sum(r['worker_iterations'] for r in state['task_results']))
            metadata['context_details'] = {k: state['context'].get(k) for k in
                ('memory_status', 'memory_error_code', 'summary_status', 'older_history_omitted', 'history_truncated')}
            metadata['context_details']['memory_count'] = len(state['context'].get('memories', []))
            if state['context'].get('summary'):
                metadata['summary_coverage'] = state['context']['summary']['covered_until_seq']

            # 持久化更新连续任务状态与追问记录
            from .models import SessionLearningState
            l_row = db.get(SessionLearningState, run.session_id)
            if state['outcome'] in ('completed', 'partial') and state.get('answer') and not state['context'].get('policy_skipped'):
                if l_row is None:
                    l_row = SessionLearningState(
                        session_id=run.session_id,
                        user_id=run.user_id,
                        learning_goal='心血管与慢病循证知识系统学习',
                        completed_topics_json='[]',
                        unresolved_questions_json='[]',
                        next_steps_json='[]',
                        last_entities_json='[]'
                    )
                    db.add(l_row)
                goal_match = re.search(r'我(?:想|要|希望)?(?:学习|掌握|了解|搞懂)([^。；\n]{3,60})', state['question'])
                if goal_match:
                    l_row.learning_goal = goal_match.group(1).strip()
                if not state['context'].get('is_follow_up'):
                    topic = state['question'][:40].strip()
                    l_row.last_topic = topic
                    completed = json.loads(l_row.completed_topics_json or '[]')
                    if topic not in completed:
                        completed.append(topic)
                    l_row.completed_topics_json = json.dumps(completed[-20:], ensure_ascii=False)
                else:
                    follow_topic = f"{l_row.last_topic or '前序主题'} (追问: {state['question'][:20].strip()})"
                    completed = json.loads(l_row.completed_topics_json or '[]')
                    if follow_topic not in completed:
                        completed.append(follow_topic)
                    l_row.completed_topics_json = json.dumps(completed[-20:], ensure_ascii=False)
                
                # 记录未解决问题
                unresolved = json.loads(l_row.unresolved_questions_json or '[]')
                if re.search(r'为什么|机制|尚未明确|不清楚|待解决|排查|区别|如何选择', state['question']):
                    q_item = state['question'][:50].strip()
                    if q_item not in unresolved:
                        unresolved.append(q_item)
                l_row.unresolved_questions_json = json.dumps(unresolved[-5:], ensure_ascii=False)

                found_entities = re.findall(r'CCB|ARB|ACEI|β受体阻滞剂|利尿剂|SGLT2i|GLP-1|他汀|阿司匹林|硝酸甘油|高血压|心衰|冠心病|心房颤动|\d+/\d+\s*mmHg|\d+\.?\d*%', state['answer'])
                l_row.last_entities_json = json.dumps(list(dict.fromkeys(found_entities))[:15], ensure_ascii=False)
                next_steps = []
                if re.search(r'下一步|后续|建议|进一步|复查|监测', state['answer']):
                    sentences = re.split(r'[。；\n]', state['answer'])
                    for s in sentences:
                        if re.search(r'建议(?:进一步|复查|监测|排查|关注|就医)', s):
                            next_steps.append(s.strip()[:60])
                l_row.next_steps_json = json.dumps(next_steps[:5], ensure_ascii=False)
                l_row.updated_at = timestamp()

            metadata['learning_state'] = {
                'learning_goal': l_row.learning_goal if l_row else state['context'].get('learning_state', {}).get('learning_goal', '心血管与慢病循证知识学习'),
                'last_topic': l_row.last_topic if l_row else state['context'].get('learning_state', {}).get('last_topic'),
                'completed_topics': json.loads(l_row.completed_topics_json or '[]') if l_row else state['context'].get('learning_state', {}).get('completed_topics', []),
                'unresolved_questions': json.loads(l_row.unresolved_questions_json or '[]') if l_row else state['context'].get('learning_state', {}).get('unresolved_questions', []),
                'next_steps': json.loads(l_row.next_steps_json or '[]') if l_row else state['context'].get('learning_state', {}).get('next_steps', []),
            }
            metadata['memory_fixed_preferences'] = state['context'].get('fixed_preferences', {})
            run.details_json = json.dumps(metadata, ensure_ascii=False)
            metadata['memory_write_status'] = ('skipped_urgent_policy' if metadata.get('response_origin') == 'urgent_policy'
                                              else 'skipped_refusal_policy' if metadata.get('response_origin') == 'refusal_policy'
                                              else self.maintenance.enqueue(db, run, state['question']))
            run.details_json = json.dumps(metadata, ensure_ascii=False)
            db.commit()
        self.maintenance.kick()
        return state

    def _initial(self, run, question):
        return {'run_id': run.id, 'session_id': run.session_id, 'user_id': run.user_id, 'question': question,
                'context': {}, 'messages': [], 'observations': [], 'pending_calls': [], 'source_ids': [], 'sources': [],
                'agent_id': 'consultation_agent', 'plan': {}, 'plan_status': 'skipped', 'model_calls': 0,
                'tool_calls': 0, 'worker_iterations': 0, 'revision': 0, 'outcome': None, 'answer': None, 'error_code': None,
                'task_results': [], 'evidence_status': 'not_run', 'evidence_issues': [], 'refinement_count': 0,
                'task_description': None}

    def _execute(self, run_id, token, graph_input):
        self.controls[run_id] = (token, time.monotonic() + self.settings.run_timeout_seconds)
        try:
            with tracing_context(enabled=False):
                self.graph.invoke(graph_input, self.config(run_id))
            snapshot = self.snapshot(run_id)
            with self.store.sessions() as db:
                db.connection().exec_driver_sql('BEGIN IMMEDIATE')
                run = db.get(Run, run_id)
                metadata = details(run)
                metadata['checkpoint_id'] = snapshot.config['configurable']['checkpoint_id']
                if snapshot.next and run.run_status == 'running':
                    run.run_status = 'paused'
                run.details_json = json.dumps(metadata)
                db.commit()
                return run_output(run)
        except Exception:
            snapshot = self.snapshot(run_id)
            with self.store.sessions() as db:
                db.connection().exec_driver_sql('BEGIN IMMEDIATE')
                run = db.get(Run, run_id)
                metadata = details(run)
                if metadata.get('lease_token') != token:
                    raise ApiError(409, 'RUN_BUSY', '运行已由另一执行者接管，请查询最新状态') from None
                if snapshot.config:
                    metadata['checkpoint_id'] = snapshot.config['configurable']['checkpoint_id']
                if run.finished_at is None:
                    run.run_status = 'paused'
                    run.safe_error_code = 'EXECUTION_INTERRUPTED'
                run.details_json = json.dumps(metadata)
                db.commit()
            raise ApiError(503, 'EXECUTION_INTERRUPTED', '运行中断；重试原请求获取run_id，再查询检查点状态') from None
        finally:
            with self.store.sessions() as db:
                db.connection().exec_driver_sql('BEGIN IMMEDIATE')
                run = db.get(Run, run_id)
                metadata = details(run)
                if metadata.get('lease_token') == token:
                    metadata.update(lease_token=None, lease_until=0)
                    run.details_json = json.dumps(metadata)
                    db.commit()
            self.controls.pop(run_id, None)

    def submit(self, user_id, session_id, body):
        with self.session_lock(session_id):
            with self.store.sessions() as db:
                db.connection().exec_driver_sql('BEGIN IMMEDIATE')
                conversation = owned_session(db, session_id, user_id)
                fingerprint = hashlib.sha256(json.dumps([session_id, body.question], ensure_ascii=False).encode()).hexdigest()
                previous = db.scalar(select(Run).where(Run.user_id == user_id, Run.request_id == str(body.request_id)))
                if previous:
                    if previous.fingerprint != fingerprint:
                        raise ApiError(409, 'IDEMPOTENCY_CONFLICT', '同一request_id不能用于不同会话或问题')
                    return run_output(previous, replayed=True)
                active = db.scalar(select(Run.id).where(Run.session_id == session_id, Run.run_status.in_(['running', 'awaiting_input', 'paused'])))
                if active:
                    raise ApiError(409, 'SESSION_BUSY', '请先恢复或取消该会话的当前运行')
                run = Run(user_id=user_id, session_id=session_id, request_id=str(body.request_id), fingerprint=fingerprint,
                          details_json=json.dumps({'graph_version': self.version, 'model_calls': 0, 'tool_calls': 0,
                             'mode': 'cloud_real' if self.settings.deepseek_enabled else ('hybrid' if self.settings.mem0_enabled or self.settings.web_search_enabled or self.settings.knowledge_enabled else 'offline_fake')}))
                db.add(run)
                db.flush()
                db.add(Message(session_id=session_id, run_id=run.id, seq=conversation.next_seq, role='user', content=body.question))
                conversation.next_seq += 1
                token = self._claim(db, run)
                initial = self._initial(run, body.question)
                run_id = run.id
                db.commit()
            return self._execute(run_id, token, initial)

    def resume(self, user_id, run_id, body):
        with self.store.sessions() as db:
            session_id = self.owned_run(db, run_id, user_id).session_id
        with self.session_lock(session_id):
            snapshot = self.snapshot(run_id)
            with self.store.sessions() as db:
                db.connection().exec_driver_sql('BEGIN IMMEDIATE')
                run = self.owned_run(db, run_id, user_id)
                metadata = details(run)
                resume_fingerprint = hashlib.sha256(json.dumps([body.checkpoint_id, body.clarification], ensure_ascii=False).encode()).hexdigest()
                if run.run_status not in ('running', 'paused', 'awaiting_input'):
                    if metadata.get('resume_fingerprint') == resume_fingerprint:
                        return run_output(run, replayed=True)
                    raise ApiError(409, 'RUN_TERMINAL', '运行已结束，不能再次恢复')
                if not snapshot.values or snapshot.values.get('run_id') != run_id or metadata.get('graph_version') != self.version:
                    raise ApiError(409, 'CHECKPOINT_UNAVAILABLE', '检查点缺失或版本不匹配')
                retry = metadata.get('resume_fingerprint') == resume_fingerprint
                if snapshot.config['configurable']['checkpoint_id'] != body.checkpoint_id and not retry:
                    raise ApiError(409, 'STALE_CHECKPOINT', '检查点已变化，请读取最新运行状态')
                waiting = run.run_status == 'awaiting_input' or (snapshot.values.get('revision') == 0 and metadata.get('pending_clarification') is not None)
                if waiting and not body.clarification:
                    raise ApiError(422, 'CLARIFICATION_REQUIRED', '请提供补充问题')
                token = self._claim(db, run)
                if waiting and metadata.get('pending_clarification') is not None and metadata['pending_clarification'] != body.clarification:
                    raise ApiError(409, 'RESUME_CONFLICT', '恢复内容已提交，请重试相同内容')
                if waiting and metadata.get('pending_clarification') is None:
                    conversation = db.get(Conversation, session_id)
                    db.add(Message(session_id=session_id, run_id=run_id, seq=conversation.next_seq, role='user', content=body.clarification))
                    conversation.next_seq += 1
                metadata = details(run)
                metadata.update(resume_fingerprint=resume_fingerprint)
                if waiting:
                    metadata['pending_clarification'] = body.clarification
                run.details_json = json.dumps(metadata)
                run.run_status, run.answer = 'running', None
                db.commit()
            return self._execute(run_id, token, Command(resume=body.clarification) if waiting else None)

    def cancel(self, user_id, run_id):
        with self.store.sessions() as db:
            db.connection().exec_driver_sql('BEGIN IMMEDIATE')
            run = self.owned_run(db, run_id, user_id)
            if run.run_status == 'cancelled':
                return run_output(run, replayed=True)
            if run.finished_at is not None:
                raise ApiError(409, 'RUN_TERMINAL', '运行已结束，不能取消已完成结果')
            run.cancel_requested = True
            db.execute(insert(ExecutionEvent).values(run_id=run_id, stage='cancel_requested', status='running',
                                                     event_key=run_id + ':cancel_requested').on_conflict_do_nothing(index_elements=['event_key']))
            if details(run).get('lease_until', 0) <= time.time():
                conversation = db.get(Conversation, run.session_id)
                run.run_status = run.result_status = 'cancelled'
                run.answer, run.safe_error_code, run.finished_at = '本轮已取消。', 'CANCELLED', timestamp()
                db.add(Message(session_id=run.session_id, run_id=run_id, seq=conversation.next_seq, role='assistant', content=run.answer))
                conversation.next_seq += 1
                metadata = details(run)
                metadata['stage'] = 'cancel'
                run.details_json = json.dumps(metadata)
                db.add(ExecutionEvent(run_id=run_id, stage='cancel', status='cancelled', event_key=run_id + ':cancelled'))
            db.commit()
            return run_output(run)
