# Dot新交付候选区（M批最终接收）

2026-10-14最终交付已本地接收：新增83份原文/85个物理正文文件，加20份既有基线共102来源族；Dot计100目标适格族，另2族临床规则用途隔离。118个本批下载文件字节hash验证、20份基线原字节与LF归一化hash验证通过。

60道新候选题/184要点/59字面family_id通过完整JSONSchema、原文quote/hash与项目policy绑定校验；metadata已staged_for_review。家族语义隔离、本地独立许可审查和医学专业复核not_run，未更新冻结题集或正式库，未Embedding/写正式Milvus。

详见[local-receipt-m.json](local-receipt-m.json)、[最终累计来源索引](deliveries/final-cumulative-index.json)与[批次M验收](../../../docs/批次M原子事实与改写复审验收.md)。`scripts/verify_dot_delivery.py`可重复核对并幂等接收metadata；不自动准入。原HTTP字节未取得时保持null，交付文本hash不冒充网页/PDF原字节hash。

## L批历史接收回执

本地已接收截至共享台账序号12的18份独立正文、17个新增来源族，20份既有来源族作基线，云端累计37/100。NIDDK/NHLBI系列章节已合并，不把18份文件冒称18个新来源族。资料待本地来源/复用条件核对与医学专业复核，本阶段不Embedding、不入正式Milvus、不改变medical问答上下文。

`raw/`保存UTF-8 LF提取正文，均通过独立回读的SHA-256核对；这些是网页提取正文，不是原HTTP字节，原HTTP hash为null。`deliveries/`保留来源清单、候选题、schema和审查JSON，8个云端JSON本地原始字节hash一致；body文件与candidate题目/答案严格分开。许可verified仅保留Dot报告，本地独立许可审查not_run，不自动准入。

两批medical-handoff-v1审查已通过现有接收器保存到`../medical-handoff/inbox/`，共20道dev/60项建议，原金标准不改；两批正文元数据18条也已接收，其中7条新增URL和1条既有NIDDK候选更新。原候选7条、这批原文18份与医学来源族17个是不同统计口径，不能相加称25份可信医学正文。

10道新合成候选题、31条参考要点另存。已核对基本字段、无split标签、专业复核pending、来源正文hash/quote存在、项目policy文本与hash；完整JSONSchema验证和跨冻结题集的家族隔离未验收，不把它们放入当前dev/test，也不用于本批模型答案或检索。

接收证据见[local-receipt-l.json](local-receipt-l.json)。资料只停在候选区，凑齐有效正文目标后再审核、冻结新语料版本、统一分块/向量化。来源不足、许可不明与临床审查待办分别记录，数量不替代质量。

L批收尾最新台账序号18报告批次05累计62/100；本地核对截止批次02，后续03–05未接收/验收，不能把云端报告计数作为本地完整来源准入。

回执前再读序号20，云端已报告批次06累计72/100；本地截止不变，03–06后续交付待接收，未向量化。
