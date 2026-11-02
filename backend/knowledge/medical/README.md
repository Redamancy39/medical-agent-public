# 医学知识库 v1

2026-10-14：成人高血压与2型糖尿病健康知识，20份NLM/MedlinePlus来源、40个章节片段。全部原文为美国英语资料；中文部分为Codex编写并绑定原文位置的编辑摘述，**非官方翻译，未经过医学专业复核**。不代表20个独立研究或20家发布机构。

仅采集MedlinePlus健康主题Summary及NLM医学检查正文；使用边界依据[MedlinePlus内容使用说明](https://medlineplus.gov/about/using/usingcontent/)。不采集A.D.A.M百科、ASHP药品专论、图片及外链第三方正文。WHO、卫健委、PMC等留作候选，不计入已导入来源。

| 文件 | 用途 |
|---|---|
| catalog.json | 20个固定公开入口；不扩散抓取外链 |
| sources.jsonl | 准入、地区、语言、许可、抓取时间、原文hash、正文路径与复核状态 |
| raw/ | 允许复用正文的UTF-8快照；旧快照保留，以manifest引用的版本为准 |
| editorial-sections.json | 20份文档的40个中文章节、英文依据；评测题不进入这里 |
| reuse-policy.txt | 采集时的内容使用说明快照 |
| collection-report.json | 最近采集批次结果；不是所有历史请求的累计账单 |
| build-report.json | 当前独立Milvus构建、幂等导入与本地模型记录 |

原文保留标题、列表层级和表格列。章节一并保留数值、单位、否定及条件，每个引用包含原文start/end/quote；起止位置按Python Unicode字符索引计算。发布日期未确定时为null，不用抓取日期代替发布日期。

构建前检查正文hash和每个英文依据的实际位置，再按章节导入。内容版本由原文hash和编辑内容hash共同决定；来源或编辑更新后，评测集绑定必须重新审查，不能静默沿用旧金标准。

```powershell
# 在backend目录执行；不调用云服务或下载模型。
.\.venv\Scripts\python.exe scripts\prepare_medical_knowledge.py --check-only
.\.venv\Scripts\python.exe scripts\prepare_medical_knowledge.py --rerank
# 仅需主动刷新公开资料时执行，会改变来源快照，触发数据集版本检查。
.\.venv\Scripts\python.exe scripts\fetch_medical_sources.py --fetch
```

使用独立`data/knowledge_medical_v1.db`，原合成库`data/knowledge_v3.db`保持不变。Embedding复用本地BGE-small-zh-v1.5，reranker复用用户已有D盘bge-reranker-v2-m3；缺权重时失败，不自动下载。

已记录的争议包括前驱糖尿病页面与HbA1c检查页面对6.5%边界的文字差异，以及风险描述和筛查年龄的不同语境。保留各自原文并提示适用范围，不能据此生成统一中国临床标准或个体诊断。
