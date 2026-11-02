# -*- coding: utf-8 -*-
"""Test retrieval across diverse Chinese medical domains (Batch 1 + Batch 2)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from app.knowledge import BGEEmbedding, KnowledgeStore, LocalReranker

def main():
    emb = BGEEmbedding(ROOT / "data/models")
    rerank = LocalReranker("D:/rag_project/models/reranker/bge-reranker-v2-m3")
    store = KnowledgeStore(ROOT / "data/knowledge_medical_v1.db", emb, rerank)

    queries = [
        ("心内科-冠心病", "心绞痛发作 硝酸甘油 含服 禁忌 西地那非 低血压"),
        ("心内科-心衰", "心力衰竭 NYHA分级 新四联 沙库巴曲缬沙坦 达格列净 螺内酯"),
        ("心血管-血脂", "血脂异常 ASCVD LDL-C 达标值 他汀 依折麦布 PCSK9"),
        ("内分泌-痛风", "高尿酸血症 420 痛风发作 秋水仙碱 降尿酸 达标 360"),
        ("呼吸科-慢阻肺", "慢性阻塞性肺疾病 肺功能 FEV1/FVC 吸入 LAMA 噻托溴铵 家庭氧疗"),
        ("呼吸科-哮喘", "支气管哮喘 舒张试验 FEV1 增加 12% 200ml ICS 福莫特罗"),
        ("消化科-反流病", "反流性食管炎 烧心 反酸 PPI试验 伏诺拉生 LA分级"),
        ("消化科-脂肪肝", "非酒精性脂肪性肝病 腹部超声 明亮肝 减重 5% 10% FIB-4"),
        ("神经科-帕金森", "帕金森病 运动迟缓 静止性震颤 复方左旋多巴 老年禁用苯海索"),
        ("肿瘤科-防癌筛查", "肺癌 50岁 吸烟 20包年 低剂量螺旋CT 结肠镜 筛查"),
        ("药理-抗感染规范", "外科清洁手术 预防性使用抗生素 术前切开前 0.5至1小时 降阶梯"),
        ("儿科-发热用药", "儿童发热 38.5度 对乙酰氨基酚 布洛芬 剂量 严禁阿司匹林"),
        ("急诊-脑卒中", "突发口角歪斜 手臂无力 脑卒中 BE FAST 4.5小时溶栓"),
        ("心内科-难治性高血压", "难治性高血压 吃了三种降压药包含利尿剂 血压不达标 螺内酯 四联用药"),
        ("心内科-HFpEF射血保留", "射血分数保留心衰 HFpEF 达格列净 恩格列净 利尿剂抵抗 托伐普坦"),
        ("内分泌-糖尿病急症DKA", "糖尿病酮症酸中毒 DKA 补液 生理盐水 见尿补钾 小剂量胰岛素"),
        ("内分泌-糖尿病肾病DKD", "糖尿病肾病 尿微量白蛋白 UACR 30到300 早期筛查 厄贝沙坦 非奈利酮"),
        ("内分泌-甲状腺疾病", "甲亢 甲巯咪唑 发热咽痛 粒细胞缺乏停药 甲减 左甲状腺素钠 空腹 妊娠TSH"),
        ("急诊-高钾血症救治", "血钾高于6.0 高钾血症 葡萄糖酸钙 稳定心肌 胰岛素加葡萄糖 严禁直接推注氯化钾")
    ]

    print("=" * 65)
    all_passed = True
    for category, q in queries:
        hits = store.search(q, limit=1)
        if hits:
            top = hits[0]
            score = top.get('rerank_score', 0)
            print(f"【{category}】")
            print(f"  查询: {q}")
            print(f"  命中: [{top['document_id']}] {top.get('title')}")
            print(f"  章节: {top.get('section')}")
            print(f"  重排得分: {score:.4f}")
            if score < 0.5:
                all_passed = False
        else:
            print(f"【{category}】 未命中！")
            all_passed = False
        print("-" * 65)

    store.close()
    print("全部专科检索测试完成，整体命中质量:", "100% 优异" if all_passed else "部分待调优")

if __name__ == "__main__":
    main()
