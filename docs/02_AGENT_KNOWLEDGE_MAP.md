# 阶段 B：Agent 工程知识地图与学习指南

日期：2026-10-13（Asia/Shanghai）。配套证据见 [01_SOURCE_AUDIT.md](01_SOURCE_AUDIT.md)。本文只做技术解释与下一步学习建议，不构成企业需求、MVP 实现或医疗规范。

## 1. 从现有经验到 Agent

你已经熟悉 FastAPI、SQLAlchemy、RAG 和工作流。Agent 额外引入的是“模型根据当前上下文选择下一步动作”，程序仍负责动作是否合法、如何执行、如何记录失败。

参考项目的核心模式是：

```text
用户消息 + 历史 + 工具描述
  → 模型返回 tool_calls 或文本
  → 程序解析调用名与参数
  → 注册表执行 Python 函数
  → 结果作为 role=tool 消息返回模型
  → 再决策，直到退出
```

模型选择动作并不等于模型有执行权限；返回合法 JSON 不等于业务语义正确；工具成功也不等于整个任务完成。后续医疗科研信息管理假设中，模型可建议“登记草稿”，业务 Service 才能决定是否写入。

全文例子使用虚构项目 `DEMO-A`、区域 `DEMO-B`、样本 `SYN-001`，只是帮助理解工程机制，未运行、未实现，不能视为医疗规则。

## 2. 三种 Skill 概念必须分开

| 概念 | 本项目证据 | 如何理解 |
|---|---|---|
| Python Function Calling 工具 | `E:/medical agent/medix-agent-swarm/core/skill_registry.py:110 to_openai_format()` 和 `:64 execute()` | 把 Python 函数描述为模型可选择的接口，程序执行实际函数；模型不会直接运行 Python 源码 |
| 项目内部 Skills 封装 | `core/skill_loader.py:81 discover_skills()`、`.claude/skills/*/script/` | 作者用“目录 + YAML 元数据 + 函数”的结构封装并自动注册工具，这是自己的运行时约定 |
| 开发助手 Agent Skills | 本轮提供的开发助手技能清单；参考目录的 `SKILL.md` 只是格式相近的材料 | 给开发助手的任务说明、资源和工作方式，不是自动获得企业 API 权限的机制；本项目没有因此变成 Codex/Claude Code 运行时 |

特别容易混淆的一点：`parse_skill_md()` 在 `core/skill_loader.py:51` 只取 YAML frontmatter；项目将 description 传给模型，并不会自动把整个 Markdown 正文作为工具工作流执行。目录里写了 `/search-knowledge`，也不能证明 `main.py` 支持这一命令。

案例：内部 skill `search_knowledge(query)` 注册后叫 Function Calling 工具；它的 SKILL.md 用来描述该工具。要让开发助手研究这段代码，则是另一个开发任务，而不是把该检索函数直接授予开发助手。

## 3. 最值得学习的 10 个模块/函数

以下按建议阅读顺序排列。源码相对路径均以 `E:/medical agent/medix-agent-swarm/` 为根。每个模块遵循“问题 → 设计原因 → 调用链 → 潜在问题 → 企业改进”，并附面试追问。

### 1）入口与智能路由：SwarmCoordinator.process

- **解决什么问题**：选择由一个 Worker 处理，还是拆成多个子任务处理。
- **为什么这样设计**：将交互界面与路由分开，Worker 不需要知道用户如何发起请求。
- **调用链**：`main.py:36 interactive_mode()` → `swarm/swarm_coordinator.py:464 process_with_swarm()` → `:85 process()` → Lead → 单 Worker 或 `_process_with_swarm()`。
- **案例**：虚构请求“查询 DEMO-A 的操作说明”若分成一项就走单 Worker；“分别查询说明并校验草稿”可以拆两项，是否拆分仍应由业务需要决定。
- **潜在问题**：当前每轮重建 Coordinator/Worker；单任务也调用 Lead；LLM 解析失败会静默改走 Consultation，业务系统不能由此自动执行写入。
- **企业改进**：业务意图用受控枚举；未知意图返回待澄清；独立管理 request/user/session/run ID；按生命周期复用无状态客户端，运行状态保持隔离。
- **面试追问**：路由失败为什么不能默认写入？客户端复用与 Agent 实例复用有什么区别？

### 2）推理与动作循环：AgentLoop.run

- **解决什么问题**：让模型在拿到工具结果后继续决定下一步，而非一次生成答案。
- **为什么这样设计**：实现通用循环，Agent 子类只提供提示、工具与后处理。
- **调用链**：`agents/base_agent.py:123 run_loop()` → `core/agent_loop.py:56 run()` → `LLMClient.chat_with_tools()` → `execute_tool()` → tool 消息 → 下一轮。
- **案例**：fake 模型第一轮请求 `lookup_demo_project({project_code:"DEMO-A"})`，第二轮读取结果输出草稿。该工具名是教学例子，未在原项目注册。
- **潜在问题**：批内工具数超限、共享计数、无单工具超时；无 tool_calls 就算完成；最后一轮错误可能返回空结果，降级文本也可能标为 completed。
- **企业改进**：运行计数局部化；每个工具执行前检查预算；将模型答复结束与业务任务成功分开；保留 failed/partial/cancelled；写操作重试依赖幂等键。
- **面试追问**：为什么迭代上限不等于请求总数上限？一句“请停止调用工具”算硬限制吗？

### 3）模型协议适配：LLMClient.chat_with_tools / create_tool_message

- **解决什么问题**：统一消息、调用参数和响应对象，减少循环对供应商响应格式的依赖。
- **为什么这样设计**：`ToolCall`、`LLMResponse` 把外部协议转为内部对象。
- **调用链**：`core/llm_client.py:141 chat_with_tools()` → API `chat.completions.create()` → `json.loads(arguments)` → `ToolCall`；`:211 create_tool_message()` 用原调用 ID 返回 JSON 字符串结果。
- **案例**：模型请求 ID 为 `call-demo-1`，工具结果必须关联同一 ID，否则模型消息上下文不能正确对应请求与结果。
- **潜在问题**：JSON 解析不等于字段校验；没有保存 response.usage；`temperature or default` 会吞掉合法的 0；显式 `chat_with_retry()` 不在 Loop 主调用链中。
- **企业改进**：注入可替换客户端；区分 parse/timeout/rate_limit 等错误；记录请求数/token/耗时；使用 `is None` 处理默认值；对可重试错误设预算与退避。
- **面试追问**：模型生成参数错误如何纠正？哪些错误可重试，哪些应直接拒绝？

### 4）工具边界：SkillRegistry.register / execute / to_openai_format

- **解决什么问题**：按名称找到可执行函数，并给模型提供接口描述。
- **为什么这样设计**：集中注册避免各 Agent 手写模型工具格式。
- **调用链**：`core/skill_registry.py:32 register()` → `:110 to_openai_format()` → 模型调用 → `:64 execute()` → async await 或 sync executor。
- **案例**：只注册 `preview_demo_registration` 时，请求 `execute_arbitrary_sql` 返回未注册错误；这仍需验证“已注册但无当前用户权限”的情况。
- **潜在问题**：所有 Worker 注册全套工具；没有运行时 Schema/用户权限；execute 可以返回任意对象；日志直接记录 kwargs。
- **企业改进**：将“名字允许、参数合法、资源可访问、用户已确认”分四层校验；定义统一结果包络；敏感参数脱敏。
- **面试追问**：工具 Schema 交给模型后还需要 Pydantic 吗？未知工具拦截为什么不够？

### 5）动态发现：discover_skills / load_skill_function / _infer_skill_parameters

- **解决什么问题**：新增目录即可发现 Python 工具，减少手工维护。
- **为什么这样设计**：把元数据、函数和文档放在同一目录，方便教学扩展。
- **调用链**：`agents/skill_registry_mixin.py:20 register_all_skills()` → `core/skill_loader.py:81 discover_skills()` → `:51 parse_skill_md()` → `:13 load_skill_function()` → `SkillRegistry.register()`。
- **案例**：目录 `search-history` 映射为函数 `search_history`；Markdown 正文不会替代 Python 实现。
- **潜在问题**：取第一个脚本依赖目录顺序；exec_module 执行顶层代码；参数名启发式把 integer 参数当 number；运行时没有沙箱。
- **企业改进**：备选 A 用显式可信工具清单，简单可审计；备选 B 用经过版本/签名/配置验证的插件发现，扩展更灵活但治理成本更高。初期优先 A，待业务确认后选择。
- **面试追问**：动态 import 有什么副作用？如何保证插件可复现且不扩大权限？

### 6）任务分解与综合：LeadAgent

- **解决什么问题**：把复杂请求分成工作单元，再整合不同结果。
- **为什么这样设计**：让专用 Worker 的循环关注自己输入，Lead 承担分解/总结角色。
- **调用链**：`swarm/lead_agent.py:198 assess_and_decompose()` → `:246 create_subtasks()` → SharedContext；执行后 `:309 synthesize_results()` → 读取 contributions → LLM 总结。
- **案例**：虚构任务可分为“查 DEMO-A 是否存在”“校验 SYN-001 字段”，但两者有依赖时不应无条件并行执行写入。
- **潜在问题**：正则抓 JSON，无 Agent 枚举和数量校验；prompt 要求独立不代表真独立；汇总错误被变成文本；引用贡献内容可能包含不可信指令。
- **企业改进**：对分解结果做结构/语义/权限校验；只允许已定义任务类型；有依赖的步骤用确定性流程控制；最终答案绑定来源与 partial 状态。
- **面试追问**：如何验证任务分解正确？多 Worker 意见冲突时由谁做业务决策？

### 7）共享状态与异步任务：SharedContext / Coordinator 执行方法

- **解决什么问题**：让子任务、状态、贡献和事件有统一可查询位置。
- **为什么这样设计**：内存黑板实现简单，便于演示并行任务返回。
- **调用链**：`shared_context.py:152 add_subtask()` → `:182 start_subtask()` → `swarm_coordinator.py:434 _execute_single_subtask()` → `:206 complete_subtask()` → Lead 读取贡献。
- **案例**：任务 A 返回项目存在、任务 B 返回草稿格式；共享环境记录两份贡献，不应由某个 Worker 把另一份状态任意覆盖。
- **潜在问题**：无持久化/版本/锁；不检查 dependencies；同 Worker 可并发共用 Loop；异常只日志，未更新失败状态；Event 列表不是实时消息订阅。
- **企业改进**：先确保单事件循环状态更新与每次运行隔离；跨进程再采用事务/CAS；显式检查任务所属者、当前状态和唯一完成事件；并发上限由 semaphore/队列执行。
- **面试追问**：asyncio 是否自动让共享字典线程安全？为什么完成操作也需要幂等？

### 8）会话记忆：ShortTermMemory / LongTermMemory

- **解决什么问题**：当前对话的指代与跨会话相关历史检索。
- **为什么这样设计**：短期保留最近消息，长期保存可检索片段，避免每轮塞全部历史。
- **调用链**：`swarm_coordinator.py:110,116` 检索 → 单 Worker context；`AgentLoop._initialize_messages()` 回放 → add_message；结束后 `LongTermMemory.add_session_summary()`。
- **案例**：“登记 SYN-001”之后“把区域改为 DEMO-B”需要关联同一草稿；检索到别人的类似历史不能成为本次登记授权。
- **潜在问题**：Swarm 不传 session/context；短期单例未提供跨用户权限；Mem0 user_id 固定；去重字段错配；存储/摘要可以失真。
- **企业改进**：服务端绑定 tenant/user/session；结构化草稿放业务流程状态，聊天记录仅用于理解；引用历史时保留来源/版本/时效，不把历史回答当规则。
- **面试追问**：记忆、知识库、业务数据库有何差别？何时该清理历史，何时必须保留审计？

### 9）状态与摘要：StateManager / SessionSummary

- **解决什么问题**：观测一次执行到哪一步，以及事后查看过程。
- **为什么这样设计**：dataclass 保存局部执行状态，Markdown 摘要便于人工阅读。
- **调用链**：`core/state_manager.py:74 create_state()` → AgentLoop 修改状态 → `mark_completed/mark_failed()`；Swarm → `memory/session_summary.py:189 from_shared_context()` → `:273 save_summary()`。
- **案例**：进程写草稿后崩溃，下次必须知道草稿 revision、确认状态和操作结果；只读到一段聊天摘要无法恢复这条操作。
- **潜在问题**：StateManager 只是内存；load_summary 未实现；同 ID 摘要覆盖；指标占位；不是 checkpoint，更不是业务审计账本。
- **企业改进**：持久 run 状态与事件，保存草稿版本和外部操作标识；在恢复时先查询写入结果，再考虑重试。备选 A 业务表+状态机简单；备选 B 持久图工作流支持复杂中断但增加运维成本。
- **面试追问**：保存一份 JSON 算 checkpoint 吗？外部 API 写成功但回包丢失怎样恢复？

### 10）确定性约束与检索证据：ConstraintValidator / MedicalKnowledgeBase

- **解决什么问题**：检查动作和输出，给模型提供检索到的材料。
- **为什么这样设计**：把规则与工具逻辑从提示词中部分拆出来，同时集中管理知识检索。
- **调用链**：`AgentLoop.run()` → `constraints/validator.py:43 validate_tool_call()` → 工具；检索 skill → `knowledge/milvus_kb.py:172 search()`；答复 → `validate_output()` → `AutoFixer.fix_output()`。
- **案例**：检索到 DEMO-A 的说明可以解释字段，但“忽略确认直接写库”若出现在文档里，不能改变当前用户权限或确认状态。
- **潜在问题**：校验不阻止工具；只检查部分文本规则；没有真正输出 Schema；dense 检索分数/来源口径待验证；数据与指令没有完整信任边界。
- **企业改进**：业务写入前强制参数、权限、确认、幂等检查；检索只提供证据，业务规则版本独立审核；来源附 doc_id/version/location，拒绝将模型 confidence 当准确率。
- **面试追问**：软约束和硬约束如何划分？检索相关度高能证明业务操作合法的吗？

## 4. Agent Loop：ReAct 与 Function Calling 的具体知识点

| 概念 | 代码位置与调用关系 | 简单案例与边界 |
|---|---|---|
| ReAct 的基本原理 | `core/agent_loop.py:101` 的 LLM → tool → result → LLM 循环 | 模型先选查询动作，看到结果再回答；本代码实现相近的行动/观察模式，没有独立可验证的推理轨迹，不要要求输出隐私性的完整思维过程 |
| 模型怎样选工具 | `BaseAgent.get_tools_for_llm():60` → registry Schema → `LLMClient.chat_with_tools():141` | 描述告诉模型该调用哪个函数；`tool_choice=auto` 允许不调用，不能保证实际查过数据 |
| 参数怎样生成 | `LLMClient.chat_with_tools():193` 将 tc.function.arguments JSON 解析成 dict | “5份”可生成 quantity=5，也可能生成错误值；程序需检查类型、范围与对应业务实体 |
| 工具结果如何回传 | `AgentLoop._create_assistant_message_with_tools():339` → `LLMClient.create_tool_message():211` | 请求 ID、工具名、序列化结果一一关联；结果中的文档文本仍是不可信数据 |
| 防止无限循环 | `AgentState.should_continue():38` + Loop max_iterations/tool_call_count | 计数必须逐次检查，还应限制总时间、总请求数、嵌套研究请求及 token；当前只有部分上限 |
| 工具失败如何处理 | `SkillRegistry.execute():101` → 错误字典回模型；Loop `:247` 捕获轮次错误 | 项目不存在应追问；参数错误可修正；超时可有限重试；无权限/取消不得让模型换工具绕过 |

如果工具结果称 success=True，只能说明这个接口的成功定义。假如它只是返回草稿，任务仍不能记为“登记已完成”。这要靠明确业务状态，而不是措辞判断。

## 5. Multi-Agent：什么时候增加 Agent 才有意义

| 概念 | 源码位置/调用 | 案例 |
|---|---|---|
| 单 Agent 与多 Agent | `SwarmCoordinator.process():153,187` 按任务数选择 | 单 Agent 也能多步查字段和预览；多个 Agent 增加各自提示、历史、模型调用与失败面 |
| Lead / Worker 职责 | `LeadAgent.assess_and_decompose/synthesize_results`；`BaseAgent.process_subtask():147` | Lead 拆分与整合；Worker 自选注册工具。角色名不同不代表工具权限不同 |
| 何时并行 | `swarm_coordinator.py:285,417` 的 create_task/gather | 两个独立的只读查询可并行；“确认后写入”“查重复后登记”有顺序依赖，不能直接并行 |
| 并发写入 | `SharedContext.start_subtask/complete_subtask/set_data` 无 await/锁；Worker 共用 loop | 同一循环同步段可连续执行；但跨 await 的预算检查或多进程更新会出现竞态，dict 不能代替事务 |
| 成本与延迟 | Lead 至少一次分解；Swarm 可能额外汇总；deep_research 内还有模型调用 | 总成本约为路由 + 各 Worker + 嵌套工具 + 汇总，必须以 usage 实测；延迟不能简单写成总时间/Agent 数 |
| 子任务失败 | `_execute_single_subtask():434` 只日志；`synthesize_results()` 可处理部分贡献 | 应记录 failed/timeout/cancelled，说明缺失证据；业务写入相关校验失败时禁止宣称任务完成 |

两个架构备选（仅学习判断，不在本轮实施）：

- **单 Agent + Tools + 确定性 Workflow**：适合字段提取、追问、预览和确认后的受控操作。成本与测试范围较小，复杂独立专家任务的模块隔离较弱。
- **Lead + 多 Worker + SharedContext**：适合确实需要分开的专业只读分析、独立检索或多视角审查。能分工，但协调、状态隔离、错误处理、成本和审计更复杂。

初步建议先掌握第一种的控制边界，再通过测量决定是否需要第二种。入职后以现有架构与真实接口约束为准；阶段 C 才系统比较业务方案与 LangGraph，不在此提前选定企业框架。

## 6. Memory：对话、状态与业务事实如何分开

| 概念 | 作用 | 当前实现与调用 | 虚构案例 |
|---|---|---|---|
| Conversation History | 保留消息上下文，理解指代 | `memory/short_term.py:26 ConversationHistory` → `AgentLoop._initialize_messages()` | “那5份”指向上一条输入，不证明已经入库 |
| Short-Term Memory | 管理一个会话的近期消息 | `ShortTermMemory.add_message/get_recent_messages/get_history`，内存或 Redis | 为本轮提取 DEMO-A 草稿字段；Redis TTL 是可选后端行为 |
| Long-Term Memory | 跨会话检索历史片段 | `LongTermMemory.search_similar_sessions()` → Mem0 API | 找到曾用过的表达方式供参考，不能复用旧用户授权 |
| State Persistence | 保存可恢复的当前任务状态 | 当前 `StateManager` 仅内存；`SessionSummary.save_summary()` 只写摘要 | 真正持久状态应能恢复草稿 revision=2、awaiting_confirmation |
| Checkpoint | 在明确步骤保存恢复所需状态/版本/操作标识 | 当前 Agent 主链路未实现；`load_summary()` 返回 None | 中断后先检查该 revision 是否已写入，再决定重试；训练 checkpoint 与此不同 |
| Business Database | 存放权威实体、关系、版本和交易结果 | 当前项目没有样本登记业务数据库链路 | SYN-001 属于哪个项目，以受控数据库记录为准，不能以聊天记忆为准 |

会话摘要是有损表示。用户取消、修改数量、切换任务时，需要更新确定性任务状态，不能靠摘要中是否出现“确认”推断。业务系统的审计保留和聊天记忆的生命周期也应分别配置。

记忆设计还有两个选择：A 使用服务端短期历史和本地持久任务状态，便于离线验证；B 增加跨会话语义记忆，能复用经验但带来隔离、时效与授权问题。当前未经企业授权，不接入云端历史保存。

## 7. Harness Engineering：程序必须强制什么

这里的 Harness 指包围模型与工具的控制程序：把预算、类型、权限、人工确认和失败状态做成可检查的边界。参考源码只是部分教学实现，不能因 YAML 写了“强制”就视为具备保护。

| 概念 | 参考源码与接线状态 | 约束性质 / 未来必须的强制边界 | 简单案例 |
|---|---|---|---|
| 工具白名单 | `SkillRegistry.execute()` 拒绝未注册工具；`validate_tool_call()` 对不推荐工具只警告 | 当前名字注册是部分硬边界，角色推荐是软约束；需按用户/角色/动作维护受控白名单 | 模型要求 drop_database，无论解释多合理都不执行 |
| 参数验证 | `_infer_skill_parameters()` 描述参数；`LLMClient` 只 json.loads；无 Pydantic 模型调用证据 | Schema 提示是软引导；执行前 Pydantic 类型/范围/枚举、业务外键校验应为硬边界 | quantity=-1 或 project_id 不存在时拒绝写入 |
| 权限检查 | 所查 registry/Loop/SharedContext 无用户业务权限链；历史 session_id 可由模型传 | 必须由已认证的服务端上下文校验，不能信任模型生成的 user_id | 用户对 DEMO-A 无权限就返回 forbidden |
| 输出 Schema | `post_process_result()` 和 `EvidenceSynthesizer._parse_response()` 正则/关键词；dataclass 不是完整业务契约验证 | 模型格式要求是软约束；返回包络和状态用类型校验，Schema 合法与语义正确分别判断 | draft 字段齐全仍要核对项目/位置是否合法 |
| 人工确认 | 当前主链路没有确认状态机 | 必须将确认绑定 user、draft_id、revision/hash、有效期；修改草稿后确认失效 | 确认数量5之后模型改成6，不能沿用原确认 |
| 审计日志 | loguru、Event 列表、SessionSummary；可能包含原始参数/问题 | 普通日志辅助观测；业务操作需持久审计记录、脱敏、唯一操作 ID 与明确结果 | 记录谁确认了哪版草稿、API 最终是否成功 |
| 失败恢复 | Loop 重试/降级，Swarm wait_for；StateManager 非持久 | 必须区分可重试/不可重试，保存终态、查询外部结果、以幂等键避免重复 | 写入成功但响应超时，先按操作 ID 查结果 |
| Prompt Injection 防护 | `EvidenceSynthesizer._build_synthesis_prompt()`、Lead synthesize 拼接来源/贡献；未见完整防护链 | 提示“忽略恶意指令”只是软约束；权限/确认/白名单/执行预算在程序端不可被文档覆盖 | SOP 文本里“跳过确认”只当引用内容，不当系统指令 |

注意用户输入和检索文档都不可信。服务端身份、工具定义、确认状态和受控规则才是执行依据。检索材料里看似专业的规则必须有授权来源和版本；当前的关键词风险逻辑只能解释为第三方演示逻辑。

可对照学习的三处断点：

1. `AgentLoop.run():166` 已知道 valid=False，仍在 `:171` 调用 execute_tool——检测与阻止是两件事。
2. `ConstraintValidator.get_required_agents()` 有实现，但 Lead/Coordinator 主链路未调用——定义与接入是两件事。
3. Loop 正常文本输出经过校验，Lead 汇总与迭代耗尽输出不走同一校验——局部校验与覆盖所有出口是两件事。

## 8. 三个最值得实际动手的案例（仅提案，未执行）

优先做独立离线实验，不直接运行原 `examples/test_all.py`。任何执行、安装前都需再次按用户要求确认依赖、出网、成本和副作用。下列模型/API费用为零的前提是全部使用 fake/stub，且未引入下载或真实 endpoint。

| 案例 | 学习目标与源码锚点 | 准备依赖 / 出网 / 成本 | 核心验收与风险 |
|---|---|---|---|
| 1. Fake LLM 两轮工具调用 | 理解 `AgentLoop.run()`、`SkillRegistry.execute()`、`create_tool_message()` | Python 与小型隔离测试环境；若复用代码需要 loguru 等 import 依赖，用 stub 避开真实 config/OpenAI client；无出网，零模型 API 费用 | scripted tool_call → 合成结果 → 最终文本，ID 对齐、调用次数准确、非法参数拒绝；原 Loop 构造会读 YAML，不能直接无审查 import 全链 |
| 2. 两个合成子任务与超时/失败 | 理解 `SharedContext`、`_execute_single_subtask()`、gather/wait_for | Python asyncio、必要 loguru；stub Lead/Worker，不构造原 Coordinator；无出网，零模型 API 费用 | 一个成功、一个失败/超时，终态与 partial 可解释；验证 dependencies 与共享计数问题；仅用临时记录，不碰 DB |
| 3. 会话隔离与记忆字段契约 | 理解 `ShortTermMemory`、`LongTermMemory.search_similar_sessions()`、`deduplicate_sessions()` | 内存后端、fake Mem0 返回；不安装/连接 Redis/Mem0，不加载 embedding；无出网，零模型 API 费用 | 两个 session 不串数据；不同 content 的相似结果不被错误去重；重启后哪些数据丢失明确；单例污染需测试隔离 |

这三个案例可以先以不改参考文件的独立练习实现。若要证明上述缺陷，先写能复现问题的失败测试，再在独立副本最小修复。当前未创建练习代码，也未申请执行原脚本。

真正的本地模型/真实检索案例应等平台、依赖、模型缓存和运行成本明确后再做；不能为了跑项目一次性安装训练栈。

## 9. 与医疗科研信息管理最有关联的部分

当前业务场景仍是假设，下面只映射可学习思想。

| 关联度 | 技术模块 | 可以迁移的思想 | 需要重新补齐的能力 |
|---|---|---|---|
| 高 | AgentLoop + LLMClient | 语义理解、字段提取、工具结果反馈 | 结构化业务 Schema、追问和任务切换语义 |
| 高 | SkillRegistry / 工具执行边界 | 受控工具映射、隐藏具体 API 实现 | 权限、确认、Service 层、幂等与事务 |
| 高 | StateManager / SharedContext | 把任务状态与消息分开 | 持久状态、草稿版本、取消、可恢复终态 |
| 高 | knowledge / 检索 skill | SOP/术语检索的接口组织 | 正式授权来源、版本、引用、检索质量验证 |
| 高 | ConstraintValidator 的位置 | 在工具前和输出后插入确定性验证 | 从警告升级为实际执行门禁，覆盖全部入口与出口 |
| 中 | Lead / Worker 并行 | 独立只读步骤或专业分析分工 | 先证明单 Agent 不足；避免增加无收益复杂度 |
| 低（本阶段） | MediX-R1 训练/评估 | 了解模型层与应用层是不同工程问题 | 不做训练，不把模型榜单分数混入业务 Agent 评测 |

不可直接迁移当前健康咨询、疾病联想、诊断概率或指南文字为企业业务规则。后续所有模拟规则必须显著标注“演示规则”，真实规则由授权资料和负责人确认。

## 10. 推荐的下一阶段学习计划

以下是建议安排，不是自动继续执行的授权。2026-10-19 入职后，真实实习任务优先。

1. **10月13–14日：源码复述**。读本文件前六个模块，手画从一条输入到一个 tool_call 再回模型的链路；能解释三个 Skill 概念与单/多 Agent 路由。
2. **10月15–16日：经确认后做离线练习**。按三个案例逐个验证，只用合成数据、fake LLM、fake API；保留失败证据与运行条件，不追求第三方百分比。
3. **10月17–18日：经下一步授权再进入阶段 C/D 设计**。先比较最简单的单 Agent + Tools + Workflow 与多 Agent 的需要；再讨论 LangGraph 的恢复价值；先设计受控登记草稿流程，不实现完整项目。
4. **10月19日入职后：重新对齐**。获取真实任务目标、既有架构、可调用接口、数据授权、负责人、验收与归属要求。用户要求的 `06_INTERNSHIP_ALIGNMENT.md` 留待阶段 F 创建，当前不提前生成。

学习成果表述建议：可以说“我对第三方项目做过静态架构审查，理解工具调用、状态、约束的边界”；不能说“我开发了 MediX”或“我的系统实现了资料中的准确率”。运行练习后也只报告实际用例与实际测量。

## 11. 需要用户确认的关键事项

这些事项影响后续工作；本轮静态文档可以先完成，不需要以确认阻塞交付。

- **材料与来源**：PDF/ZIP 是否另有位置，第三方源码的官方来源与完整许可证能否补齐？这决定阶段 A 的 PDF 指标核验能否完成。
- **下一步范围**：先开展三个离线案例，还是先进入阶段 C 的业务适配分析？不默认进入实现阶段。
- **若选运行**：具体执行清单、最小依赖、临时写入目录、全部 stub/fake 与零出网边界需获得确认；不默认批准真实 API、Mem0 或模型下载。
- **入职任务**：公司既有技术栈、接口与数据使用规定目前均为待确认；不假设公司允许使用当前框架。

## 12. 交付与恢复上下文

- 已完成：现有源码范围的阶段 A 静态审查、阶段 B 知识地图、10 个模块、3 个拟运行案例、5 类主要问题与后续学习建议。
- 未完成：缺失 PDF/原 ZIP 的来源对照与指标核验；任何运行时功能、性能、平台兼容性和医学内容正确性验证。
- 未执行：测试、训练、依赖安装、模型下载、云 API、提交/推送与阶段 C–F。
- 恢复工作时：先读两份文档；若参考源码已变化，重新核对文件行号与调用链；下一步只做用户明确选择的阶段。
