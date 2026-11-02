# -*- coding: utf-8 -*-
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from app.multitier_retrieval import MultiTierKnowledgeService

def main():
    svc = MultiTierKnowledgeService()
    stats = svc.get_tier_stats()
    print("=== MULTI-TIER STATS ===")
    print(stats)
    
    test_queries = [
        ("妇产科学", "子痫前期 螺旋动脉重铸障碍 sFlt-1 硫酸镁"),
        ("儿科学", "小儿脱水 补液疗法 见尿补钾 严禁静推"),
        ("病理生理学", "弥散性血管内凝血 DIC 组织因子 消耗性低凝"),
        ("生物化学", "高尿酸血症 黄嘌呤氧化酶 别嘌醇 痛风微晶"),
        ("外科学", "急腹症 转移性右下腹痛 板状腹 膈下游离气体"),
        ("诊断学", "黄疸鉴别 溶血性黄疸 肝细胞性黄疸 胆汁淤积"),
        ("药理学", "SGLT2抑制剂 管球反馈 入球小动脉收缩 肾小球囊内压"),
        ("生理学", "颈动脉窦 主动脉弓 压力感受性反射 减压反射"),
        ("病理学", "急性心肌梗死 冠脉前降支 凝固性坏死 室壁瘤"),
        ("内科学", "急性胸痛鉴别 冠脉综合征 心电图 主动脉夹层")
    ]
    
    print("\n=== TIER 2 MULTI-SPECIALTY PROBES ===")
    for specialty, q in test_queries:
        res = svc.search_textbooks(q, limit=1)
        if res:
            top = res[0]
            print(f"[{specialty}] Hit Book: 《{top.get('book')}》 | Section: {top.get('title')} | Score: {top.get('rerank_score', 0):.4f}")
        else:
            print(f"[{specialty}] NO HIT")
            
    print("\n=== DUAL-TIER JOINT SEARCH TEST ===")
    joint = svc.search_multitier("高血压 靶器官损害 联合降压机制", guideline_limit=1, textbook_limit=1)
    print("Query:", joint["query"])
    if joint["guideline_evidence"]:
        g = joint["guideline_evidence"][0]
        print(f"Guideline hit: [{g.get('tier')}] {g.get('title')} | {g.get('section')}")
    else:
        print("Guideline hit: None (DB locked or not queried)")
    if joint["textbook_evidence"]:
        t = joint["textbook_evidence"][0]
        print(f"Textbook hit: [{t.get('tier')}] 《{t.get('book')}》 {t.get('title')}")
    else:
        print("Textbook hit: None")
        
    svc.close()
    print("\nMultiTier test finished successfully.")

if __name__ == "__main__":
    main()
