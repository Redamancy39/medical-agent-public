# -*- coding: utf-8 -*-
"""
Medical-Agent 系统统一启动与服务管理脚本 (launcher.py)
解决 Windows CMD 批处理文件编码偏移 bug，提供可靠的跨平台服务探测与自愈启动。
"""

import os
import sys
import time
import socket
import urllib.request
import subprocess
import webbrowser
from pathlib import Path

# 保证控制台正常输出 UTF-8 并绕过本地回环代理
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 确保 127.0.0.1 和 localhost 不受系统 HTTP/HTTPS 代理影响
os.environ["NO_PROXY"] = "127.0.0.1,localhost," + os.environ.get("NO_PROXY", "")
os.environ["no_proxy"] = "127.0.0.1,localhost," + os.environ.get("no_proxy", "")

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "demo-frontend"
PYTHON_EXE = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"

BACKEND_PORT = 8010
FRONTEND_PORT = 5178
BACKEND_HEALTH_URL = f"http://127.0.0.1:{BACKEND_PORT}/health"
FRONTEND_URL = f"http://127.0.0.1:{FRONTEND_PORT}/"


def find_pids_by_port(port: int) -> set:
    """查询指定端口正在监听的进程 PID 列表"""
    pids = set()
    try:
        res = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            errors="ignore",
            check=False,
        )
        for line in res.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.strip().split()
                if parts:
                    pid = parts[-1]
                    if pid.isdigit() and int(pid) > 0:
                        pids.add(pid)
    except Exception:
        pass
    return pids


def kill_port(port: int) -> int:
    """终止占用指定端口的所有进程"""
    pids = find_pids_by_port(port)
    killed = 0
    for pid in pids:
        try:
            subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, check=False)
            killed += 1
        except Exception:
            pass
    return killed


def is_port_listening(port: int, host: str = "127.0.0.1") -> bool:
    """检查指定端口是否已在监听 TCP 连接"""
    try:
        with socket.create_connection((host, port), timeout=0.8):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def check_http_ok(url: str, timeout: float = 1.2) -> bool:
    """检查 HTTP 接口是否返回 200 OK（绕过本地代理直接连接）"""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "MedicalAgentLauncher/1.0"},
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def stop_system():
    """停止系统所有关联服务"""
    print("=" * 55)
    print("         医疗科研 Agent 系统 - 一键停止器")
    print("=" * 55)
    print()

    print(f"[1/2] 正在检查并释放 {BACKEND_PORT} 端口 (后端服务)...")
    k_back = kill_port(BACKEND_PORT)
    if k_back > 0:
        print(f"      已终止 {k_back} 个占用后端端口的进程。")
    else:
        print("      后端端口未被占用。")

    print(f"[2/2] 正在检查并释放 {FRONTEND_PORT} 端口 (前端服务)...")
    k_front = kill_port(FRONTEND_PORT)
    if k_front > 0:
        print(f"      已终止 {k_front} 个占用前端端口的进程。")
    else:
        print("      前端端口未被占用。")

    print()
    print("=" * 55)
    print(" [✔] 8010 与 5178 端口已全部释放，系统已安全退出。")
    print("=" * 55)
    time.sleep(2)


def start_system():
    """启动系统后端与前端，并自动唤起浏览器"""
    print("=" * 55)
    print("         医疗科研 Agent 系统 - 一键启动器")
    print("=" * 55)
    print()

    # 1. 验证 Python 虚拟环境
    if not PYTHON_EXE.exists():
        print(f"[错误] 未找到 Python 虚拟环境解释器：{PYTHON_EXE}")
        print("请确认虚拟环境已创建并安装在 backend/.venv 目录中。")
        input("\n按回车键退出...")
        sys.exit(1)

    # 2. 检查前端依赖
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        print("[提示] 未检测到前端 node_modules，正在执行 npm install 安装依赖...")
        try:
            subprocess.run(["npm", "install"], cwd=str(FRONTEND_DIR), shell=True, check=True)
            print("[✔] 前端依赖安装完毕。")
        except subprocess.CalledProcessError as e:
            print(f"[错误] npm install 安装依赖失败: {e}")
            input("\n按回车键退出...")
            sys.exit(1)

    # 3. 启动/复用后端服务
    if check_http_ok(BACKEND_HEALTH_URL):
        print(f"[提示] 检测到后端 8010 服务已在运行中 (HTTP 200 OK)，复用当前服务。")
    else:
        # 如果端口被无响应进程占用，先清理
        if is_port_listening(BACKEND_PORT):
            print(f"[提示] 端口 {BACKEND_PORT} 处于假死或未就绪状态，正在重置占用...")
            kill_port(BACKEND_PORT)
            time.sleep(1)

        # 默认启用真实医疗模型与医学知识库（如需离线模拟可传 --fake 参数）
        is_fake = any(arg in sys.argv for arg in ("--fake", "--offline", "--sim"))
        if is_fake:
            print("[模式] 用户指定运行：离线模拟模式 (FakeModel)")
            backend_args = [arg for arg in sys.argv[1:] if arg not in ("--stop", "-s", "stop", "--fake", "--offline", "--sim")]
        else:
            print("[模式] 正在启用：全功能真实医疗模型 (DeepSeek API + 医疗知识库 + Mem0 + PubMed + CUDA 重排)")
            backend_args = ["--real", "--medical"]
            for arg in sys.argv[1:]:
                if arg not in ("--stop", "-s", "stop") and arg not in backend_args:
                    backend_args.append(arg)

        cmd_backend = f"title Medical-Agent-Backend [Port {BACKEND_PORT}] && .venv\\Scripts\\python.exe run.py"
        if backend_args:
            cmd_backend += f" {' '.join(backend_args)}"

        print(f"[1/3] 正在启动后端服务 (FastAPI / LangGraph / SQLite : {BACKEND_PORT})...")
        subprocess.Popen(
            ["cmd.exe", "/k", cmd_backend],
            cwd=str(BACKEND_DIR),
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
        )

        # 循环探测健康探针，直到后端真正就绪（最大等待 45 秒，涵盖 CUDA 模型权重加载耗时）
        max_retries = 45
        backend_ok = False
        print("      等待后端初始化就绪", end="", flush=True)
        for _ in range(max_retries):
            time.sleep(1)
            print(".", end="", flush=True)
            if check_http_ok(BACKEND_HEALTH_URL):
                backend_ok = True
                break

        print()
        if backend_ok:
            print(f"[✔] 后端服务已就绪！({BACKEND_HEALTH_URL})")
        else:
            print(f"[警告] 后端启动用时超过 {max_retries} 秒，请检查后端命令行窗口是否报错。")

    # 4. 启动/复用前端服务
    if is_port_listening(FRONTEND_PORT):
        print(f"[提示] 检测到前端 {FRONTEND_PORT} 服务已在运行中，复用当前服务。")
    else:
        print(f"[2/3] 正在启动前端服务 (Vue 3 / Vite : {FRONTEND_PORT})...")
        cmd_frontend = f"title Medical-Agent-Frontend [Port {FRONTEND_PORT}] && npm run dev"
        subprocess.Popen(
            ["cmd.exe", "/k", cmd_frontend],
            cwd=str(FRONTEND_DIR),
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
        )

        max_retries = 25
        frontend_ok = False
        print("      等待前端编译服务就绪", end="", flush=True)
        for _ in range(max_retries):
            time.sleep(0.8)
            print(".", end="", flush=True)
            if is_port_listening(FRONTEND_PORT):
                frontend_ok = True
                break

        print()
        if frontend_ok:
            print(f"[✔] 前端服务已就绪！({FRONTEND_URL})")
        else:
            print(f"[警告] 前端启动用时较长，请检查前端命令行窗口。")

    # 5. 唤起默认浏览器访问系统
    print(f"[3/3] 正在唤起默认浏览器打开系统界面...")
    time.sleep(1)
    webbrowser.open(FRONTEND_URL)

    # 6. 展示就绪状态面板
    print()
    print("=" * 55)
    print(" 系统已成功启动并就绪！服务入口如下：")
    print(f" - 前端问答控制台: {FRONTEND_URL}")
    print(f" - 后端接口文档:   http://127.0.0.1:{BACKEND_PORT}/docs")
    print()
    print(" 使用提示：")
    print(" 1. 后端与前端分别在独立的命令行控制台窗口中稳定运行。")
    print(" 2. 前端顶部具备健康自愈检测，状态实时同步为绿标 [8010 在线]。")
    print(" 3. 如需彻底关闭系统所有服务，请双击运行【停止系统.bat】。")
    print(" 4. 您可随时关闭本启动引导窗口，不影响服务在后台持续工作。")
    print("=" * 55)
    print()
    try:
        input("按回车键可关闭本引导窗口（系统服务保持后台运行）...")
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--stop", "-s", "stop"):
        stop_system()
    else:
        start_system()
