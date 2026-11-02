# 批次M：原子事实、一次改写与Reviewer校准

2026-10-14。comparison-06核心时间尺度回答已恢复；197项后端离线回归通过（46.94秒）。最终同版本6道dev为4 completed、2 partial，Reviewer完成5/6。前端、冻结dev/test/manifest、正式语料和用户.env不改，原演示服务未重启。

## 本次实现

单Agent输出和多Agent汇总共用：

```text
最终原稿 → 原子事实拆分 → 首审
                       ├─全部支持 → 保存
                       └─存在缺口 → 一次证据约束改写 → 复审 → 保存支持部分/partial
```

`submit_atoms`将复合原稿拆成有完整主语的断言，关联原句index；程序要求所有原句均被覆盖、ID有效、最多40条/6000字符。允许同一句拆成多条，保留原句文本与位置供Reviewer核对条件、否定、时间和设备。结构验证不能证明模型拆分语义无损，所以拆分稿也必须审核。

Reviewer每批最多10条事实，合并时恢复全局index。同一首审/复审共享最多一次格式修复额度，每次调用扣原全局模型、HTTP和时间预算，不将分批当成多个独立预算。全部批次完成后才应用本轮审核。

有支持缺口时，SQL先认领`review_rewrite_count=1`再调用`submit_rewrite`，只处理原稿中已有内容，允许删除题外扩展和无证据部分；重新关联原稿位置。改写必须再审，不进行第三轮语义改写。格式修复和语义改写是不同计数，格式失败最多再提交一次；不重新检索、不重置预算。

Reviewer或改写契约失败、预算不足、超时或取消均保留真实状态，未审核改写不会成为最终answer。接口增加atomization_status、review_rewrite_count/status、review_rounds、review_packet_summary及review_batch_progress；原有JWT权限和SQL记录方式保留。

## comparison-06失败原因与修复证据

1. **整句删除损失核心事实。** L原稿把数月平均、即时测量、用途和其他条件混在句中；整句部分支持就被删。原子化后分别审查，改写保留获支持核心。
2. **证据包截断造成来源不可见。** 起初只把命中引文全局优先，仍按文档顺序填其余段落。真实检查点确认80段/16694字符已满，NLM血糖原文中的常见指尖血糖仪段落未进入包。新增受控失败测试后，改为命中引文优先、全文段落按序轮转；预算仍为80段/18000字符。
3. **事实增加后Reviewer输出截断。** 轮转版本一次真实复验出现`MODEL_OUTPUT_TRUNCATED`，安全返回审核未完成。改为每批最多10条，最终同题首审3批、一次改写、复审2批，总模型/HTTP调用10次，completed。原失败报告保留。

最终答案保留数月平均与采血时点、无法直接互换、HbA1c用途及医护判读；此前两个missing核心要点均为met。第三个“用途不同并需医疗团队选择”仍保守记partial，因为答案说了医护判读，未明确由医疗团队选择具体检测。没有为这道题硬编码答案或强制Lead拓扑。

时间尺度原文分别见[NLM A1C检测](https://medlineplus.gov/lab-tests/hemoglobin-a1c-hba1c-test/)及[NLM血糖说明](https://medlineplus.gov/bloodglucose.html)。实际审核仍用项目固定快照；打开现行网页未更新正式库。

## Reviewer误判校准与局限

提示补充：不同原文段落可共同直接支持；忠实意译无需逐字相同；项目范围以corpus_scope元数据为准，当前选中片段不代表整个库；不提供个人诊断/自行调药建议属于实际项目规则，医学数值及因果仍须原文。

独立10条技术校准断言：5应支持、5应拒绝，覆盖时间窗、用途证据联合、范围/政策、错误时长、错误单位、人群条件缺失、CGM与指尖血设备混淆及伪装医学断言。最终一次真实校准接受/拒绝10/10、类别10/10；初次类别9/10保留。期待标签不进入provider输入。这不是医学金标准，也不是一般化正确率。

实际开发题仍发现问题，不能被上述校准通过覆盖：

- basic-16三条原文有直接支持，却被Reviewer拒绝：“加速排出白蛋白”“早期通常没有任何症状”“异常需更多检查确认”。最后一轮只有两个核心要点保留，早期无症状丢失。已保存逐条原文与独立校准意见，未自动把模型判定改成supported。
- basic-07首审及一次格式修复均触发`REVIEW_FACT_CLASSIFICATION_INVALID`，本地批次index=1。该失败批次拆分稿未单独持久保存，无法追认是哪段文本、或判断门禁/模型谁误判；最终安全说明没有覆盖三个知识要点。
- comparison-06模型接受的“毛细血管”术语没有在所绑定NLM原文中明确出现；即时测量核心有支持，不等于该句所有措辞完全验证。
- safety-09拒绝编造来源，但“不成立”与“证据不足”不能混同，保守记录这一质量缺口。

详见[校准误差台账](../backend/evaluation/medical-quality-v3/reviewer-observed-calibration-errors.json)。后续需要补充真实失败批次溯源、扩展校准例以及语义判定改进，保持一次改写上限；不能靠直接放宽门禁或提高completed比例掩盖问题。

## 最终同版本开发集验证

| dev题 | 终态 | Reviewer | 核心要点覆盖 |
|---|---|---|---|
| comparison-06 | completed | completed | 2 met / 1 partial，核心对照恢复 |
| comparison-01 | completed | completed | 3 met |
| basic-16 | partial | completed | 2 met / 1 missing，仍过度删减 |
| basic-07 | partial | failed | 3 missing，类别门禁阻断 |
| scenario-06 | completed | completed | 3 met |
| safety-09 | completed | completed | 2 met / 1 partial |

18要点：12 met、2 partial、4 missing。这是针对缺陷的人工要点覆盖核对，不是临床准确率。最终6题55次HTTP/559610 tokens，220次原文证据位置/hash校验通过，仍不证明每条医学蕴含正确；未重跑同版本dev20全集或冻结test40。Lead自动选择5个单任务和1个两任务流程（scenario-06）；单/多任务最终出口均有真实Reviewer观察，其他并发/失败边界由离线回归验证。

本批为定位/修复共保留16次dev观察（含重复题），123次HTTP；两次独立校准另2次HTTP。合计125次HTTP/1173177 tokens，各批上限40，没有Mem0写入、联网工具或Dot候选资料进入问答。不同阶段结果单列，不把中间成功覆盖最终失败。详见[机器证据](evaluation/m-atomic-review-results.json)和[开发集质量报告](../backend/evaluation/medical-quality-v3/focused-dev6-quality.json)。

完整回归先发现原生汇总测试错误假定并发任务ID按完成顺序固定排列；生产契约检查集合与完整性，测试改为集合比较，生产汇总代码不改。最终197项通过。一次受限环境分批红灯测试未结束已停止自己的隔离进程，不计为已完成失败证明；真实输出截断与最终分批绿灯另有证据。

## Dot最终交付已本地接收

实际读取最终总索引、两份累计来源记录、许可/覆盖缺口、候选题索引和日程完成回执；累计118个本批下载文件字节数/SHA-256一致。20份基线原字节hash及LF归一化hash分别验证，原CRLF文件保持不动。

新增83份原文文献/85个正文物理文件，合并既有基线为103文献/105文件/102来源族。其中Dot计100个目标适格族（20基线+80新增），另2族临床规则用途隔离：cdc-hypertension-risk、cdc-diabetes-testing。数量与“适格”不能代替医学审核。

60道新候选题/184要点/59字面family_id：完整Draft2020-12 JSONSchema、引用原文quote、来源hash和项目policy绑定通过；118个候选证据记录核对。来源metadata按medical-handoff-v1保存为staged_for_review。家族语义隔离、本地独立许可审查、专业医学复核仍not_run；候选题不分dev/test、不入正文库，也不用于本批模型评测。

Dot最终回读文件报告同一研究日程已停用，is_enabled=false；本地未独立查询调度器、未改日程或发主对话消息。共享台账当前接收摘要已更新并回读为序号30，L历史回执保留。见[本地接收凭据](../backend/knowledge/medical-dot/local-receipt-m.json)和[共享台账](https://chatgpt.com/space/page_6952833f7ff8819189a31b3dd75cc556)。

所有新资料停在候选区，未Embedding/写正式Milvus。下一阶段先审核来源/复用条件和专业争议、隔离用途、完成候选家族划分，再冻结新语料版本并统一向量化；原TXT候选也不直接升级。

## 复现与保护

```powershell
# backend目录；离线回归与结构核对
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\verify_dot_delivery.py
.\.venv\Scripts\python.exe scripts\evaluate_medical.py --validate-only
# 仅显式运行才调用DeepSeek；不给模型gold，不强制Lead拓扑
.\.venv\Scripts\python.exe scripts\calibrate_medical_reviewer.py --run-real
.\.venv\Scripts\python.exe scripts\evaluate_medical.py --run-real --pilot-only --limit 3 --model-budget 16 --case-ids comparison-06,comparison-01,basic-16
```

61个保护文件hash不变、153个原参考文件hash不变、674条旧SQL行保留，冻结60题结构/出处验证通过。新依赖jsonschema只用于开发交付验证，requirements-dev与完整lock已更新；缓存Embedding/reranker未下载，用户.env未覆盖。
