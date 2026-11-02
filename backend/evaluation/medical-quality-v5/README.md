# O批：改写保留与完整开发集运行观察

本轮已执行全部20道开发题；2个程序安全出口completed，4 partial、14 failed，后18题均受DeepSeek上游错误影响。不能将“20题执行过”描述为“20题回答质量通过”。

[dev20-observation.json](dev20-observation.json)保留逐题终态、答案hash、真实返回文案和未评状态。安全出口6个项目行为要点单列，其余54个要点未评；医学质量指标为null。完整运行保存代码快照hash；收尾的内部合并上限修复只作离线验证，最终代码真实质量复验仍待provider恢复。

原始执行在`medical-v1/runs/20261015-100150-2cf734fc/full-dev.json`及10个批次目录；单独检索评测在`medical-v1/runs/20261015-095721-0d5caf3d/retrieval.json`。原始报告和冻结题集不改。

见[批次O记录](../../../docs/批次O审核保留与完整开发集观察.md)。
