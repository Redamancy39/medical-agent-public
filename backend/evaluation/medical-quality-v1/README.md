# 医学逐项来源审查 v1

这是冻结medical-v1之外的开发审查记录，不是新医学金标准，也未覆盖test40。原dev/test/manifest和正式语料不改。

- `dev-reference-review-v1.json`：Codex依据固定原文逐项审查dev20的60条参考要点，区分医学事实、项目行为与当前语料范围；全部专业复核pending。
- `dev-reference-report-v1.json`：程序校验原文hash、Unicode LF字符位置和quote；34条医学事实中28条所需审查引文未被旧绑定范围完整覆盖、6条完整覆盖，26条为政策/范围。全文支持草稿不等于原绑定正确或临床金标准成立。
- `observed-dev10-v1.json`：4题J批旧运行与6题K批新运行，保留每题run_id。两次观察不能合并称本次10题新模型试验；另10道dev未生成回答。K新6题5完成/1失败，J旧4题4完成。
- `dev-answer-review-v1.json`：按实际答案字符范围逐句审查63项，保留数值、单位与条件，且不能删掉未获支持句子。36项医学事实草稿审查中21项全文支持、12项部分支持、3项当前原文无支持；其余27项是政策/范围/编辑或失败说明。
- `dev-answer-report-v1.json`：来源版本、引用片段正文和quote逐项验证；医学引用29项需补绑定、4项完整绑定、3项无支持。临床准确率始终null，professional review未开展。

“全文支持”是Codex的逐原文审查建议。程序只验证版本、字节/字符位置与quote真实存在，不能判定医学蕴含或临床正确；support_status不是程序按关键词推断。“citation_gap”表示审查使用的完整引文不在当前绑定范围内；引文较长时也会触发，不能把28/29当自动认定的医学错误数量。“unsupported”仅限定当前固定正式语料，不等于医学结论已被反驳。NHS等新候选的支持需分开核对与准入。

```powershell
# 在backend目录执行：只读现有资料与运行报告，不读取.env、不调用模型、Mem0或Milvus。
.\.venv\Scripts\python.exe scripts/review_medical_quality.py --review evaluation/medical-quality-v1/dev-reference-review-v1.json --output ..\tmp\reference-review-new.json
# 从真实观察生成全部pending的句子模板，不会自动判正确。
.\.venv\Scripts\python.exe scripts/review_medical_quality.py --report evaluation/medical-quality-v1/observed-dev10-v1.json --output ..\tmp\answer-template-new.json
# 回读实际填好的逐项审查，校验所有非空白答案字符都被覆盖。
.\.venv\Scripts\python.exe scripts/review_medical_quality.py --report evaluation/medical-quality-v1/observed-dev10-v1.json --review evaluation/medical-quality-v1/dev-answer-review-v1.json --output ..\tmp\answer-review-new.json
```

输出路径已存在时拒绝覆盖。未提交的参考审查补pending；未观察的开发题保留unobserved；小数6.5不会因ASCII句点被拆开。假引文、陈旧基线、答案修改、遗漏/重复覆盖、伪造来源内容、专业审核passed及test题审查均拒绝。

运行时当前仍是工程证据门禁，不是逐事实医学Reviewer。K批新增最小紧急风险规则出口，跳过外部上下文与Agent，response_origin=urgent_policy；该路径与修复前的真实观察另行统计，旧危险扩展答案保留为缺陷证据。下一步开展独立开发修订、实时claims到来源映射、补证据/降级与完整dev覆盖；不把临床审查自动化包装为已完成。
