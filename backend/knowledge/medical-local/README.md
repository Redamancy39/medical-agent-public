# 原项目TXT候选入库

2026-10-14：已处理原项目01、02、20、21四份TXT，生成38个片段，独立候选Milvus库为`backend/data/knowledge_medical_candidates_v1.db`。来源版本、发布机构和复用条件待核对，全部为pending_source_review，医学专业复核not_run。候选库未接入默认医学问答工具，不与正式20来源医学库混合。

借鉴rag-agent的文件探测、统一文档块、质量检查与阶段报告设计，在独立medical_ingestion模块实现；不导入rag-agent应用配置、SQL或Chroma。当前仅TXT，PDF/OCR后续另做。

| 文件或目录 | 含义 |
|---|---|
| raw/ | 原始字节快照，保留原编码、BOM和CRLF；以raw_source_sha256命名 |
| text/ | 严格解码后统一LF的UTF-8文本；原文件不改动 |
| manifest.json | 当前本地文档、版本、章节位置和候选状态 |
| reports/ | 每次处理的独立报告，保留历史失败和版本 |
| last-report.json | 最近一轮读取、切块、质量、准入和候选索引阶段 |
| index-report.json | 本地BGE/重排探针、片段数和幂等导入结果 |

原始字节hash与归一化文本hash分开。start/end/source_spans使用LF归一化文本中的Unicode字符位置，不是字节位置；offset_basis明确记录decoded_text_lf_unicode。同内容的CRLF/LF、UTF-8 BOM变体在一批内归为同源重复，不当独立医学证据。

读取按UTF-8（识别BOM）或GB18030严格解码；无法解码、空正文、控制字符明确报错。切块保留章节和完整段落，原子段落超过900字符时返回ATOMIC_BLOCK_TOO_LONG，不静默截断数值、单位或条件。短片段标记需要上下文复查；质量标记不代表医学事实真假。

文档标题来自原文件，仅表示文件自称；publisher和publication_date等正式出处字段保持null，claimed_publisher另作为待核对声明。原始快照保留，版本更新不会修改旧快照。索引对照实际片段及元数据，未变才跳过Embedding；来源备注等发生变化仍更新索引。

```powershell
# 在backend目录执行，默认处理上述4份原TXT，不调用模型API。
.\.venv\Scripts\python.exe scripts\ingest_medical_txt.py
# 显式构建独立候选库，使用本地BGE及已有reranker。
.\.venv\Scripts\python.exe scripts\ingest_medical_txt.py --index-candidates --rerank
```

API的medical profile仍使用knowledge_medical_v1.db。本入口没有正式库导入开关，不因处理成功自动变为可信医学资料。
