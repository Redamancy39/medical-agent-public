"""专门针对此前 7 例降级用例进行工程平滑有效性验证的测试脚本"""
import json
import os
import sys
import time
import uuid
from pathlib import Path

# 添加项目根目录到 Python 路径
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.app.config import load_settings
from backend.app.main import create_app
from backend.scripts.eval.run_ablation_baseline import call_ours

TARGET_CIDS = ["GDL-06", "GDL-10", "BND-01", "BND-03", "BND-06", "DUAL-05", "DUAL-06"]

def main():
    print("=" * 70)
    print("  启动 7 例工程平滑针对性验证")
    print(f"  测试目标: {TARGET_CIDS}")
    print("=" * 70)

    with open(ROOT / "backend/evaluation/test_cases_v2.json", "r", encoding="utf-8") as f:
        all_cases = json.load(f)
    case_map = {c["id"]: c for c in all_cases}

    settings = load_settings()
    app = create_app(settings)

    with TestClient(app) as client:
        reg_body = {"username": f"smooth_eval_{uuid.uuid4().hex[:6]}", "password": "EvalPassword123!"}
        client.post("/auth/register", json=reg_body)
        login_res = client.post("/auth/login", json=reg_body)
        headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

        success_count = 0
        for idx, cid in enumerate(TARGET_CIDS, 1):
            case = case_map[cid]
            q = case["question"]
            cat = case["category"]
            print(f"\n[{idx}/{len(TARGET_CIDS)}] 正在验证用例 {cid} [{cat}] ...")
            print(f"  问题: {q[:60]}...")

            t0 = time.time()
            try:
                res = call_ours(client, headers, q)
                ans = res.get("answer", "")
                ans_len = len(ans)
                rd = res.get("run_data") or {}
                safe_err = rd.get("safe_error_code")
                srcs_count = len(res.get("sources", []))

                is_fallback = "本轮逐项引用审核未完成" in ans or "本轮未完成" in ans or ans_len <= 50

                print(f"  -> 生成耗时: {time.time()-t0:.2f}s | 回答长度: {ans_len} 字 | 命中证据: {srcs_count} 篇")
                print(f"  -> safe_error_code: {safe_err}")
                print(f"  -> 回答摘要: {ans[:80]}...")

                if is_fallback:
                    print(f"  [FAIL] 仍触发了降级或短文本兜底！")
                else:
                    print(f"  [SUCCESS] 成功生成完整高水准回答！")
                    success_count += 1
            except Exception as e:
                print(f"  [ERROR] 执行异常: {e}")

        print("\n" + "=" * 70)
        print(f"  验证总结: 成功 {success_count}/{len(TARGET_CIDS)} 例")
        print("=" * 70)

if __name__ == "__main__":
    main()
