# 批次J：Lead规划、汇总修复与Dot资料接收

2026-10-14。后端161项离线测试全部通过；沿用H批原四道开发题，真实DeepSeek Flash自动规划4/4完成。前端暂时不动，登记保持模拟。工程完成状态不代表医学答案正确。

## 规划与汇总的修复

原先Lead主要依赖提示词输出JSON，规划失败只给通用错误，汇总未覆盖任务/来源时无法在预算内修复。本批先用6个失败测试复现契约缺口，再实现原生结构化提交与安全诊断；新增10个Lead测试覆盖故障和原生工具契约。

- 规划通过唯一原生函数`submit_plan`提交，程序继续校验角色、任务ID、依赖存在及无环。提示词要求只分配任务目标，信息不足时仍给有效计划，由Worker处理缺证据，不生成空计划或把医学结论当任务描述。
- 多任务汇总通过`submit_synthesis`提交。工具schema绑定实际完成任务和来源ID，并约束数量；程序仍检查精确覆盖、重复和虚构ID，不降低校验要求来获得completed。
- 运行接口新增`contract_diagnostics`和`contract_repair_counts`，保留字段位置、错误类型和覆盖数量，未知字段名称被遮蔽，不保存模型原始错误内容或密钥。
- 启用`schema_repair_limit=1`时，plan、synthesize各最多修复一次，全体Worker另共用一次格式修复额度。默认0不自动修复；真实入口和此次试验使用1。所有修复占用原全局模型/HTTP预算，仍受超时、取消和租约控制。鉴权、限流等非格式错误不作格式重试。
- 规划重复失败明确返回失败，不静默切到ConsultationAgent。汇总重复失败保留已完成Worker结果并返回partial，不重复执行Worker，不把失败汇总当最终答案。

旧H报告未保存违规模型原始输出，无法事后证明unknown-01具体违反哪个字段。本批修复可复现的契约弱点，并验证同四题的新运行；原2完成/1部分/1失败报告保持不变。

## 验收结果

| 开发题 | Lead实际任务数/角色数 | 状态 | 模型调用/工具调用 |
|---|---:|---|---:|
| basic-01 | 1/1 | completed | 3/1 |
| scenario-03 | 2/2 | completed | 5/2 |
| comparison-03 | 3/3 | completed | 6/2 |
| unknown-01 | 1/1 | completed | 3/2 |

真实调用17次HTTP，均返回200，总计50,412 tokens；Mem0、联网和维护关闭，test40未生成回答。模型实际未触发格式修复，修复、预算耗尽、鉴权失败和来源虚构等路径由离线受控测试证明，不能称为真实故障观察。

命令为`evaluate_medical.py --run-real --pilot-only --limit 4`，只跳过重复的20题检索扫描，仍检查冻结资料并在独立SQL/Milvus中运行。检索扫描状态not_run，未将历史检索指标当成本次新结果。当前4题不能证明长期零失败；逐事实引用支持、额外医学推断、正文长ID引用和专业复核仍pending。MED-04/06等质量工作继续保留。

完整离线回归161/161，耗时45.79秒；10项Lead契约测试全部通过。可复核摘要见[批次J证据](evaluation/j-lead-contract-results.json)，原始本机试验目录为`backend/evaluation/medical-v1/runs/20261014-110851-fadf3853/`。

## Dot资料接收

本地读取[共享台账](https://chatgpt.com/space/page_6952833f7ff8819189a31b3dd75cc556)与[来源说明](https://chatgpt.com/space/page_7e24fb56fa9c81919ad603a26b6c58cd)，将5条既有新来源加NIDDK/NHS低血糖2条适配为medical-handoff-v1。此次为Page元数据本地适配，尚不是Dot新JSON附件交付。

接收批次`dot-ledger-20261014-v5-sources`：7条来源元数据、0份新增正文、0条逐点审查建议，均staged_for_review。访问状态仅保留Dot报告，复用条件均unconfirmed；中国糖尿病2024临床正文仍unavailable。接收和同批重放幂等通过，SHA-256为`81798bb29c33619f181e5993fc3a2f963b57087358d35cad944b54f865253688`。

记录见[接收文件](../backend/knowledge/medical-handoff/inbox/dot-ledger-20261014-v5-sources.json)及[snapshots](../backend/knowledge/medical-handoff/snapshots/dot-20261014-ledger.json)。新增跨批URL去重，分别统计新增、更新和未变来源；同批不同内容仍拒绝，不覆盖旧接收回执。

Dot报告dev20/60要点核查完成，不能算作本地收到60条审查JSON。两个旧附件不可读问题保持pending_readable_export，后续需独立JSON或Page完整代码块。接收回执已写入同一台账并回读；Page更新不主动唤醒Dot，不改日程，也未发送主对话消息。

## Milvus入库现状

本次实际打开现有独立Milvus库核对数量，没有重新Embedding或导入：

| 区域 | 文档/来源 | 片段 | 用途 |
|---|---:|---:|---|
| 正式`knowledge_medical_v1.db` | 20 | 40 | 当前medical问答检索 |
| TXT候选`knowledge_medical_candidates_v1.db` | 4 | 38 | pending_source_review，不接默认问答 |
| Dot来源候选 | 7 | 未向量化 | 仅元数据，不是新增Milvus知识 |

TXT链路已实现：严格解码→章节/段落切块→LF字符位置及原始字节/文本hash→来源候选状态→版本去重→本地BGE向量→独立Milvus→已有reranker。重复资料和元数据未变时跳过Embedding；解析失败、来源未核实明确记录。

当前是脚本驱动：正式库用`prepare_medical_knowledge.py`，TXT候选用`ingest_medical_txt.py --index-candidates --rerank`，Dot建议用`receive_medical_handoff.py --input <JSON>`。尚无通用上传API、PDF/OCR流水线或自动来源准入；Dot元数据不能直接转成医学正文入库。

## 保留与续作

153份参考文件hash一致，674条备份旧SQL保留，冻结60题结构/来源绑定通过。原资料、正式语料、dev/test/manifest、用户.env和前端未改；本批没有Mem0写入、权重下载或重新部署。独立测试应用已运行新代码，原演示服务未重启，下一次重新启动后才加载修改。

下一步优先接收可读的逐点建议，核对引用支持，在独立开发快照修订资料/参考要点；原冻结版保留。随后开展MED-04逐事实支持与完整条件评测，决定新来源准入，再安排完整dev问答；test40继续暂停。
