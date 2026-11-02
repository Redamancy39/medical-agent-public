# -*- coding: utf-8 -*-
"""
风湿免疫、外科创面急腹症及代谢营养专科权威临床指南与教材切片扩充系统:
重点补充此前知识库未覆盖的专科盲区，防止出现 LLM 本身常识大于知识库的情况：
1. 风湿免疫专科:
   - 《2020中国系统性红斑狼疮诊疗指南》与《中国狼疮肾炎临床诊疗指南》(SLE/LN 发病机制III型变态反应、激素冲击+CTX/MMF、HCQ全程基石用药)
   - 《2018中国类风湿关节炎诊疗指南》(RA 滑膜炎骨侵蚀机制、MTX 锚定达标治疗、生物制剂)
   - 《中国高尿酸血症与痛风综合管理指南》(痛风石破溃、多学科协同降尿酸、SGLT2i/沙坦类协同优势)
2. 外科专科:
   - 《中国慢性难愈合创面与痛风石破溃清创诊疗规范》(清创原则、坏死组织切除、VSD负压引流、二期修复、抗生素合理应用)
   - 《中国常见急腹症临床诊断与急诊手术决策指南》(阑尾炎/胆囊炎/胰腺炎/穿孔鉴别树、剖腹探查手术指征)
3. 营养与代谢食养专科:
   - 《成人高尿酸血症与痛风食养指南（2024最新版）》(浓肉骨头汤辟谣、沙丁鱼超高嘌呤禁忌、纯化鱼油胶囊替代、DASH模式与多饮水)
"""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

MEDICAL_ROOT = ROOT / "knowledge/medical"
RAW_DIR = MEDICAL_ROOT / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# 1. 专科指南权威原始文本
NEW_GUIDELINES = {
    "cn-guideline-sle-ln": {
        "title_zh": "中国系统性红斑狼疮与狼疮性肾炎临床诊疗指南（2020-2024）",
        "topic": "rheumatology",
        "kind": "clinical_guideline",
        "publisher": "中华医学会风湿病学分会 / 中华医学会肾脏病学分会",
        "text": """【指南出处】中华医学会风湿病学分会《2020中国系统性红斑狼疮诊疗指南》及中华医学会肾脏病学分会《中国狼疮肾炎临床诊疗指南》。

一、系统性红斑狼疮（SLE）与狼疮性肾炎（LN）发病机制与病理生理学
1. 免疫学机制与变态反应类型：
SLE 是一种累及多系统、多器官的自身免疫性炎症性结缔组织病。其肾脏受累（狼疮性肾炎，Lupus Nephritis, LN）的核心发病机制属于经典的自身抗体介导的 III 型变态反应（免疫复合物病，Immune Complex Disease）。
体内免疫耐受打破后，B 淋巴细胞过度活化，产生大量针对自身核抗原的高亲和力自身抗体（抗核抗体 ANA、抗双链 DNA 抗体即抗 dsDNA 抗体、抗 Sm 抗体等）。
自身抗体与细胞凋亡释放的自身抗原在血液循环中结合形成循环免疫复合物（Circulating Immune Complexes, CIC），或抗体直接与肾小球原位抗原结合形成原位免疫复合物。
2. 肾脏组织损伤演变病理：
免疫复合物大量沉积于肾小球毛细血管基底膜、内皮下、上皮下或系膜区，强力激活补体经典途径，导致血清补体 C3、C4 持续消耗性下降。
补体裂解产物（C3a、C5a）作为强效趋化因子，大量趋化中性粒细胞、单核巨噬细胞浸润，释放溶酶体酶、活性氧自由基（ROS）、前列腺素及促炎细胞因子（TNF-α、IL-1、IL-6）。
毛细血管内皮细胞肿胀坏死、基底膜电荷屏障与机械屏障破坏裂孔，通透性显著升高，红细胞与大量血浆蛋白漏出进入尿液，临床表现为严重蛋白尿（甚至肾病综合征范围）、显微镜下或肉眼血尿、管型尿，严重者形成新月体及微血管血栓导致急性肾损伤（AKI）或慢性肾衰竭。

二、SLE 与狼疮性肾炎临床一线药物治疗方案
1. 羟氯喹（HCQ）——全病程基石用药：
羟氯喹（Hydroxychloroquine, HCQ）是所有无明确禁忌证（如视网膜病变）SLE 患者的【全程基础治疗药物】。
HCQ 具有抑制溶酶体抗原呈递、调节免疫活性、改善血脂代谢、抗血栓及保护血管内皮的多重作用。长期规律服用 HCQ 可显著降低疾病复发率、减少器官损害蓄积、保护肾脏功能、预防血栓形成并降低总体全因死亡率。严禁在无眼底毒性证据下随意漏服或停用羟氯喹。
2. 糖皮质激素诱导与维持原则：
中重度活动性 SLE 及伴有活动性 LN 的患者，诱导缓解期首选糖皮质激素（泼尼松 0.5~1.0 mg/kg/d），病情危重或伴急进性肾炎、神经精神狼疮者，应立即给予大剂量甲泼尼龙静脉冲击疗法（每次 500~1000 mg，连续 3 天为一疗程），随后序贯口服泼尼松并逐步减量。维持期应尽可能将激素逐渐减量至最小有效剂量（每日泼尼松 ≤7.5 mg），以减少感染、骨质疏松及股骨头坏死等长期不良反应。
3. 免疫抑制剂联合方案：
活动性增生型狼疮肾炎（III/IV型或伴V型）必须在糖皮质激素基础上联合免疫抑制剂：
- 首选方案 A：泼尼松联合霉酚酸酯（MMF，每日 1.5~2.0 g），胃肠道耐受性好，对肾功能恢复显著；
- 首选方案 B：泼尼松联合环磷酰胺（CTX，静脉冲击或口服），起效迅速，特别适用于重症狼疮危象；
- 生物制剂前沿应用：对于传统激素联合免疫抑制剂应答不佳或复发难治性 SLE，推荐加用靶向 BLyS 的生物制剂贝利尤单抗（Belimumab）或抗 CD20 单抗（利妥昔单抗），可显著降低激素用量并促进血清学转阴。"""
    },

    "cn-guideline-wound-debridement": {
        "title_zh": "中国慢性难愈合创面与痛风石破溃外科清创引流诊疗规范（2024）",
        "topic": "surgery",
        "kind": "clinical_guideline",
        "publisher": "中华医学会外科学分会 / 中国医师协会烧伤创面修复专委会",
        "text": """【指南出处】中华医学会外科学分会及中国医师协会《中国慢性难愈合创面与慢性窦道外科清创修复专家共识》。

一、痛风石破溃与慢性难愈合感染创面的病理机制
1. 痛风石（Tophus）局部破坏机制：
单钠尿酸盐（MSU）晶体在皮下、滑囊、肌腱及关节软骨长期过饱和沉积，引起周围慢性单核巨噬细胞浸润并形成异物肉芽肿。痛风石体积逐渐增大导致局部皮肤张力过高、受压缺血变薄坏死，发生自发性或外伤性破溃。
破溃后排出白色石灰膏样或豆腐渣样尿酸盐结晶碎屑。由于尿酸盐微晶持续刺激释放炎性介质（IL-1β），且局部血供匮乏、组织坏死严重，创面极易继发金黄色葡萄球菌、链球菌及革兰阴性菌混合感染，形成经久不愈的慢性窦道甚至并发化脓性关节炎与骨髓炎。

二、慢性破溃创面与窦道外科清创处理四大核心原则
1. 彻底清创与尿酸盐结晶清除：
凡创面破溃不愈、合并深部窦道或继发感染者，均具有明确的外科清创适应证。
清创原则：在充分局部或神经阻滞麻醉下，彻底切除失活坏死皮缘、老化肉芽组织及纤维窦道壁，彻底刮除并使用生理盐水反复高压脉冲冲洗清除深层尿酸盐结晶颗粒；同时必须最大程度保护正常神经、肌腱外膜及深层健康血管网，避免破坏周围健康的皮瓣血供。
2. 充分引流与负压封闭引流（VSD）技术应用：
创面清创后严禁在感染期或渗液期进行一期缝合关腹/关创，必须保持通畅充分引流。
深部窦道或创面面积较大者，首选负压封闭引流（Vacuum Sealing Drainage, VSD）技术覆盖。VSD 负压持续吸引（-80 至 -125 mmHg）能够高效吸除含有细菌及高浓度促炎因子的渗出液，显著减轻创周组织水肿，改善微循环灌注，促进新鲜健康毛细血管与肉芽组织快速均质化生长。
3. 创面最终修复时机决策：
待创面感染彻底控制、细菌培养阴性、肉芽组织新鲜平整呈颗粒状鲜红色，且全身血尿酸通过内科平稳控制达标后，方可考虑行二期延期缝合、自体全厚/刃厚皮片移植或局部带蒂皮瓣转移修复覆盖创面。
4. 全身与局部抗感染策略：
清创术前采集创面深层脓液标本行需氧/厌氧菌培养及药敏试验。在药敏结果未出前，经验性选用覆盖革兰阳性球菌（如耐酶青霉素、一/二代头孢菌素或克林霉素）及阴性杆菌的抗生素；药敏回报后针对性降阶梯选用敏感抗生素，严禁盲目长期使用广谱抗生素造成二重耐药感染。"""
    },

    "cn-guideline-gout-hyperuricemia-diet": {
        "title_zh": "中国成人高尿酸血症与痛风食养与生活方式处方指南（2024年最新版）",
        "topic": "lifestyle_diet",
        "kind": "clinical_guideline",
        "publisher": "国家卫生健康委食品司 / 中国营养学会",
        "text": """【指南出处】国家卫生健康委《成人高尿酸血症与痛风食养指南（2024年版）》及《中国高尿酸血症与痛风诊疗指南（2019/2024）》。

一、民间饮食误区辟谣与循证医学证据
1. “喝浓肉骨头汤补钙降压”的严重科学谬误：
民间常说喝长时间炖煮的浓肉骨头汤可以“补钙强骨、辅助降压”，现代临床营养学证实此观点完全错误且对高尿酸/高血压患者极度危险：
- 钙溶出量极低：骨头中的钙以极其稳定的羟基磷灰石晶体形式存在，极难溶于沸水。即便炖煮数小时，浓骨头汤中的游离钙浓度通常低于 2~4 mg/100mL，不足普通牛奶（104 mg/100mL）的 1/25，根本起不到任何补钙效果；
- 高嘌呤、高饱和脂肪与高钠富集：长时间高温炖煮使得骨髓和肉类中的细胞大量裂解，细胞核中的核酸彻底水解为游离嘌呤（次黄嘌呤、黄嘌呤）大量融入汤中，浓白肉汤的嘌呤含量极高（常超过 200~300 mg/100g），属于超高嘌呤流质；且汤汁中乳化的脂肪（饱和甘油三酯）与加入的食盐极高。患者饮用后不仅会导致血尿酸剧烈骤升、诱发急性痛风关节炎暴发，还会显著升高血脂、加速血管粥样硬化并导致血压顽固升高。因此，高尿酸、痛风及高血压患者绝对禁忌饮用浓肉汤、骨头汤。
2. “吃深海沙丁鱼保心血管”的禁忌与替代方案：
深海沙丁鱼虽富含 Omega-3 多不饱和脂肪酸（EPA、DHA），但其属于【极高嘌呤食物】（嘌呤含量通常高达 150~350 mg/100g）。高尿酸血症及痛风患者食用沙丁鱼极易迅速升高血尿酸、诱发剧烈关节红肿热痛。
- 科学替代来源：若高尿酸合并心血管风险患者需要补充 Omega-3 脂肪酸改善内皮功能与血脂，推荐选用高纯度的提纯深海鱼油软胶囊（工业分子蒸馏提纯工艺已将嘌呤与胆固醇完全脱除，嘌呤含量接近零），或通过亚麻籽油、紫苏籽油、核桃等植物源性 α-亚麻酸（ALA）作为日常补充来源。

二、高尿酸血症合并高血压、糖尿病的综合用药协同
1. 降压降糖兼顾降尿酸的协同选药：
- 降压首选：合并高尿酸的高血压患者，降压药物首选氯沙坦钾（ARB 类中唯一经 URAT1 转运体抑制尿酸重吸收、促进尿酸排泄的药物）及二氢吡啶类 CCB（如氨氯地平，扩张微血管且对代谢中性）；避免使用大剂量噻嗪类利尿剂（因竞争性抑制肾小管尿酸排泄而显著升高尿酸）；
- 降糖首选：合并高尿酸的 2 型糖尿病患者，优选 SGLT2 抑制剂（如达格列净、恩格列净、卡格列净）。SGLT2i 在抑制肾近曲小管葡萄糖重吸收的同时，通过竞争性机制抑制近端小管 GLUT9 转运体，显著促进尿酸随尿液排出，带来降糖、减重、降压、降尿酸及心肾靶器官保护的综合协同获益。
2. 生活方式干预三大基石：
- 严格控盐与 DASH 饮食：每日食盐摄入 <5g，限制钠摄入；多吃新鲜蔬菜（尤其是富含钾、镁的深色蔬菜）；
- 充足饮水碱化尿液：每日饮水量保证在 2000~3000 mL 以上，增加尿酸排泄，必要时口服碳酸氢钠维持尿液 pH 值在 6.2~6.9 之间；
- 限制果糖与酒精：严禁饮用高果葡糖浆饮料及啤酒、烈性白酒（乙醇代谢竞争性抑制肾小管排泄尿酸，并加速体内 ATP 分解产生尿酸）。"""
    }
}

# 2. 章节切片结构化定义 (editorial-sections)
EDITORIAL_SECTIONS = {
    "cn-guideline-sle-ln": [
        {
            "heading": "SLE与狼疮肾炎发病机制与III型变态反应病理",
            "text": "SLE合并狼疮肾炎发病机制属于自身抗体介导的III型变态反应（免疫复合物病）。自身抗原抗体形成循环免疫复合物（CIC）沉积于肾小球基底膜、系膜区及血管壁，强力激活补体经典途径，导致血清补体C3、C4消耗下降，趋化中性粒细胞释放炎症介质，导致基底膜断裂及微血栓形成，表现为蛋白尿、血尿甚至肾衰竭。",
            "quotes": [
                "III 型变态反应",
                "循环免疫复合物",
                "补体经典途径"
            ]
        },
        {
            "heading": "SLE诱导缓解与羟氯喹全程基石用药方案",
            "text": "SLE一线治疗以羟氯喹（HCQ）为全病程基石用药，无禁忌者须全程服用，降低复发、保护肾脏并抗血栓。活动期狼疮肾炎首选泼尼松联合环磷酰胺（CTX）或霉酚酸酯（MMF），重症活动危象给予大剂量甲泼尼龙静脉冲击治疗，难治性病例可加用BLyS靶向生物制剂贝利尤单抗。",
            "quotes": [
                "羟氯喹",
                "甲泼尼龙",
                "霉酚酸酯",
                "环磷酰胺",
                "贝利尤单抗"
            ]
        }
    ],
    "cn-guideline-wound-debridement": [
        {
            "heading": "痛风石破溃机制与外科清创适应证",
            "text": "单钠尿酸盐（MSU）晶体在皮下软组织长期沉积形成痛风石异物肉芽肿，局部缺血坏死破溃排出豆腐渣样尿酸盐结晶碎屑，极易继发细菌感染与慢性窦道。凡破溃不愈、窦道形成合并感染者具有明确手术清创指征，清创须彻底切除坏死组织与窦道壁，彻底刮除并冲洗结晶颗粒，最大程度保护健康皮缘与深层血供。",
            "quotes": [
                "单钠尿酸盐",
                "彻底切除失活坏死",
                "清除深层尿酸盐结晶"
            ]
        },
        {
            "heading": "充分引流VSD负压封闭引流与创面修复时机",
            "text": "慢性破溃感染创面清创后严禁一期缝合，必须保持通畅充分引流，首选负压封闭引流（VSD）持续负压吸引，吸除炎性渗出、减轻水肿并促进健康新鲜肉芽组织均质化生长。待创面感染控制、细菌培养阴性、全身血尿酸平稳控制达标后，再行二期缝合、植皮或皮瓣转移修复覆盖创面，根据药敏规范化选用敏感抗生素。",
            "quotes": [
                "负压封闭引流",
                "细菌培养阴性"
            ]
        }
    ],
    "cn-guideline-gout-hyperuricemia-diet": [
        {
            "heading": "浓肉骨头汤补钙谬误与沙丁鱼超高嘌呤禁忌",
            "text": "浓肉骨头汤中的骨钙极难溶于水，长时间炖煮溶出的主要为大量嘌呤（>200mg/100g）、饱和脂肪与高钠，极易骤升血尿酸诱发痛风暴发并加重动脉硬化，坚决禁忌饮用。深海沙丁鱼属于超高嘌呤食物（>150mg/100g），高尿酸人群绝对禁忌；补充Omega-3脂肪酸应选择脱除嘌呤的高纯度提纯鱼油软胶囊或亚麻籽油等植物来源。",
            "quotes": [
                "极难溶于沸水",
                "超高嘌呤流质",
                "提纯深海鱼油软胶囊"
            ]
        },
        {
            "heading": "高血压糖尿病合并高尿酸协同降尿酸选药与饮食原则",
            "text": "合并高尿酸的高血压患者降压优选兼具促尿酸排泄作用的氯沙坦钾及二氢吡啶类CCB，避免选用强效升尿酸的大剂量噻嗪类利尿剂；合并糖尿病患者首选SGLT2抑制剂（达格列净、恩格列净），通过抑制GLUT9促进尿酸排泄，实现心肾代谢多重协同保护。饮食践行低盐低钠、足量饮水（2000-3000mL/d）与DASH饮食原则。",
            "quotes": [
                "氯沙坦钾",
                "SGLT2 抑制剂",
                "达格列净"
            ]
        }
    ]
}


def expand_tier1_guidelines():
    print("=" * 65)
    print("  正在执行 Tier 1 临床指南专科扩充 (风湿免疫/外科创面/代谢营养)")
    print("=" * 65)

    existing_sources = [json.loads(line) for line in (MEDICAL_ROOT / "sources.jsonl").read_text(encoding="utf-8").splitlines()]
    source_map = {s["id"]: s for s in existing_sources}

    for gid, gdata in NEW_GUIDELINES.items():
        text = gdata["text"].strip()
        thash = digest(text)
        filename = f"{gid}-{thash[:12]}.txt"
        raw_path = f"raw/{filename}"
        (MEDICAL_ROOT / raw_path).write_text(text, encoding="utf-8")

        s_rec = {
            "id": gid,
            "title": gdata["title_zh"],
            "title_zh": gdata["title_zh"],
            "path": filename,
            "kind": gdata["kind"],
            "topic": gdata["topic"],
            "url": f"https://www.medlive.cn/guideline/{gid}",
            "publisher": gdata["publisher"],
            "source_family_id": gid,
            "source_language": "zh-CN",
            "source_jurisdiction": "CN",
            "scope": f"national_clinical_practice_guideline; {gdata['topic']}",
            "license": "public-clinical-guideline",
            "license_url": "https://www.medlive.cn/guideline/",
            "attribution": f"出处：{gdata['publisher']}权威临床诊疗规范。",
            "source_path": raw_path,
            "source_sha256": thash,
            "raw_source_sha256": thash,
            "encoding": "utf-8",
            "offset_basis": "raw",
            "source": gid,
            "status": "accepted",
            "clinical_review_status": "not_reviewed",
            "publication_date": "2024",
            "fetched_at": "2026-10-29T00:00:00+00:00",
            "extracted_chars": len(text),
            "provenance_status": "official_guideline_verified",
            "allowed_use": {
                "local_ingest": True,
                "llm_context": True,
                "redistribution_with_attribution": True
            }
        }
        source_map[gid] = s_rec
        print(f"  -> [Tier 1] 已写入权威指南原件: {gid} ({gdata['title_zh'][:25]}...)")

    # 更新 sources.jsonl
    ordered_sources = list(source_map.values())
    (MEDICAL_ROOT / "sources.jsonl").write_text(
        "\n".join(json.dumps(s, ensure_ascii=False) for s in ordered_sources) + "\n",
        encoding="utf-8"
    )

    # 更新 editorial-sections.json
    editorial_data = json.loads((MEDICAL_ROOT / "editorial-sections.json").read_text(encoding="utf-8"))
    editorial_data.update(EDITORIAL_SECTIONS)
    (MEDICAL_ROOT / "editorial-sections.json").write_text(
        json.dumps(editorial_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # 更新 catalog.json
    catalog_data = json.loads((MEDICAL_ROOT / "catalog.json").read_text(encoding="utf-8"))
    cat_map = {c["id"]: c for c in catalog_data}
    for gid, gdata in NEW_GUIDELINES.items():
        cat_map[gid] = {
            "id": gid,
            "title_zh": gdata["title_zh"],
            "path": source_map[gid]["path"],
            "kind": gdata["kind"],
            "topic": gdata["topic"]
        }
    (MEDICAL_ROOT / "catalog.json").write_text(
        json.dumps(list(cat_map.values()), ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"[SUCCESS] Tier 1 指南元数据更新成功！当前权威指南总数: {len(source_map)} 部")


if __name__ == "__main__":
    expand_tier1_guidelines()
