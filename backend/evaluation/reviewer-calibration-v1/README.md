# Reviewer技术校准

fixtures.json有5条应支持和5条应拒绝的固定来源/项目规则断言，独立于冻结test40，非医学金标准。校准标签只在本地统计，不进入DeepSeek payload。脚本默认验证输入，不联网；加--run-real才显式调用，最多2次HTTP，不调用Mem0或检索。

初次20261014-185253-7057acec：接受/拒绝10/10、类别9/10；最终20261014-191104-2a7d3547：两者10/10，各1次HTTP。这是两个小样本观察；实际开发题仍有错误，见../medical-quality-v3/reviewer-observed-calibration-errors.json。clinical_review=not_run，generalization=not_established。
