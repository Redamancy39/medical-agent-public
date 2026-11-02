# 医疗科研 Agent 独立后端

2026-10-15批次Q：检索短引句与完整原文上下文已对齐，明确字数限制的证据修复/精简共享一次有界改写并独立复审，失败保留已审核正文。246项离线回归通过；最新真实三任务HTTP22.62秒，正文141/180字符（固定提示另计），仍省略1条无证据的“互补/不可替代”扩展、状态partial。前端源码和冻结题集未改。**无管理员角色或默认管理员账号**，前端“后端联调”可注册自己的普通账号；当前交接进程保留此前联调SQL库，不是默认data/app.db。启动入口、所有失败与调用成本见[批次Q验收及登录步骤](../docs/批次Q范围声明与长度合并验收.md)。

2026-10-15批次P：引用改写保护、上下文精简与GPU重排已落地，最终229项后端回归和pip check通过。RTX5060重排同5候选中位CPU2.680秒/GPU0.02911秒，health实际cuda。最新同题多Agent HTTP23.67秒，核心回答恢复，仍partial（省略1条范围声明、正文183>180）；所有失败与成本边界见[批次P验收](../docs/批次P引用保护与GPU重排验收.md)。冻结题集未运行、哈希不变，前端源文件未改。

2026-10-14批次L：实时`review_answer`已接单Worker与多任务汇总出口，原文快照证据、完整覆盖、保守删减与审核失败降级入SQL；缺引用补查保留检索资料并提供evidence_diagnostics。187项回归通过，剩余10道dev真实观察完成（3完整、7部分，Reviewer10/10完成）；dev20要点覆盖已核对，临床准确率null。本批52次新HTTP、324,128 tokens包含两道专项复验，不能算成12个独立题。Dot新正文18份/17来源族、60项建议与10候选题已接收，均不入正式库。详见[批次L验收](../docs/批次L实时Reviewer与开发集续评验收.md)。前端/冻结测试集/用户.env/原演示进程保持不动。

Reviewer仅在medical profile与真实DeepSeek模式启用（独立Fake测试可注入review）；可用MEDICAL_REVIEWER_ENABLED控制，默认true，Reviewer输出上限REVIEWER_MAX_TOKENS默认1400，Worker仍768。审核与一次格式修复占原全局预算，状态completed不代表医学审核认证；支持不足返回partial。最终主答复不返回未审核医学原稿，受控run详情保留省略段与原因用于审查。

2026-10-14批次K：新增独立逐项引用审查工具，dev20/60条参考要点及首批10题/63项答案来源审查已记录，临床复核not_run；本批新6题真实观察5完成/1失败（38次HTTP、104,270 tokens）。紧急风险新增规则快速出口，跳过外部上下文/Agent并标记response_origin=urgent_policy；澄清恢复也复查。最终178项后端回归通过。完整限制及待补功能见[批次K验收](../docs/批次K逐项引用与开发集质量验收.md)；新提示词与安全出口改动后尚未追加真实模型验收。前端和原演示进程暂不调整。

2026-10-14批次J：Lead规划/汇总原生结构化提交、安全诊断和有界格式修复已完成，161项后端离线测试通过；原4道dev真实自动路由4/4完成（17次HTTP、50,412 tokens），医学质量待复核。Dot新增7条来源元数据已接收，正文0份、逐点审查JSON 0条；正式Milvus20份/40片段，TXT候选4份/38片段。前端暂不调整，原演示服务未重启。详见[批次J验收](../docs/批次J规划汇总修复与资料接收验收.md)。以下A–I数字保留各批历史边界。

批次 A–G 已实现：查询、记忆维护、独立SQL模拟登记分支与单/多Agent配对评测。默认配置offline_fake；真实provider需显式启用。D/E/F的15个真实场景为历史验收；G当前结果与限制见 [批次G验收记录](../docs/批次G验收记录.md)。

## 启动

本机已建立独立 .venv 并安装依赖，在 PowerShell 执行：

```powershell
Set-Location 'E:\medical agent\backend'
.\.venv\Scripts\python.exe run.py
```

服务绑定 http://127.0.0.1:8010，接口文档为 http://127.0.0.1:8010/docs，健康检查为 /health。只使用一个本地服务进程。结束后用 Ctrl+C；再启动使用相同数据库和签名密钥，旧会话和未过期登录凭证仍可使用。

新环境安装（Python 3.12 已验收）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

没有 .env 的新环境才从 .env.example 复制；已有文件不可覆盖。requirements.txt 是运行依赖，requirements-dev.txt 是直接测试依赖，requirements-lock.txt 固定本次已验收的完整环境。

本机 RTX 5060 的 GPU 环境使用独立锁文件（CUDA 12.8 PyTorch；不修改显卡驱动）：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-gpu-lock.txt
```

已有 CPU 环境仅切换 PyTorch 可安装 `requirements-gpu.txt`。原 `requirements-lock.txt` 保留 CPU 基线。`RERANKER_DEVICE=auto` 优先 CUDA，无法使用时回退 CPU；`cpu` 强制 CPU，`cuda` 则在不可用时明确启动失败。GPU 重排使用 FP16、CPU 使用 FP32，模型与所有输入张量使用同一设备；`/health` 的 `providers.reranker_device` 返回实际设备。首次启动和预热不等于稳定推理耗时，必须分别测量；不自动下载模型权重。

## 在接口文档中操作

1. POST /auth/register：用自行选择的合成用户名和密码注册本地账号；密码至少8个字符。
2. POST /auth/login：使用同一账号登录，取得 access_token。
3. 点击文档页面的 Authorize，填写 access_token 本身；请求会以 Bearer 方式携带。
4. POST /sessions：创建会话，记录返回的 id。
5. POST /sessions/{session_id}/chat：提交 question 和 request_id。该 UUID 是本次请求的幂等标识，重试同一次请求保持不变；新问题使用新 UUID。
6. GET /sessions/{session_id}/messages：读取有序历史；重启后继续使用同一个 session_id。

默认模拟回答明确显示“离线模拟”；真实模式使用DeepSeek而不会静默改成fake回答。本地注册入口面向本机学习；企业认证在后续适配。

| 接口 | 用途 |
|---|---|
| GET /health | 服务、数据库和当前模式 |
| POST /auth/register、POST /auth/login、GET /auth/me | 本地账号、短期 JWT 和当前用户 |
| POST /sessions、GET /sessions | 创建会话、分页列出自己的会话 |
| GET /sessions/{session_id} | 自己的会话元数据 |
| GET /sessions/{session_id}/messages | 按 seq 读取消息；after_seq 和 limit 控制分页 |
| POST /sessions/{session_id}/chat | 按当前模式处理、保存用户输入和最终回复 |
| GET /runs/{run_id} | 已持久化的运行状态和结果 |
| GET /sessions/{session_id}/runs、GET /runs/{run_id}/events | 运行列表和安全节点事件 |
| POST /runs/{run_id}/resume、POST /runs/{run_id}/cancel | 恢复等待/暂停运行、取消当前运行 |
| GET /runs/{run_id}/providers | 本轮真实HTTP尝试、安全错误和token记录 |
| GET /sessions/{session_id}/summary | 本人会话摘要、版本和覆盖区间 |
| GET /memories、POST /memories/{fact_id} | 本人记忆列表、纠正/撤回；更新已撤回条目可显式恢复 |
| GET /maintenance/jobs、POST /maintenance/retry | 本人后台任务状态与有界重试 |

JWT 默认15分钟，固定HS256，验证issuer、audience、签名和必要时效字段；过期重新登录。每次查当前用户是否启用，并检查资源所有权；跨用户资源请求返回404。

同一用户重复提交相同request_id和相同会话/问题，返回原run_id，replayed=true，不新增消息；相同键用于不同内容返回409。省略request_id会自动生成；客户端需要可靠重试时应自行提供并保留。

## 配置与数据

backend/.env 已有 DEEPSEEK_API_KEY、MEM0_API_KEY 保留。JWT_SECRET 首次为空时由程序本地生成并写回，后续不覆盖。密钥和完整配置不输出；公开示例在 .env.example。

当前.env的外部开关保留false；可以通过配置分别启用provider，或使用下方显式真实入口。数据库默认 backend/data/app.db，相对路径以backend目录解析，使用SQLite WAL。密码仅存Argon2哈希；数据库、虚拟环境、.env和缓存已忽略；原参考数据库未打开或修改。

用户消息按递增seq保存，内部事件单独保存；完整历史保留，模型上下文取最近10轮与有效旧摘要。第11轮完成后，退出窗口的消息进入后台增量摘要。记忆纠正/撤回使相关旧摘要失效，模型过滤过时偏好，SQL原文保留。维护失败不丢回答；状态与重试单独提供。新增表保留升级前数据，不用删库替代迁移。

输入保存、计数更新和结果保存各自使用短事务；模型/工具循环在事务之外，由LangGraph执行。检查点在同目录checkpoints.db，按每次运行隔离；同会话顺序执行，跨实例通过运行租约保护。暂停运行恢复需使用最新checkpoint_id，详见批次B记录。

## 验证

当前批次J离线回归161/161；新增10项Lead契约测试验证格式修复上限、全局预算、鉴权不重试、汇总精确覆盖和原生工具提交。`schema_repair_limit=1`表示plan、synthesize各最多一次，全体Worker另共享一次，所有调用仍占原模型/HTTP预算；默认0关闭修复，真实入口使用1。`RunOut`新增`contract_repair_counts`及脱敏`contract_diagnostics`；重复规划失败返回failed，重复汇总失败保留Worker结果并返回partial。真实4题未触发修复，不能将受控故障测试称为真实故障观察。

```powershell
.\test.ps1
.\.venv\Scripts\python.exe scripts\smoke.py
```

test.ps1 为每次测试在工作区tmp内选择独立目录，绕开本机不可写的系统临时目录。测试不读用户.env，不接云服务。smoke.py 需先启动服务；通过真实本机HTTP创建合成账号和验收会话，只输出通过状态，不输出密码或JWT。

当前已验收：123项后端离线测试、5项前端测试通过；G最终真实配对单/多各3/3，正常HTTP与登记20项检查通过。本机Vue3登记联调通过，旧SQL与参考文件保持一致。详见 [批次G验收记录](../docs/批次G验收记录.md)；A–F数字保留为历史证据。

前端运行npm run dev后，在5178点击“后端联调”，登录本地账号并创建/选择会话。通常可测试“你好”“检索研究项目资料”“请澄清我的请求”；最后一种会等待补充，也可取消。JWT不存浏览器localStorage，刷新后重新登录即可加载SQL历史。

完整设计见 [完整修改计划](../docs/完整修改计划.md)。原合成流程库保留，新增独立医学库见下文；网络仍只读取PubMed索引元数据，医学答案质量与专业复核尚未完成。真实登记Service、企业认证和部署另按实际需求实施。

## 医学知识库与60题评测（H1–H3）

20份NLM/MedlinePlus来源、40个章节片段，限定美国成人高血压与2型糖尿病健康教育；中文为Codex编辑摘述，非官方译文、未专业复核。独立`data/knowledge_medical_v1.db`，保留原`knowledge_v3.db`。资料契约见[知识库说明](knowledge/medical/README.md)，60题开发/测试分割和评分契约见[评测集说明](evaluation/medical-v1/README.md)。

```powershell
.\.venv\Scripts\python.exe scripts\prepare_medical_knowledge.py --check-only
.\.venv\Scripts\python.exe scripts\prepare_medical_knowledge.py --rerank
.\.venv\Scripts\python.exe scripts\evaluate_medical.py --validate-only
# 20题开发集的本地检索，默认不调用云服务。
.\.venv\Scripts\python.exe scripts\evaluate_medical.py
# 4题真实Lead观察，独立SQL/KB，关闭Mem0、联网和维护写入。
.\.venv\Scripts\python.exe scripts\evaluate_medical.py --run-real --limit 4
# 医学入口；默认仍是假模型，只验证工具链。
.\.venv\Scripts\python.exe run.py --medical
# 显式启用真实完整链路；需先停止占用8010的旧服务。
.\.venv\Scripts\python.exe run.py --real --medical
```

`--medical`仅本进程选库和提示，不改写.env；也可在配置中指定`KNOWLEDGE_PROFILE=medical`并启用知识库。默认知识库路径自动切到医学库，自定义路径则由调用者明确提供。`/health`和RunOut返回knowledge_profile；计划返回plan_reason、task_count和planned_agent_count，理由缺失时为null，不由程序虚构。

医学入口所有问题先到Lead，由模型选择必要任务；同一知识解释通常单任务，需要独立证据/依赖时可以拆分。评测不强制单/多Agent，也不把题目答案传给模型。旧G固定拓扑脚本保留作历史流程消融，不代表当前Lead选择。前端本批未修改，40题保留测试未运行医学回答，完整质量验收留到H4。

## TXT候选入库与Dot资料协作

医学TXT与Dot数据协作（2026-10-14）：新增[TXT候选入库](knowledge/medical-local/README.md)和[Dot JSON交付接口](knowledge/medical-handoff/README.md)，详见[批次I验收](../docs/批次I资料入库与Dot协作验收.md)。4份原TXT/38片段仅为候选，未接入默认问答或正式医学库；150项后端回归通过。Dot数据只存建议，test40暂停，无新云模型调用。

## 批次G模拟登记与配对评测

在“后端联调”中登录并选择会话，点击“打开服务端模拟登记”。输入合成内容后生成草稿，补字段并保存编辑，再“核对当前版本”并勾选确认，最后“明确确认模拟登记”。取消不会新增记录；编辑使旧确认失效。SQL业务数据与原浏览器localStorage演示分别展示。详见 [端到端演示指南](../docs/端到端演示指南.md)。

查询主图仍为v3。登记使用独立registration_graph_v1提取/校验，SQL保存待补充/待确认状态，Service短事务执行确认/取消，无模型可写业务工具。项目DEMO-A/B、类型组织/血液/唾液、区域DEMO-B/C、数量1–20；输入提取采用有界规则，歧义保留空字段，不声称是通用LLM提取。确认记录和幂等回执同事务提交，写入结果不明先读草稿或重放原request_id。

新增接口：`GET /registration-options`；`POST/GET /sessions/{id}/registration-drafts`；`GET /registration-drafts/{id}`和`/audit`；`POST /registration-drafts/{id}/edit|review|confirm|cancel`；`GET /registration-records`。所有资源由JWT与当前SQL用户、会话所有权校验。

```powershell
# 默认离线的3题×2种固定拓扑评测，独立tmp数据库，不读.env。
.\.venv\Scripts\python.exe scripts\evaluate.py --local-tools-only
# 本机HTTP验收。真实服务的Agent观察需另加 --real-agents。
.\.venv\Scripts\python.exe scripts\g_smoke.py --run
# 只有显式执行才使用DeepSeek；最多36次HTTP，无Mem0/网络工具。
.\.venv\Scripts\python.exe scripts\evaluate.py --run-real --local-tools-only
```

配对评测固定同题、独立会话、相同每轮预算与工具范围；固定计划消耗一个规划预算尝试但不调用模型，不测试Lead路由质量。正常HTTP另验收实际Lead单/多任务。报告记录来源契约、真实HTTP/token、延迟、关键词覆盖与失败；关键词出现不等于语义正确或医学证据支持，3题也不足以得出多Agent更优的结论。

## 显式启动真实完整链路

本机Embedding已准备，reranker复用用户已有目录 `D:\rag_project\models\reranker\bge-reranker-v2-m3`，启动仅从本地加载，不重新下载权重。

```powershell
# 独立知识库导入；新环境需下载Embedding时才加 --download-model。
.\.venv\Scripts\python.exe scripts\prepare_knowledge.py --rerank
# 暂停已有8010服务后启动；本次进程覆盖配置，不写回.env。
.\.venv\Scripts\python.exe run.py --real
```

真实进程总上限：DeepSeek40、Mem060、PubMed8次HTTP；单轮模型16/工具5，多任务Worker模型4/工具2/迭代4，全轮90秒。摘要也消耗真实模型请求；实际尝试和token看provider记录。达到上限返回明确错误，需要重新启动才开启新的进程预算，不自动升级额度。该模式会发送合成问题与筛选偏好到对应服务。

`scripts/full_flow_live.py --run` 是独立真实验收入口，创建合成用户并清理自己的云记忆；不作为普通回归自动执行。`scripts/smoke.py` 只用于默认离线服务。15场景成功测试实际消耗DeepSeek34/Mem022/PubMed4次请求，前期失败尝试与额外核对另见验收记录，不等于账户余额或医学正确率。

## 批次 C 与独立真实冒烟

批次C历史联调输入“三个专家研究样本登记”，可查看3个任务/3个角色与依赖。当前主图v3检查点按任务波保存；任务终态先写SQL，完成任务恢复时跳过；未完成的只读Worker可能重跑，但仍扣除已消耗预算。旧v1/v2暂停检查点拒绝跨版本恢复，旧结束历史保留。真实模式调用次数由模型选择和实际预算决定，不沿用fake固定次数。

显式真实测试（不由应用或pytest自动调用）：

```powershell
.\.venv\Scripts\python.exe scripts\provider_smoke.py --run
```

可用 `--provider ds` 或 `--provider mem0` 单独验收；省略 `--run` 不联网。每次上限DS 3个请求、每个最多512输出token，Mem0 5个请求且仅1条新合成偏好原文。脚本记录安全状态与实际token，精确清理自己创建的记忆；不查询真实用户数据、不升级套餐。Mem0事实提取未验收。

完整范围、恢复边界与本次结果见 [批次C验收记录](../docs/批次C验收记录.md)。

## 当前医学问答后端（M批）

医学最终原稿经原子事实拆分、每批最多10条Reviewer首审，必要时一次证据约束改写和复审，再保存。多任务汇总共用同一出口；所有调用扣原模型/HTTP/时间预算，未审改写不返回。运行详情提供两轮审核、改写计数及分批进度，前端暂未更新。

197项离线回归通过；最终同版本6题4 completed/2 partial、Reviewer5/6完成。comparison-06核心恢复，basic-16误删与basic-07分类阻断仍待改进，不能称完整dev20或医学评测通过。见[批次M验收](../docs/批次M原子事实与改写复审验收.md)及[evaluation/medical-quality-v3](evaluation/medical-quality-v3/README.md)。

Dot最终资料已候选区接收，100目标适格来源族另2隔离；60候选题结构与quote/hash/policy绑定通过，未专业审查、未准入正式库。`scripts/verify_dot_delivery.py`仅验证交付并幂等暂存metadata；需requirements-dev/lock中的jsonschema，不调用模型。

## 审核溯源与校准（N批，2026-10-15）

运行详情新增本人可见的review_trace：审核输入原子稿/原句位置/原文证据、程序期望类别、轮次与批次、格式修复前后类型合法判定和安全错误索引。未知ID只计数，任意provider响应、headers与错误原文不保存；其他用户仍404，未审稿不作为最终answer。

206项离线回归通过；basic-07分类阻断与basic-16三处核心误删的目标复验均completed。另两道相邻题仍partial，18条受控正反校准全部通过，但不代表医学正确率或全开发集已通过。详见[批次N验收](../docs/批次N审核溯源与分类校准验收.md)与[evaluation/medical-quality-v4](evaluation/medical-quality-v4/README.md)。前端与冻结题集不改，旧演示服务未自动重启。

## 改写保留与完整开发集观察（O批，2026-10-15）

改写未覆盖的原事实保留原审核判定和引用；未支持内容仍省略，不能通过删去记录变成completed。两轮合并记录标明实际审核轮次/index；外部每轮40条、每批10条，内部已验证两轮合并最多80条。

最终213项后端离线回归通过（48.12秒），3个新增受控缺陷均先复现失败再修复。

显式完整开发集入口：`scripts/evaluate_medical.py --run-real --pilot-only --full-dev --model-budget 16`，20题各一次、两题一批、独立SQL和40次HTTP批次上限，并校验运行中代码hash。真实20题已执行，但18题受HTTP 503等上游错误阻断；2个completed是程序安全出口，不代表医学问答通过。最后的内部合并边界修复仅离线验证，最终同版本真实质量复验待provider恢复。

本地完整检索16个适用题Top-5命中100%、平均引用片段覆盖94.79%，并非回答准确率。24条技术校准最后只完成10条，类别9/10；不能沿用N批18/18描述当前全部通过。前端、冻结题集和正式库不改。详见[批次O记录](../docs/批次O审核保留与完整开发集观察.md)及[evaluation/medical-quality-v5](evaluation/medical-quality-v5/README.md)。
