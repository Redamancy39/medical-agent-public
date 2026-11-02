# -*- coding: utf-8 -*-
"""
验证 Phase 2 (Planner Priority Wave DAG) 和 Phase 3 (Adaptive Medical Reviewer) 的实测脚本
"""
import json
import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8010"

def run_test():
    # 1. 注册并登录获取 token
    user = f"test_verifier_{int(time.time())}"
    requests.post(f"{BASE_URL}/auth/register", json={"username": user, "password": "TestPassword123!"}, timeout=10)
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={"username": user, "password": "TestPassword123!"}, timeout=10)
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 读取 test_cases_v2.json 中的 DUAL-02, DUAL-03, TXB-02
    with open("backend/evaluation/test_cases_v2.json", "r", encoding="utf-8") as f:
        cases = json.load(f)
    case_map = {c["id"]: c for c in cases}

    test_ids = ["DUAL-02", "DUAL-03", "TXB-02"]
    results = {}

    for cid in test_ids:
        case = case_map[cid]
        print(f"\n=======================================================")
        print(f"正在测试用例 [{cid}] ({case['category']} - {case['specialty']})")
        print(f"问题: {case['question'][:60]}...")
        print(f"=======================================================")

        # 创建 session
        s_resp = requests.post(f"{BASE_URL}/sessions", json={"title": f"Test {cid}"}, headers=headers, timeout=10)
        session_id = s_resp.json()["id"]

        # 发送提问
        start_t = time.time()
        chat_resp = requests.post(
            f"{BASE_URL}/sessions/{session_id}/chat",
            json={"question": case["question"]},
            headers=headers,
            timeout=120
        )
        cost = time.time() - start_t
        print(f"响应耗时: {cost:.2f}s, HTTP状态码: {chat_resp.status_code}")
        
        if chat_resp.status_code != 200:
            print(f"请求失败: {chat_resp.text}")
            continue

        data = chat_resp.json()
        answer = data.get("answer", "")
        plan = data.get("plan", {})
        tasks = plan.get("tasks", []) if isinstance(plan, dict) else []
        review_metadata = data.get("review_metadata", {})
        sources = data.get("sources", [])

        print(f"\n[1] 规划器 Task 拆解 (共 {len(tasks)} 个任务):")
        for idx, t in enumerate(tasks, 1):
            print(f"  Task {idx}: id={t.get('task_id')}, agent={t.get('agent_id')}, depends_on={t.get('depends_on')}")
            print(f"          desc: {t.get('description')[:50]}...")

        print(f"\n[2] 回答字数: {len(answer)} 字符")
        print(f"回答前 150 字预览:\n{answer[:150]}...")

        print(f"\n[3] 审核器结果 (Review Metadata):")
        print(f"  status: {review_metadata.get('review_status')}")
        print(f"  verified: {review_metadata.get('verified')}")
        claims = review_metadata.get("claim_reviews", [])
        print(f"  核验命题数 (claims): {len(claims)}")
        supported = [c for c in claims if c.get("support_status") == "supported"]
        unsupported = [c for c in claims if c.get("support_status") != "supported"]
        print(f"  支持数: {len(supported)}, 未支持数: {len(unsupported)}")
        if unsupported:
            for u in unsupported[:3]:
                print(f"    未支持命题示例: index={u.get('index')}, text={u.get('text')}, note={u.get('note')}")

        print(f"\n[4] 引用来源数: {len(sources)}")
        for s in sources[:3]:
            print(f"  Source: id={s.get('id')}, title={s.get('title')}, doc_id={s.get('document_id')}")

        results[cid] = {
            "tasks": tasks,
            "answer_len": len(answer),
            "answer_preview": answer[:120],
            "claims_count": len(claims),
            "supported_count": len(supported),
            "unsupported_count": len(unsupported),
            "sources_count": len(sources)
        }

    print("\n\n################ 测试总结 ################")
    print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    run_test()
