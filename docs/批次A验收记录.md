# 批次 A：后端基础、JWT 与 SQL 会话持久化

日期：2026-10-13；状态：已实现并完成本地验收。范围限独立 backend，现有 Vue3 仍使用演示数据。

## 已交付

| 模块 | 实际行为 | 位置 |
|---|---|---|
| 应用与配置 | FastAPI、本地8010启动、明确后端路径、SecretStr隔离密钥、外部开关拒绝启用 | backend/app/main.py、config.py、run.py |
| 鉴权 | 本地注册/登录、Argon2哈希、15分钟HS256 JWT、签名/算法/时效/issuer/audience校验、禁用用户拒绝 | backend/app/security.py、schemas.py |
| 持久化 | SQLite WAL、用户/会话/消息/运行/事件表、所有权、顺序编号、分页历史 | backend/app/database.py、models.py |
| 请求处理 | 明确模拟模型、同用户request_id唯一、重复返回原结果、不同内容同键冲突、失败结果保存 | backend/app/service.py |
| 错误边界 | 安全错误码、字段验证不返回原输入、数据库参数隐藏、未预期异常不传到服务器栈日志 | backend/app/main.py |
| 复现环境 | 独立.venv、直接依赖及完整lock、工作区测试脚本、本机HTTP验收脚本 | backend/requirements*.txt、test.ps1、scripts/smoke.py |

启动时应用读取已有API配置，但未将密钥通过工具打印或用于云调用。JWT_SECRET从空值本地生成并保存，重启沿用；配置保留行为用合成密钥单独测试。

## 验证结果

- 确定性离线测试：passed=23，failed=0，skipped=0。
- 正常登录、重复注册/用户名归一化、哈希保存；过期/错误签名/错误算法/错误audience/缺失exp/篡改token和禁用用户均拒绝。
- 跨用户会话/运行/历史访问和客户端伪造user_id均拒绝；空白/超长问题零写入。
- 同请求串行/并发重试仅保存一轮，不同内容同键409；不同请求并发顺序正确，分页游标正确。
- 关闭并重新创建应用后，历史和未过期token继续可用；这验证数据库重开，不代表实现LangGraph checkpoint恢复。
- 模型失败持久failed；数据库写入失败回滚；异常不泄露；密码空格保留；外部开关不静默启用。
- 合成.env密钥保留、JWT密钥生成后复用、Settings表示不泄露；测试使用临时数据库和合成配置。
- 真实本机HTTP冒烟：登录、建会话、提交/重试、历史、运行、第二用户隔离和OpenAPI均通过；脚本不输出密码/JWT。
- pip check：No broken requirements found。
- 有一条测试客户端httpx弃用提醒；锁定环境可运行，后续客户端升级单独处理，未屏蔽警告。

两个关键边界先有失败测试，再修复并通过：密码前后空格被通用输入设置裁剪；未预期异常在安全响应后仍向ASGI外传播。已分别修正。

Windows沙箱初次阻止系统临时目录访问和asyncio本机socketpair；测试数据改放工作区，测试在允许本机socket的环境完成。依赖下载为开源Python包安装，不是模型/Mem0调用；挂起的两个本轮诊断进程已按独立虚拟环境和特有命令匹配终止。

## 来源与边界

实现参考 [FastAPI官方JWT/密码哈希说明](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) 与 [SQLAlchemy Session事务说明](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)。本地认证选择与状态契约属于本工程设计，未进行完整安全审计。

对首次审查基线的153个参考源码/文档/结构配置文件做SHA-256比较：变化0、缺失0（排除私有config.py、.env和缓存）。AgentLoop、Coordinator、SessionSummary、test_all四个代表文件指纹也一致。未执行原脚本、读取顶层私有config、打开原Milvus库或连接业务系统。

DeepSeek/Mem0请求为0。LangGraph、10轮上下文/摘要、长期记忆维护、真实检索、取消/checkpoint恢复和Vue3后端接入均待后续实施。本地HTTP测试生成隔离的合成账号和验收会话；用户自行注册学习账号，其他人的测试会话不会显示在其列表。

运行方式和接口步骤见 [backend README](../backend/README.md)。下一批按 [实施路线](实施路线.md) 实现单Agent LangGraph链路。
