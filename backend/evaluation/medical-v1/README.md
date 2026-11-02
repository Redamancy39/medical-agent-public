# 医学问答评测集 v1

L批剩余10道开发题真实评测完成，并新增[medical-quality-v2](../medical-quality-v2/README.md)独立来源/要点覆盖报告。medical真模式的最终出口现有Reviewer，partial可能表示省略部分无充分支持内容，不能当成API失败或医学准确；报告另给reviewer_completed。当前原dev/test/manifest完全保留，test40只做结构校验；多批不同代码的dev20观察不宣称最终同版20题通过。

2026-10-14批次K新增独立[medical-quality-v1来源审查](../medical-quality-v1/README.md)，不覆盖本目录冻结输入。dev20/60参考要点及10题63项答案已逐原文审查，临床专业复核未开展；另10题dev回答未观察。K新增6题真实5完成/1失败，38次HTTP、104,270 tokens；缺引用失败保留。安全规则入口和精简任务提示之后的效果另行验证，不把旧运行重计为新代码真实通过。

版本medical-v1-2026-10-14，60道人工编排、依据原文绑定的评测草稿。开发集20题、冻结测试集40题；所有个人场景均为合成内容，没有真实患者资料。参考要点和安全规则**未经过医学专业复核**。

| 类别 | dev | test | 合计 |
|---|---:|---:|---:|
| basic 基础知识 | 6 | 14 | 20 |
| scenario 场景与信息不足 | 4 | 6 | 10 |
| comparison 来源比较 | 4 | 6 | 10 |
| unknown 库外或缺证据 | 3 | 7 | 10 |
| safety 风险与不当请求 | 3 | 7 | 10 |
| 合计 | 20 | 40 | 60 |

高血压21题、2型糖尿病30题、共享主题9题，分布如实记录，不虚构主题均衡。每题含family_id、预期动作、参考要点、禁止结论、来源版本、原文位置和复核状态；policy.json定义项目回答边界。无医疗原文依据的未知/隐私题使用项目规则，不伪造医学来源。

manifest.json冻结正文、规则及数据集hash。校验60题数量、分组、重复问题、跨split家族泄漏、来源版本与段落位置。该校验只证明结构与出处绑定，不证明参考要点医学正确。

```powershell
# 在backend目录执行。
.\.venv\Scripts\python.exe scripts\evaluate_medical.py --validate-only
# 默认仅20题dev本地BGE+重排检索；无模型API、Mem0或网络调用。
.\.venv\Scripts\python.exe scripts\evaluate_medical.py
# 显式4题开发链路观察：真实DeepSeek Flash，最多40次HTTP。
.\.venv\Scripts\python.exe scripts\evaluate_medical.py --run-real --limit 4
# 只观察同4题真实主链，跳过重复的20题本地检索扫描。
.\.venv\Scripts\python.exe scripts\evaluate_medical.py --run-real --pilot-only --limit 4
```

脚本建立独立SQL与Milvus目录，按真实Lead自动规划。只把question传入应用；预期动作、路由建议和金标准不会送入Lead/Worker。真实模式最多选6道dev题，默认basic-01、scenario-03、comparison-03、unknown-01。test的40题只做结构校验，本阶段不用于调参或生成回答。

`--pilot-only`必须与`--run-real`一起使用，仍校验冻结输入并建立独立库，retrieval_sweep_status为not_run、检索指标为null，不复用旧结果冒充新扫描。批次J同4题4/4工程完成，17次HTTP、50,412 tokens；真实未触发格式修复，医学答案pending_review，不能据此报告准确率。H批原失败和检索结果保留，见[批次J验收](../../../docs/批次J规划汇总修复与资料接收验收.md)。

Hit@5要求命中文档版本、编辑段落范围和原文支持位置；同文档其他段落不算命中。MRR@5记录首个相关片段；支持覆盖率按每题所需证据组计算后取平均。无gold题从检索分母排除，单列数量；不能因此称其答案正确。检索分数不是临床可信度。

真实报告保留原始运行状态、实际plan/reason、任务数量、引用、HTTP状态、token和延迟，不按关键词自动算医学准确率。答案逐项核对数值、条件、地区、引用支持和边界行为，标记充分/部分/矛盾/待复核。严重错误逐项记录；工程completed不等于医学正确。

四种配置属于可选后续消融实验。当前默认业务流程与评测都由真实Lead自主选择任务，不强制单/多Agent。只有明确做消融时才固定执行策略，并独立标注，不用于宣称Lead路由正确。

运行产物位于runs/，包含开发报告和临时数据库；不作为公开数据集分发。后续H4再开展完整问答质量、引用支持与保留测试评测。
