# Dot资料交付接口

L批已接收新的可读交付：两批dev20审查共60项，两批正文来源元数据共18条；正文18份（17来源族）与10个候选题保存在[medical-dot](../medical-dot/README.md)，不作为当前问答语料。原旧附件可读性问题不重试，以本批新独立JSON作为实际接收证据，历史“0审查/0正文”状态保留各批边界。所有建议仍staged_for_review，冻结题集/正式语料不改。

分工：Dot在云端搜集资料、核查参考要点，本地Codex实现后端并核对交付物。共享台账是[成人高血压与2型糖尿病 独立资料核查台账](https://chatgpt.com/space/page_6952833f7ff8819189a31b3dd75cc556)。本地开发时读取台账和可访问交付；这不是关机后仍运行的本地同步服务。

schema.json定义medical-handoff-v1。每批UTF-8 JSON不超过256000字节，batch_id唯一，created_at带时区；sources提供候选来源，audits提供逐点建议。引用存在、格式合法和医学正确分别处理，接收只验证结构与题号范围。

```powershell
# 在backend目录执行。
.\.venv\Scripts\python.exe scripts\receive_medical_handoff.py --schema
.\.venv\Scripts\python.exe scripts\receive_medical_handoff.py --input ..\tmp\dot-batch.json
```

成功写入inbox/<batch_id>.json，状态staged_for_review，专业复核not_run，语料和数据集更新均not_applied。同批同内容重放幂等；同batch_id不同内容拒绝，不覆盖原建议。当前CLI拒绝test题审查，保持test40暂停；项目行为规则使用policy.json中的规则ID，不能当成医学事实支持。

跨批按来源URL（忽略片段和末尾斜线）统计新增、更新和未变元数据，分别返回new_source_candidates、updated_source_candidates、unchanged_source_candidates；不因去重覆盖历史回执。原有批次幂等重放仍返回其原始summary。

示例（仅展示格式，不能当真实Dot审查结果）：

```json
{
  "schema_version": "medical-handoff-v1",
  "batch_id": "example-only",
  "created_at": "2026-10-14T09:00:00+08:00",
  "sources": [],
  "audits": [{
    "case_id": "basic-01",
    "reference_point": "收缩压定义",
    "reference_kind": "medical_fact",
    "issue_type": "citation_gap",
    "support_status": "supported",
    "evidence": [{
      "url": "https://medlineplus.gov/highbloodpressure.html",
      "locator": "Summary",
      "quote": "This is called systolic pressure.",
      "access_status": "opened"
    }],
    "suggested_change": "补原文支持位置",
    "professional_review": "pending"
  }]
}
```

schema已上传到共享台账并成功回读，文件sha256为c5331e069afd098d92e6d78829a2b815fda7d9620efcbea37555c5612f3a0072。Dot应每轮链接独立可读取JSON，不只提供ZIP/Excel。若附件无法读取，可在台账放完整JSON代码块；接收后仍需人工检查，不自动入正式库或改金标准。

当前Dot报告dev20/60参考要点核查完成，test40暂停。A至E说明Page可读；两份已有B/C/E系列附件通过文件接口读取失败，因此尚未完成旧数据文件的自动接收。本批新增接收入口与测试已经通过，不将它称为云端资料全量同步已完成。

2026-10-14批次J已从可读Page适配接收[7条来源元数据](inbox/dot-ledger-20261014-v5-sources.json)，其中原5条加NIDDK/NHS低血糖2条；并非Dot直接交付的新JSON。原Page记录保存在snapshots。所有reuse_status=unconfirmed，access_status仅保留Dot报告；正文0份、audits 0条，逐点审查仍等待可读JSON。正式医学Milvus20份/40片段和候选4份/38片段不变，接收回执已写入共享台账并回读，没有修改日程或唤醒Dot。
