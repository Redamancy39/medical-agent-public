# 开发集20题质量续评（L批）

冻结medical-v1不改，临床准确率null，专业复核pending，test40语义/答案生成均not_run。

- `remaining10-real-observation.json`：剩余10题分两批真实自动Lead运行，21+23次HTTP，合计268,810 tokens；3 completed、7 partial，Reviewer 10/10完成。partial多数是保守删减，不是provider调用失败。
- `remaining10-independent-review.json`及`remaining10-source-report.json`：独立读取固定原文与最后答案，63项逐句审查。28项医学陈述中26项获全文支持、2项部分支持，其余35项为范围/行为/编辑说明；不是自动采用运行时Reviewer自评分。报告内unobserved_dev_cases=10仅指此子集，项目整体20题已观察。
- `dev20-quality-report.json`：先前10题与新10题的独立要点覆盖核对；comparison-09用本批重跑替换该表最新观察，旧K失败另列。60要点：52 met、5 partial、3 missing；覆盖不是临床正确率，各行保留来源运行和answer hash。不同代码版本的观察不能当本批全20题同版本通过。

当前实时Reviewer审查句子/分号段，一个段含多断言时要求全部有直接支持。支持不足会删整段，可能连同有效核心信息一起删去；comparison-06出现时间尺度核心被全删。原子化claim拆解、有界改写后再审查、独立语义校准与专业复核仍需后续实现，不以严苛过滤掩盖回答覆盖不足。

首次剩余10题观察先于最终类别门禁/固定资料范围提示。后续safety-09单题复验另列于[本批证据](../../../docs/evaluation/l-realtime-review-results.json)，不替换旧运行或将其重计为10题同时通过。剩余10题的Reviewer全部完成不等于判定全部正确，发现了误删、误标和对同一原文条件判断不一致。
