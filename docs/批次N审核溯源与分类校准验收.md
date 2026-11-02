# 批次N：审核失败溯源与分类/语义校准

2026-10-15。206项后端离线回归通过（45.49秒）。最终basic-07、basic-16均completed，两个Reviewer完成；相邻comparison-06、scenario-06仍partial且Reviewer完成。前端、冻结dev/test/manifest、正式语料、Dot候选区及用户.env保持不动，原演示服务未重启。

## 审核失败现在能定位什么

新增SQL持久`review_trace`，在外部Reviewer调用前保存输入：原子事实文本、全局index/位置、去重后的原句位置/文本、对应原句ID、原文证据quote/offset/hash、实际项目规则与语料范围、程序期望类别及分类规则hash。输入包有独立SHA-256；问题只重复记录hash，原问题仍由原SQL会话保存。

每次首审、复审及格式修复记录轮次、批次、全局offset、尝试状态、是否格式修复、解析后的类别/支持判定/已知证据ID/备注，以及安全诊断。格式已合法但语义分类不合法的结果也会保留；因此以后可看到“哪一句、模型给了什么类别、规则预期什么、哪个证据及哪个全局index”。失败第二批不会清掉第一批成功记录。

只接收已通过字段结构校验的Reviewer字段；未知证据ID保留数量，不复制任意值；任意provider envelope、HTTP正文/headers、密钥和异常原文不入trace。结构无效的输出只保存类型/字段路径诊断。取消、超时或预算不足会将待完成尝试标记为真实失败状态，未审核内容仍不作为最终answer。

`GET /runs/{id}`可返回本人trace，另一个用户读取仍404。原子事实最多40条，证据80段/18000字符，每批最多10条；输入去重，trace次数上限受本轮原模型预算约束。所有外部尝试仍扣原计数，未新增独立预算或第三轮语义改写。

## basic-07：定位与分类阻断修复

题目：“什么是2型糖尿病的胰岛素抵抗？”M旧检查点的审核前原稿能读到“有风险因素不等于已患病，也不代表已确诊”。但旧失败批次的原子稿未保存，无法追认当时index=1究竟是哪句，不伪造历史结果。

已用离线失败测试确定：旧门禁把“代表”无条件当医学事实特征，连“本内容不代表个体诊断或处方建议”也会拒绝；风险不代表已确诊提醒也存在同一误拦路径。N第一轮保留旧门禁的真实重跑本身completed，没有重复M阻断，说明模型输出具有波动，不能把一次成功当根因修复证明。

修复为完整句匹配的窄政策/风险边界：仅表达科普不能替代诊断、风险不等于确诊的限定提醒，按project_behavior绑定实际educational_scope等规则。混入医学事实、数值或单位不享受该例外；“有风险因素代表一定患病”仍被医学事实门禁检查。没有按basic-07题号放行。

Reviewer原生JSONSchema及payload提供逐index类别约束，让模型在初次提交就遵守程序要求；类别约束不授予supported，医学事实仍需英文原文，项目行为仍需真实policy。supported判定不会被程序自动升级。

最终新运行basic-07：8次模型/HTTP、一次语义改写，两轮审核完成，三个参考要点均保留，包括此前容易遗漏的随时间胰岛素可能不足。新trace已保存全部输入和两批首审/一批复审。M旧失败继续保留，不能声称已重建其丢失的精确原子文本。

## basic-16：过度删减修复

M已记录的三处误删均有固定NLM原文直接支持：排出速率增加、早期通常无症状、异常需更多检查确认。问题主要是Reviewer对意译、限定词作用域及检测全称/缩写的判断过于机械，例“通常没有任何症状”被错误理解成绝对全称，“加快排出”被当成额外的加速度/机制断言。

提示现在要求按原句实际命题核对，不自行添出额外命题后再拒绝；“通常”限定整个否定谓语、同一检测全称/缩写可对应；部分支持必须指出实际缺证据子断言。一次改写使用接近原文的重述保留获支持核心和完整限定，再交复审。没有建立医学答案白名单、没有用字符串匹配替代语义审核。

最终basic-16：11次模型/HTTP、一次语义改写，completed，三个核心参考要点与原三处误删内容均保留。复审第二批首次缺少医学证据ID，`REVIEW_MEDICAL_EVIDENCE_REQUIRED`触发一次格式修复后恢复；失败判定、原子文本、修复后的引用均已留存，终态成功不掩盖中间失败。

基于已保存的类型合法输出离线复核，缺证据条目是批内index=1、全局index=11的“UACR不等同于直接测GFR”。修复后同一条绑定了NLM GFR和UACR原文。原记录的诊断未带index，保持不改；另存离线定位结果。最终代码已让每条证据ID/政策ID/医学证据缺失诊断都带索引，并对16个真实成功批次离线回放确认仍通过。政策例外也要求正确project_behavior类别及实际policy，不能改成corpus_scope逃过绑定。

原文核对见[NLM UACR](https://medlineplus.gov/lab-tests/microalbumin-creatinine-ratio/)；运行仍使用固定库快照，没有用打开现行网页更新正式语料。

## 校准与真实开发题

独立技术校准扩至18条（10应支持、8应拒绝），加入原三处UACR意译、风险提醒、胰岛素响应，以及丢掉“通常”、取消复查、完全不分泌胰岛素等反例。最终接受/拒绝18/18、类别18/18，2次HTTP。期待标签只用于本地统计，不发送给Reviewer；不是医学金标准或一般化正确率。

| 最终同版本dev | 终态 / Reviewer | 参考要点 |
|---|---|---|
| basic-07 | completed / completed | 3 met |
| basic-16 | completed / completed | 3 met |
| comparison-06 | partial / completed | 2 met / 1 partial |
| scenario-06 | partial / completed | 3 met |

四题共12要点：11 met、1 partial、0 missing；M同四题为7 met、1 partial、4 missing。最终四题41次HTTP/438017 tokens，分两个各≤40次预算批次；Lead自动选择3个单任务和scenario-06的2任务依赖链。8个trace输入hash和578个原文证据位置/hash核对通过。原文位置正确不证明全部医学蕴含正确。

相邻题仍有局限：comparison-06两种时间窗和日常监测保留，但“信息维度不同、不能互换”的概括仍被过严拒绝，第三要点部分满足；scenario-06核心空腹条件保留，但题外胰岛素/降糖药细节和额外告知要求被删除。范围免责声明也偶有误判，程序固定范围提示最终保留。不能宣称Reviewer误判已彻底消失，或同版本dev20/冻结test40全部通过。

完整结果见[质量报告](../backend/evaluation/medical-quality-v4/focused-dev4-quality.json)和[机器证据](evaluation/n-review-trace-results.json)。N新增8次开发题观察含重复题，4个不同dev；加校准共71次HTTP/681280 tokens。每个真实批次独立上限40，Mem0、联网工具和后台维护关闭，Dot新资料未进入问答。

## 本批发现的schema边界

新增类别约束在某审核批次没有匹配项时曾生成空allOf。这是无效JSONSchema；两题试验第二批返回REQUEST_INVALID。先补离线失败复现，再改为只有存在约束才输出allOf；最终真实两题审核通过。12次请求的中间报告保留，不合并为最终成功。不打印或猜测远端错误原文。

该问题来自本次新增条件约束的空集合边界，未归咎模型能力或旧项目。新增原生schema测试同时覆盖有/无类别要求；全部字段约束与原审核预算保持。

## 保护与复现

206项离线回归通过：包含失败第二批全局index、格式修复前后留存、任意响应不入trace、未知ID只计数、跨用户404、窄政策边界与混合事实保护、原生schema有效性，以及原有单多Agent/JWT/SQL/登记/预算测试。

210个保护文件hash无变化、153个原参考文件hash无变化、674条旧SQL行保留；冻结60题结构/出处校验通过。前端、原参考代码、Dot候选区、正式语料、用户.env及原演示服务均保持原状，未Embedding/写正式Milvus，未下载模型。

```powershell
# backend目录；默认离线
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\evaluate_medical.py --validate-only
# 仅显式运行时调用DeepSeek
.\.venv\Scripts\python.exe scripts\calibrate_medical_reviewer.py --fixtures evaluation/reviewer-calibration-v2/fixtures.json --run-real
.\.venv\Scripts\python.exe scripts\evaluate_medical.py --run-real --pilot-only --limit 2 --model-budget 16 --case-ids basic-07,basic-16
```

下一步优先扩展真实语义误判校准和完整同版本dev20核对，继续记录失败输入，保留一次改写上限与未审核内容封闭；专业医学复核、Dot来源/许可准入及候选题家族隔离仍未完成。
