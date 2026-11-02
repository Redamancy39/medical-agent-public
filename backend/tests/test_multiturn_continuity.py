"""Comprehensive regression test suite for continuous multi-turn cardiovascular learning assistant.

Covers:
1. Cross-session & turn-by-turn memory (deterministic SQL loading).
2. Continuous learning state & follow-up resolution ("继续刚才讲的", "有什么区别").
3. Memory correction and deletion lifecycle.
4. Entity isolation (self vs hypothetical cases vs third parties vs user isolation).
5. >10-turn rolling summary & history compression.
6. Mem0 unavailability graceful fallback degradation.
"""
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import create_app
from app.models import MemoryFact, SessionLearningState, SessionSummary
from app.providers import ProviderError
from test_api import app, client, login, session, settings
from test_graph import ask


def finish(app):
    if app.state.flow.maintenance.future:
        app.state.flow.maintenance.future.result(timeout=5)


def test_cross_session_and_deterministic_sql_preference_loading(client, app):
    """固定偏好（语言、风格）跨会话确定性从 SQL 每轮加载生效。"""
    headers = login(client, 'cross_session_user')
    sid1 = session(client, headers)
    
    # Session 1: 设定固定偏好
    res1 = ask(client, headers, sid1, '我偏好中文和详细的回答').json()
    assert res1['result_status'] == 'completed'
    finish(app)

    # 验证 SQL 事实表中记录了该偏好
    memories = client.get('/memories', headers=headers).json()['items']
    assert any(m['key'] == 'answer_language' and '中文' in m['content'] for m in memories)
    assert any(m['key'] == 'answer_style' and '详细' in m['content'] for m in memories)

    # Session 2: 全新会话，验证每轮从 SQL 确定性加载生效
    sid2 = session(client, headers)
    res2 = ask(client, headers, sid2, '高血压一线用药有哪些？').json()
    assert res2['result_status'] == 'completed'

    state = app.state.flow.snapshot(res2['run_id']).values
    fixed_prefs = state['context']['fixed_preferences']
    assert 'answer_language' in fixed_prefs and '中文' in fixed_prefs['answer_language']
    assert 'answer_style' in fixed_prefs and '详细' in fixed_prefs['answer_style']

    # 验证 messages 注入了 SQL 偏好指令
    pref_system_msg = next(m for m in state['messages'] if '【用户固定偏好（从SQL每轮确定性加载生效）】' in m['content'])
    assert '用户偏好回答语言：中文' in pref_system_msg['content']
    assert '用户偏好回答风格：详细' in pref_system_msg['content']


def test_multiturn_learning_state_and_follow_up_understanding(client, app):
    """连续任务状态追踪、追问意图识别与上下文接续。"""
    headers = login(client, 'learner_user')
    sid = session(client, headers)

    # 第 1 轮：明确学习目标并提问核心主题
    q1 = '我想学习原发性高血压分级与一线降压药物选择'
    res1 = ask(client, headers, sid, q1).json()
    assert res1['result_status'] == 'completed'

    # 检查会话学习状态
    state_out = client.get(f'/sessions/{sid}/learning-state', headers=headers).json()
    assert '原发性高血压' in state_out['learning_goal']
    assert state_out['last_topic'] is not None
    assert len(state_out['completed_topics']) >= 1

    # 第 2 轮：追问“继续刚才讲的，它俩有什么区别？”
    q2 = '继续刚才讲的，CCB与ACEI二者有什么区别？'
    res2 = ask(client, headers, sid, q2).json()
    assert res2['result_status'] == 'completed'

    state2 = app.state.flow.snapshot(res2['run_id']).values
    assert state2['context']['is_follow_up'] is True

    # 验证 messages 注入了追问接续指令
    follow_up_msg = next((m for m in state2['messages'] if '【连续任务状态与追问上下文接续】' in m['content']), None)
    assert follow_up_msg is not None
    assert '接续性追问' in follow_up_msg['content']
    assert '协作接续指令' in follow_up_msg['content']

    # 验证学习状态持续更新（记录未解决问题和最新主题）
    state_out2 = client.get(f'/sessions/{sid}/learning-state', headers=headers).json()
    assert any('区别' in item for item in state_out2['unresolved_questions'])
    assert len(state_out2['completed_topics']) >= 2


def test_memory_correction_and_deletion_lifecycle(client, app):
    """记忆修正与删除生命周期：支持在线纠正、撤回与脱敏。"""
    headers = login(client, 'correction_user')
    sid = session(client, headers)

    # 1. 设定初始背景
    ask(client, headers, sid, '我是研究生')
    finish(app)
    memories = client.get('/memories', headers=headers).json()['items']
    occ = next(m for m in memories if m['key'] == 'occupation')
    assert '研究生' in occ['content']
    assert occ['version'] == 1

    # 2. 纠正背景为心内科住院医
    ask(client, headers, sid, '纠正一下，我是心内科住院医')
    finish(app)
    memories = client.get('/memories', headers=headers).json()['items']
    occ_updated = next(m for m in memories if m['key'] == 'occupation')
    assert '心内科住院医' in occ_updated['content']
    assert occ_updated['version'] == 2

    # 3. 删除偏好与记忆
    ask(client, headers, sid, '删除我的偏好')
    finish(app)
    memories = client.get('/memories', headers=headers).json()['items']
    assert all(m['status'] == 'deleted' for m in memories)

    # 4. 后续提问不再加载已删除偏好
    res = ask(client, headers, sid, '请问顽固性高血压如何诊断？').json()
    state = app.state.flow.snapshot(res['run_id']).values
    assert state['context']['fixed_preferences'] == {}


def test_entity_isolation_self_hypothetical_thirdparty_and_user_separation(client, app):
    """实体隔离：区隔用户本人、假设案例、他人信息以及多用户数据隔离。"""
    headers_alice = login(client, 'alice_doctor')
    sid_alice = session(client, headers_alice)

    # Alice 提出假设案例（不应作为 Alice 本人病史记录）
    ask(client, headers_alice, sid_alice, '假设一个60岁高血压患者合并冠心病，一线降压药怎么选？')
    finish(app)
    memories_alice = client.get('/memories', headers=headers_alice).json()['items']
    assert not any(m['key'] == 'user_health_profile' for m in memories_alice)

    # Alice 记录家属病史（他人信息）
    ask(client, headers_alice, sid_alice, '请记住我父亲有高血压病史10年')
    finish(app)
    memories_alice = client.get('/memories', headers=headers_alice).json()['items']
    third_party_fact = next((m for m in memories_alice if m['key'] == 'third_party_info'), None)
    assert third_party_fact is not None
    assert third_party_fact['entity_type'] == 'third_party'
    assert '父亲' in third_party_fact['content']

    # Bob 登录：验证多用户隔离
    headers_bob = login(client, 'bob_patient')
    memories_bob = client.get('/memories', headers=headers_bob).json()['items']
    assert len(memories_bob) == 0  # Bob 看不到 Alice 的任何记忆

    sid_bob = session(client, headers_bob)
    res_bob = ask(client, headers_bob, sid_bob, '糖尿病的诊断标准是什么？').json()
    state_bob = app.state.flow.snapshot(res_bob['run_id']).values
    # Bob 的上下文绝不包含 Alice 的家属信息或偏好
    assert 'third_party_info' not in state_bob['context']['fixed_preferences']
    assert not any('父亲' in m.get('content', '') for m in state_bob['messages'])


def test_more_than_ten_turns_rolling_summary(client, app):
    """超过10轮后的滚动摘要与历史压缩。"""
    headers = login(client, 'marathon_user')
    sid = session(client, headers)

    # 连续对话 11 轮
    for i in range(11):
        r = ask(client, headers, sid, f'心血管问答第{i}轮：需要关注的要点{i}').json()
        assert r['result_status'] == 'completed'
    finish(app)

    # 验证摘要已生成
    summary = client.get(f'/sessions/{sid}/summary', headers=headers).json()
    assert summary['status'] == 'ready'
    assert summary['covered_until_seq'] > 0
    assert summary['content'] is not None

    # 第 12 轮：上下文包含摘要，且 older_history_omitted 为 True
    res12 = ask(client, headers, sid, '总结前面提到的关键问题').json()
    state12 = app.state.flow.snapshot(res12['run_id']).values
    assert state12['context']['summary'] is not None
    assert state12['context']['older_history_omitted'] is True
    # messages 中包含旧会话摘要
    assert any('旧会话摘要' in m.get('content', '') for m in state12['messages'])


def test_mem0_unavailable_graceful_degradation(client, app):
    """Mem0 故障或不可用时的降级容错：SQL 固定偏好依旧生效，系统正常返回。"""
    headers = login(client, 'fallback_user')
    sid = session(client, headers)

    # 先保存固定偏好
    ask(client, headers, sid, '我偏好中文回答')
    finish(app)

    # 模拟 Mem0 检索抛出不可用异常
    def broken_search(*args, **kwargs):
        raise ProviderError('MEMORY_UNAVAILABLE')

    app.state.flow.memory.search = broken_search

    # 执行提问
    res = ask(client, headers, sid, '心衰患者可以常规使用CCB吗？').json()
    assert res['result_status'] == 'completed'
    assert res['answer'] is not None

    # 验证上下文状态正确标记降级
    state = app.state.flow.snapshot(res['run_id']).values
    assert state['context']['memory_status'] == 'failed'
    assert state['context']['memory_error_code'] == 'MEMORY_UNAVAILABLE'

    # 验证 SQL 固定偏好依然完好加载生效
    assert 'answer_language' in state['context']['fixed_preferences']
    assert any('【用户固定偏好（从SQL每轮确定性加载生效）】' in m['content'] for m in state['messages'])
