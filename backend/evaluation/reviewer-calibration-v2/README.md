# Reviewer语义与类别校准v2

18条固定来源/项目规则断言：10应支持、8应拒绝。加入UACR三处意译误删、风险提醒、胰岛素响应与丢限定/单位/时长/设备混淆等反例。标签只在本地统计，不进入provider payload。

20261015-002117-0f189d46：接受/拒绝18/18、类别18/18；按每批最多10条执行，共2次HTTP，原文固定快照。clinical_review=not_run，generalization=not_established。不是医学金标准，实际dev仍有误判；v1历史文件不改。

默认运行只校验输入；显式--run-real才调用：

```powershell
.\.venv\Scripts\python.exe scripts\calibrate_medical_reviewer.py --fixtures evaluation/reviewer-calibration-v2/fixtures.json --run-real
```
