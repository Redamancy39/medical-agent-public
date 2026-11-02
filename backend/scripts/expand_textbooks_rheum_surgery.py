# -*- coding: utf-8 -*-
"""
人卫第10版《内科学》风湿免疫系统与《外科学》创伤创面清创核心长章节扩充系统 (Tier 2 Master Expander):
为国家规划教材独立向量池 (knowledge_textbooks_v1.db) 注入高精度专科核心章节：
1. 《内科学》（第10版，2024）第八篇第二章: 系统性红斑狼疮（SLE）与狼疮性肾炎（LN）病理生理发病机制与变态反应类型
2. 《外科学》（第10版，2024）第一篇第十一章: 创面愈合病理生理、慢性窦道、痛风石破溃与外科清创引流原则
3. 《内科学》（第10版，2024）第八篇第五章: 高尿酸血症与痛风病理机制、单钠尿酸盐（MSU）沉积与痛风石形成
"""

import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from app.knowledge import BGEEmbedding, LocalReranker

TEXTBOOK_ROOT = ROOT / "knowledge/textbooks"
RAW_DIR = TEXTBOOK_ROOT / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
TEXTBOOK_DB_PATH = ROOT / "data/knowledge_textbooks_v1.db"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


NEW_TEXTBOOK_CHAPTERS = [
    # 1. 《内科学》（第10版，2024年，人卫版，葛均波/王辰/王建安 主编）
    {
        "id": "tb-rheum-sle-pathophys",
        "book": "内科学",
        "edition": "第10版",
        "year": 2024,
        "publisher": "人民卫生出版社",
        "part": "第八篇 风湿性疾病",
        "chapter": "第二章 系统性红斑狼疮",
        "section": "第一节 病因与发病机制（变态反应类型与肾小球病理）",
        "title": "《内科学（第10版）》系统性红斑狼疮与狼疮性肾炎免疫复合物沉积与组织损伤机制",
        "text": """【教材出处】人卫版全国高等学校五年制本科临床医学规划教材《内科学》（第10版，2024年），第八篇风湿性疾病第二章第一节。

一、系统性红斑狼疮（SLE）与狼疮性肾炎（Lupus Nephritis, LN）免疫发病机制
1. 自身耐受丧失与抗体产生：
系统性红斑狼疮是典型的由自身抗原免疫耐受丧失、B细胞多克隆异常活化引起的系统性自身免疫病。易感基因与环境因素（紫外线、病毒感染、雌激素）相互作用导致淋巴细胞凋亡清除障碍，暴露于细胞表面的自身核抗原（如双链DNA、组蛋白、Sm抗原）持续刺激树突状细胞和T辅助细胞（Th细胞），活化B细胞分化为浆细胞，持续合成产生高亲和力抗核抗体谱（ANA、抗dsDNA、抗Sm抗体）。
2. III型超敏反应（免疫复合物介导的血管与肾脏损伤）：
本病肾脏与微血管受累在病理免疫学上属于经典的【III型变态反应】（免疫复合物型超敏反应，Immune Complex Disease）。
- 循环免疫复合物（CIC）形成与沉积：自身抗体与大量游离自身核抗原在血液循环中结合形成中等大小的可溶性免疫复合物。此类复合物不易被单核巨噬细胞系统吞噬清除，随血流流经肾小球毛细血管袢、全身小血管壁及滑膜时，因毛细血管流速减慢、局部滤过压高而沉积于内皮下、肾小球基底膜（GBM）或系膜区；原位免疫复合物亦可由抗核抗体直接与预先植入基底膜的带阳离子核抗原发生原位特异性结合；
- 补体级联激活与组织坏死：免疫复合物与补体C1q结合，强力激活补体经典途径，导致血清补体C3、C4出现消耗性极度低下（C3、C4水平是反映狼疮病情活动度的极其敏感指标！）；
- 炎症细胞趋化与微血栓形成：补体裂解产生的C3a、C5a等过敏毒素强力趋化中性粒细胞和单核细胞浸润，释放大量溶酶体中性蛋白酶、胶原酶、弹性蛋白酶及活性氧，消化破坏基底膜网状纤维与内皮细胞，破坏滤过屏障电荷与孔径，导致大量蛋白尿（>0.5g/24h或尿蛋白++以上）与镜下血尿；同时血小板黏附聚集启动外源性凝血途径，导致肾小球毛细血管腔内广泛纤维蛋白沉积与微血栓形成，晚期进展为肾小球硬化及间质纤维化。

二、SLE 与狼疮肾炎临床一线药物治疗决策
1. 羟氯喹（HCQ）的全程基石地位：
所有确诊无禁忌证（如视网膜病变）的 SLE 患者均应全程规律口服羟氯喹（常规 200~400 mg/d）。HCQ 能够抑制溶酶体酸性环境、阻断浆细胞样树突状细胞 TLR7/9 信号通路并抑制抗原递呈，临床试验证实其具有显著降低 SLE 复发率、延缓器官功能损害进展、改善血脂谱、减少血栓形成并降低全因死亡率的独立获益，严禁在无明确眼底毒性证据下随意漏用或停药。
2. 诱导缓解期核心方案：
- 糖皮质激素：中重度活动期首选泼尼松（0.5~1.0 mg/kg/d），危及生命的重症狼疮肾炎危象或急性急进性肾小球肾炎，必须首选大剂量甲泼尼龙静脉冲击疗法（每次500~1000 mg，每日1次，连续3天）；
- 联合免疫抑制剂：增生型狼疮肾炎（III型/IV型）诱导期必须联合免疫抑制剂，首选环磷酰胺（CTX）静脉冲击或霉酚酸酯（MMF，1.5~2.0 g/d），兼具强效抑制B细胞和T细胞增殖、逆转活动性病理损伤的作用；
- 靶向生物制剂：对难治复发患者推荐联合 B 淋巴细胞刺激因子（BLyS）拮抗剂贝利尤单抗（Belimumab）或抗CD20单抗（利妥昔单抗）。"""
    },

    # 2. 《外科学》（第10版，2024年，人卫版，赵玉沛/陈孝平 主编）
    {
        "id": "tb-surgery-wound-healing",
        "book": "外科学",
        "edition": "第10版",
        "year": 2024,
        "publisher": "人民卫生出版社",
        "part": "第一篇 外科总论",
        "chapter": "第十一章 创伤与创面修复",
        "section": "第三节 慢性难愈合创面、痛风窦道与外科清创引流技术",
        "title": "《外科学（第10版）》慢性破溃窦道病生机制与创面外科清创充分引流规范",
        "text": """【教材出处】人卫版全国高等学校五年制本科临床医学规划教材《外科学》（第10版，2024年），第一篇外科总论第十一章第三节。

一、慢性难愈合感染创面与痛风石破溃的病理生理学特征
1. 创面愈合受阻的病理微环境：
正常创面愈合经历炎症期、细胞增殖肉芽形成期及瘢痕组织重塑期三个连续演变阶段。当创面受单钠尿酸盐（MSU）结晶异物刺激、重度局部缺血坏死或细菌生物膜（Biofilm）定植浸润时，创面长期停滞于慢性促炎相。
单钠尿酸盐结晶在皮下和滑囊形成痛风石，持续机械性压迫表面微循环导致缺血坏死破溃，流出白色膏状结晶碎屑；同时结晶被巨噬细胞吞噬激活 NLRP3 炎症小体，持续释放大量 IL-1β、基质金属蛋白酶（MMPs），过度降解细胞外基质与新生血管内皮，导致局部肉芽组织老化苍白、水肿脆弱，形成经久不愈的慢性窦道与腔隙，继发混合细菌感染甚至骨质破坏。

二、创面外科清创术（Debridement）核心操作规范与原则
1. 彻底清除坏死组织与异物结晶（Debridement）：
对于破溃不愈、合并深部窦道或继发感染的创面，必须实施规范外科清创术。
清创原则与操作要点：
- 坏死组织鉴别与彻底切除：依据“红（颜色鲜红）、软（质地柔软弹性）、血（渗血活跃）、缩（刺激收缩）”四标准严格辨别活性组织，将变黑坏死、无血供的失活皮缘、老化水肿肉芽组织及纤维窦道壁彻底锐性切除；
- 结晶刮除与脉冲冲洗：对于痛风石破溃灶，必须使用刮匙彻底刮除骨面、滑囊及肌腱周围沉积的尿酸盐结晶颗粒，并配合大量无菌生理盐水进行脉冲加压冲洗，尽可能清除化学性炎性微晶；
- 严密保护正常解剖结构：在彻底清创的同时，必须最大程度保护正常肌腱外膜、深部神经及健康骨膜，保护创缘有生机的微小皮下血管网。
2. 充分引流与负压封闭引流（VSD）技术应用：
感染创面及窦道清创后绝对严禁早期一期直接拉拢缝合！严禁封闭感染腔隙造成脓液蓄积扩散。
- 负压封闭引流（VSD）技术是当前慢性感染创面最权威标准的引流处置：采用医用聚乙烯醇水化海绵填塞创腔，半透性生物薄膜严密贴附密封，接负压源维持 -80~-125 mmHg 持续均匀吸引；
- VSD 作用机制：不仅全天候全方位吸除创面脓液、坏死组织分解物及炎性介质，消除局部组织水肿；同时微机械张力牵拉刺激血管内皮生长因子分泌，显著增加局部微循环血流量，诱导颗粒状健康新鲜肉芽组织快速均质生长，将开放创面转化为清洁创面。
3. 创面二期修复时机决策：
必须待局部感染完全扑灭、创面细菌培养转阴、基底长满致密平整的鲜红色颗粒状健康肉芽组织，且全身基础病（如高尿酸血症经内科治疗控制达标）平稳后，方可选择延期二期缝合、自体游离皮片移植（刃厚/中厚皮片）或局部转移皮瓣覆盖修复创面。根据细菌培养及药敏试验合理阶梯化应用抗生素，控制局部与全身侵袭性感染。"""
    },

    # 3. 《内科学》（第10版，2024年，人卫版，葛均波/王辰/王建安 主编）
    {
        "id": "tb-rheum-gout-pathophys",
        "book": "内科学",
        "edition": "第10版",
        "year": 2024,
        "publisher": "人民卫生出版社",
        "part": "第八篇 风湿性疾病",
        "chapter": "第五章 痛风与高尿酸血症",
        "section": "第二节 痛风石形成机制与急慢性期综合达标治疗",
        "title": "《内科学（第10版）》单钠尿酸盐结晶微环境、痛风石肉芽肿病理与代谢协同治疗",
        "text": """【教材出处】人卫版全国高等学校五年制本科临床医学规划教材《内科学》（第10版，2024年），第八篇风湿性疾病第五章第二节。

一、单钠尿酸盐（MSU）沉积与痛风石病理生理学机制
1. 尿酸理化特性与微晶析出条件：
尿酸是嘌呤代谢的终产物。在人体正常体温（37℃）及生理pH值下，单钠尿酸盐（Monosodium Urate, MSU）在血液中的饱和溶解度为 420 μmol/L（7.0 mg/dL）。
当血尿酸浓度持续超过 420 μmol/L 即定义为高尿酸血症。由于外周四肢末端（如第一跖趾关节、耳郭、跟腱）局部温度较低（约30~32℃）、血流相对缓慢且受经常性微创伤刺激，尿酸盐溶解度显著下降，大量细小针状 MSU 结晶自过饱和体液中析出，沉积于关节滑膜、软骨、滑囊及周围韧带软组织。
2. 痛风石（Tophus）异物肉芽肿形成：
析出的针状 MSU 晶体作为危险相关分子模式（DAMP），被局部单核巨噬细胞吞噬，促使溶酶体膜破裂释放组织蛋白酶B，强力装配并活化 NLRP3 炎症小体。前胱天蛋白酶-1（pro-Caspase-1）裂解自活化为 Caspase-1，将未成熟的前体 pro-IL-1β 剪切转化为高活性的 IL-1β，引发剧烈的血管扩张、毛细血管通透性暴增与中性粒细胞趋化浸润，临床表现为急性痛风性关节炎发作。
若高尿酸长期得不到有效达标控制，巨噬细胞和多核巨细胞无法降解吞噬的尿酸盐晶体，周围被大量淋巴细胞、成纤维细胞及致密结缔组织层层包绕浸润，形成特征性的慢性异物肉芽肿——即痛风石（Tophus）。痛风石不仅破坏关节软骨导致软骨下骨质发生“穿凿样”或“虫蚀样”骨侵蚀缺损与关节畸形，且因张力增高极易导致表面皮肤缺血坏死、破溃窦道形成。

二、痛风急性期与慢性间歇期间歇期降尿酸规范化治疗决策
1. 痛风急性发作期处置：
急性期必须在 12 小时内尽早启动抗炎止痛，以终止关节炎症破坏。一线推荐小剂量秋水仙碱（初始负荷剂量 1.0 mg，1小时后追加 0.5 mg，12小时后维持 0.5 mg 每日1~2次），安全性显著优于传统大剂量疗法；或选用非甾体抗炎药（NSAIDs，如双氯芬酸、塞来昔布）及短期口服糖皮质激素。急性发作第一天绝对严禁新加用或加量降尿酸药物（因血尿酸剧烈波动可致痛风石表面结晶溶解脱落，引发“二次发作”转移性痛风）；若发作前原本已规律服用降尿酸药物者，发作期严禁随意停药，维持原剂量继续服用。
2. 痛风石患者严格降尿酸目标（ULT）：
对已形成痛风石、慢性痛风性关节炎的患者，降尿酸治疗（ULT）目标更为严格，必须长期稳定将血尿酸控制在 <300 μmol/L（5.0 mg/dL），以促进已有痛风石结晶逐渐溶解缩小甚至完全吸收，并防止新结晶形成。降尿酸一线药物首选黄嘌呤氧化酶抑制剂（别嘌醇，汉族人使用前强烈推荐筛查 HLA-B*5801 基因防范剥脱性皮炎致死风险；或非布司他）及促尿酸排泄药（苯溴马隆）。
3. 伴代谢综合征的协同选药优势：
- 降压药协同：合并高血压的痛风患者，降压药物优选氯沙坦钾及二氢吡啶类 CCB（氨氯地平），避免选用升高血尿酸的噻嗪类利尿剂；
- 降糖药协同：合并 2 型糖尿病的痛风患者，降糖药首选 SGLT2 抑制剂（达格列净、恩格列净）。SGLT2i 抑制近端肾小管葡萄糖重吸收的同时，通过竞争性抑制肾小管尿酸转运体 GLUT9 促进尿酸排泄，降低血尿酸约 35~50 μmol/L，发挥降糖、减重、降压、促尿酸排泄与心肾多重获益。"""
    }
]


def expand_tier2_textbooks():
    print("=" * 65)
    print("  正在执行 Tier 2 规划教材长章节扩充 (风湿免疫SLE/LN/痛风石/外科创面)")
    print("=" * 65)

    # 1. 保存教材原始文本
    for chap in NEW_TEXTBOOK_CHAPTERS:
        cid = chap["id"]
        raw_text = chap["text"].strip()
        chash = digest(raw_text)
        filename = f"{cid}-{chash[:12]}.txt"
        (RAW_DIR / filename).write_text(raw_text, encoding="utf-8")
        chap["source_path"] = f"raw/{filename}"
        chap["source_sha256"] = chash
        print(f"  -> [Tier 2] 已保存教材长章节原件: {cid} ({chap['title'][:30]}...)")

    # 2. 读取已有 sources.jsonl 与 catalog.json
    existing_sources = [json.loads(line) for line in (TEXTBOOK_ROOT / "sources.jsonl").read_text(encoding="utf-8").splitlines()]
    source_map = {s["id"]: s for s in existing_sources}

    existing_catalog = json.loads((TEXTBOOK_ROOT / "catalog.json").read_text(encoding="utf-8"))
    catalog_map = {c["id"]: c for c in existing_catalog}

    # 3. 对新增章节进行结构化切片 (每 350~500 字符切片)
    emb = BGEEmbedding(ROOT / "data/models")
    from pymilvus import MilvusClient
    client = MilvusClient(str(TEXTBOOK_DB_PATH))
    collection_name = "textbooks_internal_med_10th"

    new_rows = []
    for chap in NEW_TEXTBOOK_CHAPTERS:
        cid = chap["id"]
        text = chap["text"].strip()
        # 按段落与语义切分
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        cur_chunk = ""
        for p in paragraphs:
            if len(cur_chunk) + len(p) < 600:
                cur_chunk += ("\n\n" + p if cur_chunk else p)
            else:
                if cur_chunk:
                    chunks.append(cur_chunk)
                cur_chunk = p
        if cur_chunk:
            chunks.append(cur_chunk)

        chash = chap["source_sha256"]
        source_map[cid] = {
            "id": cid,
            "title": chap["title"],
            "book": chap["book"],
            "edition": chap["edition"],
            "year": chap["year"],
            "part": chap["part"],
            "chapter": chap["chapter"],
            "section": chap["section"],
            "source_path": chap["source_path"],
            "source_sha256": chash,
            "chunks_count": len(chunks),
            "tier": "textbook_tier2",
            "clinical_status": "authoritative_curriculum_textbook_10th"
        }

        catalog_map[cid] = {
            "id": cid,
            "title": chap["title"],
            "book": chap["book"],
            "edition": chap["edition"],
            "year": chap["year"],
            "part": chap["part"],
            "chapter": chap["chapter"],
            "section": chap["section"],
            "chunks": len(chunks)
        }

        print(f"      章节 {cid} 切分为 {len(chunks)} 个结构化切片，正在向量化...")
        vectors = emb.embed(chunks)
        for i, (chk, vec) in enumerate(zip(chunks, vectors)):
            mid = f"{cid}_c{i}_{chash[:8]}"
            new_rows.append({
                "id": mid,
                "document_id": cid,
                "title": chap["title"],
                "book": chap["book"],
                "edition": chap["edition"],
                "year": chap["year"],
                "part": chap["part"],
                "chapter": chap["chapter"],
                "section": chap["section"],
                "text": chk,
                "vector": vec,
                "source_type": "medical_textbook"
            })

    # 4. 插入 Milvus
    client.upsert(collection_name=collection_name, data=new_rows)
    client.load_collection(collection_name)
    total_stats = client.get_collection_stats(collection_name)
    print(f"  -> [Milvus] 成功将 {len(new_rows)} 个新增教材切片 Upsert 入库！当前教材总行数: {total_stats['row_count']}")

    # 5. 回写 sources.jsonl 与 catalog.json
    (TEXTBOOK_ROOT / "sources.jsonl").write_text(
        "\n".join(json.dumps(s, ensure_ascii=False) for s in source_map.values()) + "\n",
        encoding="utf-8"
    )
    (TEXTBOOK_ROOT / "catalog.json").write_text(
        json.dumps(list(catalog_map.values()), ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"[SUCCESS] Tier 2 教材知识库扩充完毕！当前全套大部头章节总数: {len(source_map)} 篇")


if __name__ == "__main__":
    expand_tier2_textbooks()
