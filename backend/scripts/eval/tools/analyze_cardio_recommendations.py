# -*- coding: utf-8 -*-
import csv
import json
import sys
from pathlib import Path
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT.parent / "docs/research/cardio-zh-20261027"

def load_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

rows_104 = load_csv(DOCS_DIR / "公开全文优先下载_104份.csv")
rows_173 = load_csv(DOCS_DIR / "中文心血管文档推荐清单_173份.csv")

# 1. 系统中已有文档
current_sources = []
with open(ROOT / "knowledge/medical/sources.jsonl", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            current_sources.append(json.loads(line))

# 列出已有中文指南主题关键词
existing_zh_keys = {
    "cn-guideline-hypertension": ["2024中国高血压防治指南", "高血压防治指南(2024年修订版)", "高血压"],
    "cn-coronary": ["稳定性冠心病", "急性冠状动脉综合征", "冠心病"],
    "cn-heart-failure": ["心力衰竭诊断和治疗指南", "心力衰竭指南2024", "心衰", "GDMT"],
    "cn-dyslipidemia": ["血脂管理指南", "低密度脂蛋白", "LDL-C", "血脂"],
    "cn-stroke-emergency": ["急性缺血性卒中", "胸痛中心", "胸痛识别"],
    "cn-refractory-hypertension": ["难治性高血压", "难治性高血压诊断治疗中国专家共识"],
    "cn-hfpef-cardiomyopathy": ["射血分数保留的心力衰竭", "HFpEF", "心肌病"],
    "cn-electrolyte-arrhythmia": ["高钾血症", "心律失常", "电解质紊乱"],
    "cn-lifestyle-diet": ["高血压生活方式", "食养指南"]
}

print(f"=== 1. 104 份公开全文优先下载列表分析 ===")
p_dist = Counter(r["优先级"] for r in rows_104)
t_dist = Counter(r["主题"] for r in rows_104)
type_dist = Counter(r["文献类型"] for r in rows_104)

print("优先级分布:", dict(p_dist))
print("主题分布:", dict(t_dist))
print("文献类型分布:", dict(type_dist))

# 检查 104 份中每篇与现有库的关系
matched = []
unmatched = []

for r in rows_104:
    doc_name = r["文献名称"]
    is_covered = False
    match_source = None
    for src_id, keywords in existing_zh_keys.items():
        if any(kw in doc_name for kw in keywords):
            is_covered = True
            match_source = src_id
            break
    if is_covered:
        matched.append((r, match_source))
    else:
        unmatched.append(r)

print(f"\n现有知识库已覆盖核心主题/相同主干的文献: {len(matched)} 份")
print(f"尚未下载/尚未入库的文献: {len(unmatched)} 份")

print("\n--- 覆盖对比示例 ---")
for r, sid in matched[:5]:
    print(f"  [{r['编号']}] {r['文献名称']} ({r['年份']}) -> 对应已有 [{sid}]")

print(f"\n=== 2. 未下载文献 (共 {len(unmatched)} 份) 深入分级分析 ===")
unmatched_by_p = defaultdict(list)
for r in unmatched:
    unmatched_by_p[r["优先级"]].append(r)

for p in ["P0", "P1", "P2"]:
    docs = unmatched_by_p[p]
    print(f"\n>>> 优先级 {p} (共 {len(docs)} 份):")
    # 统计文献类型与主题
    t_cnt = Counter(d["文献类型"] for d in docs)
    sub_cnt = Counter(d["主题"] for d in docs)
    print(f"    文献类型: {dict(t_cnt)}")
    print(f"    主题: {dict(sub_cnt)}")
    # 打印前 8 份清单
    for d in docs[:8]:
        print(f"    - [{d['编号']}] ({d['年份']}) 《{d['文献名称']}》 | 类型: {d['文献类型']} | 平台: {d.get('发布/刊载平台', '')}")

# 3. 统计 173 份全量清单中无法直接下载（69 份）的特征
rows_69 = [r for r in rows_173 if not any(r["编号"] == u["编号"] for u in rows_104)]
print(f"\n=== 3. 69 份非公开/闭源期刊文献特征 ===")
print("优先级分布:", dict(Counter(r["优先级"] for r in rows_69)))
print("文献类型分布:", dict(Counter(r["文献类型"] for r in rows_69)))
print("抽样前 5 篇:")
for r in rows_69[:5]:
    print(f"  - [{r['编号']}] [{r['优先级']}] ({r['年份']}) 《{r['文献名称']}》 | 类型: {r['文献类型']} | 闭源状态: {r.get('访问状态', r.get('公开全文状态', ''))}")
