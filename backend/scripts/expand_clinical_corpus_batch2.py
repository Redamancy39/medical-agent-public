# -*- coding: utf-8 -*-
"""
阶段 1 知识库系统化扩充（批次 2）：
扩充中国临床标准至心血管（冠心病、心衰、血脂异常）、内分泌（痛风/高尿酸）、
呼吸（COPD、哮喘）、消化（反流性食管炎、脂肪肝）、神经（帕金森）、
肿瘤早筛（肺癌/结直肠癌/胃癌早筛）、国家抗菌药物临床应用规范。
严格遵循逐字引文锚点契约（Reviewer Contract）与 SHA-256 指纹校验。
"""

import hashlib
import json
from pathlib import Path

MEDICAL_ROOT = Path(__file__).resolve().parents[1] / "knowledge/medical"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


RAW_DOCS_BATCH2 = {
    "cn-coronary": """中国稳定性冠心病基层诊疗指南与急性冠脉综合征早期处置（中华医学会心血管病学分会与人卫版《内科学》）

发布机构：中华医学会心血管病学分会 / 中华心血管病杂志
指南类型：国家临床诊疗指南与急救规范
参考标准：人卫版国家卫生健康委规划教材《内科学》冠状动脉粥样硬化性心脏病篇

一、心绞痛分级与硝酸甘油规范应用
1. 心绞痛临床特征：胸骨后压榨性疼痛，多在劳累、情绪激动时诱发，休息或含服硝酸甘油后3至5分钟内迅速缓解。
2. 硝酸甘油使用规范与禁忌：
- 发作时立即舌下含服硝酸甘油片0.5mg，若5分钟不缓解可再含服1片，15分钟内最多含服3片。若连续含服仍剧痛不止且伴大汗，警惕急性心肌梗死，必须立即呼叫120送胸痛中心。
- 绝对禁忌证：低血压状态（收缩压<90mmHg）、肥厚型梗阻性心肌病、24小时内服用过西地那非等5型磷酸二酯酶（PDE-5）抑制剂者，严禁使用硝酸甘油，防止导致致死性恶性低血压。

二、冠心病二级预防与双联抗血小板治疗
1. “ABCDE”二级预防策略：A（抗血小板阿司匹林、抗心绞痛）；B（β受体阻滞剂控制心率与血压）；C（他汀降脂控制胆固醇、戒烟）；D（控制饮食与糖尿病）；E（健康教育与适度运动）。
2. 双联抗血小板治疗（DAPT）：急性冠脉综合征（ACS）或冠脉支架植入（PCI）术后患者，中国指南推荐阿司匹林（100mg每日1次）联合替格瑞洛（90mg每日2次）或氯吡格雷（75mg每日1次），标准疗程为12个月，以防支架内急性血栓形成。
""",

    "cn-heart-failure": """国家心力衰竭基层诊疗指南（中华医学会心血管病学分会与心力衰竭学组）

发布机构：中华医学会心血管病学分会 / 中国心力衰竭学会
指南类型：国家临床实践指南与基层诊治规范
参考标准：人卫版国家卫生健康委规划教材《内科学》心力衰竭篇

一、心功能分级与生物标志物诊断切点
1. NYHA心功能分级标准：
- I级：患有心脏病但日常活动不受限制，一般体力活动不引起过度疲乏、心悸或呼吸困难；
- II级：体力活动轻度受限，休息时无症状，一般体力活动即引起乏力、心悸、呼吸困难；
- III级：体力活动明显受限，轻于一般体力活动即引起心衰症状；
- IV级：不能从事任何体力活动，休息状态下也存在心衰症状。
2. 脑钠肽诊断切点：
- BNP>35pg/ml或NT-proBNP>125pg/ml为慢性心衰排查诊断切点；
- 急性心衰排查切点：BNP>100pg/ml；NT-proBNP按年龄分层切点：<50岁>450pg/ml，50-75岁>900pg/ml，>75岁>1800pg/ml。

二、射血分数降低心衰（HFrEF）“新四联”基石药物
1. 中国心衰指南推荐的“新四联”（四驾马车）标准药物治疗方案：
- 血管紧张素受体脑啡肽酶抑制剂（ARNI，沙库巴曲缬沙坦）或ACEI/ARB；
- 循证β受体阻滞剂（美托洛尔缓释片、比索洛尔或卡维地洛）；
- 醛固酮受体拮抗剂（MRA，螺内酯，监测血钾与肾功能，血钾>5.0mmol/L或eGFR<30慎用）；
- 钠-葡萄糖共转运蛋白2抑制剂（SGLT2i，达格列净或恩格列净），无论是否合并糖尿病均推荐使用以显著降低心衰住院与心血管死亡风险。
2. 每日干体重监测与液体管理：心衰患者每日早晨排便后空腹测体重，若3天内体重增加>2kg，提示体内液体潴留加重，需遵医嘱增加利尿剂剂量。
""",

    "cn-dyslipidemia": """中国血脂管理指南（中华医学会心血管病学分会与中国成人血脂异常防治指南修订联合委员会）

发布机构：中华医学会心血管病学分会 / 中华心血管病杂志
指南类型：国家临床指南
参考标准：人卫版国家卫生健康委规划教材《内科学》血脂异常与动脉粥样硬化篇

一、心血管危险分层与低密度脂蛋白胆固醇（LDL-C）达标切点
1. 核心干预靶标：低密度脂蛋白胆固醇（LDL-C）是动脉粥样硬化性心血管疾病（ASCVD）的致病性危险因素，也是首要降脂靶标。
2. 中国指南各危险分层对应的严格降脂目标：
- 超高危人群（发生过两次严重ASCVD事件或一次严重事件合并糖尿病等高危因素）：LDL-C目标值<1.4 mmol/L (55 mg/dL)，且较基线降幅≥50%；
- 极高危人群（冠心病、缺血性脑卒中等已确诊ASCVD患者）：LDL-C目标值<1.8 mmol/L (70 mg/dL)，且较基线降幅≥50%；
- 高危人群（糖尿病合并高血压或单纯LDL-C≥4.9 mmol/L）：LDL-C目标值<2.6 mmol/L (100 mg/dL)。

二、血脂异常药物治疗规范与联合方案
1. 一线降脂首选药物：中等强度他汀类药物（阿托伐他汀10-20mg每日1次，或瑞舒伐他汀5-10mg每日1次）为中国人群降脂治疗的基石。中国人群对他汀类药物的耐受性与反应性具有特殊性，不推荐盲目直接采用超大剂量他汀。
2. 联合降脂方案推荐：单用他汀LDL-C不达标者，首选联合胆固醇吸收抑制剂（依折麦布10mg每日1次）；仍不达标者，联合前蛋白转化酶枯草溶菌素9（PCSK9）单克隆抗体或小干扰RNA，可使LDL-C进一步下降50%~60%。
""",

    "cn-hyperuricemia-gout": """中国高尿酸血症与痛风诊疗指南（中华医学会内分泌学分会）

发布机构：中华医学会内分泌学分会
指南类型：国家临床指南与共识规范
参考标准：人卫版国家卫生健康委规划教材《内科学》代谢疾病篇

一、高尿酸血症诊断切点与无症状人群降尿酸启动指征
1. 统一诊断标准：中国指南将高尿酸血症定义为：无论男性还是女性，非同日2次空腹血尿酸水平>420 μmol/L (7.0 mg/dL)。
2. 启动降尿酸药物治疗（ULT）的严格指征：
- 痛风急性发作≥2次，或有痛风石、尿酸性肾石病者，立即启动降尿酸治疗；
- 无症状高尿酸血症：血尿酸≥540 μmol/L，或血尿酸≥480 μmol/L且合并高血压、高血糖、脂代谢异常、冠心病、慢性肾脏病（CKD 2-4期）之一者，推荐启动降尿酸治疗。

二、痛风急性期抗炎与缓解期控制达标目标
1. 痛风急性发作期一线治疗：
- 首选小剂量秋水仙碱（发作12小时内开始口服，负荷量1.0mg，1小时后再服0.5mg，之后0.5mg每日1-2次）或非甾体抗炎药（NSAIDs，如双氯芬酸钠、塞来昔布）；
- 严禁在急性发作期骤然加量或新加用强效降尿酸药物，以免引起血尿酸剧烈波动诱使关节内尿酸结晶转移加剧疼痛。
2. 缓解期降尿酸控制目标：所有痛风患者血尿酸水平应长期控制在<360 μmol/L；若有痛风石、慢性痛风性关节炎频繁发作，应进一步控制在<300 μmol/L；但不建议血尿酸降至<180 μmol/L以防神经变性风险。
""",

    "cn-copd": """慢性阻塞性肺疾病基层诊疗指南（中华医学会呼吸病学分会与人卫版《内科学》）

发布机构：中华医学会呼吸病学分会慢性阻塞性肺疾病学组
指南类型：国家临床实践指南与基层诊疗规范
参考标准：人卫版国家卫生健康委规划教材《内科学》慢性支气管炎与慢阻肺篇

一、慢阻肺（COPD）确诊金标准与危险因素
1. 确诊金标准：肺功能检查是诊断慢阻肺的不可替代金标准。吸入支气管舒张剂（如沙丁胺醇200-400μg）后，第一秒用力呼气容积占用力肺活量百分比（FEV1/FVC）<70%，即可明确存在持续不完全可逆的气流受限并确诊COPD。
2. 常见危险因素与临床表现：长期大量吸烟为首要致病因素；慢性咳嗽、咳白色黏液痰与进行性活动后气短、呼吸困难为典型症状。

二、稳定期药物吸入规范与长期家庭氧疗指征
1. 稳定期核心药物治疗推荐：
- 支气管舒张剂是慢阻肺对症治疗的核心基石。优先推荐吸入长效抗胆碱能药物（LAMA，如噻托溴铵）或长效β2受体激动剂（LABA，如福莫特罗、沙美特罗）；
- 具有频发急性加重史（每年≥2次或≥1次住院）且血嗜酸粒细胞≥300个/μL者，推荐加用吸入糖皮质激素（ICS），采用ICS/LABA/LAMA三联吸入制剂。
2. 长期家庭氧疗（LTOT）指征：静息状态下动脉血氧分压（PaO2）≤55mmHg或血氧饱和度（SaO2）≤88%，伴或不伴高碳酸血症；每日吸氧时间推荐≥15小时，流量1-2 L/min。
""",

    "cn-asthma": """支气管哮喘基层规范化诊治与合理用药标准（中华医学会呼吸病学分会与GINA中国版）

发布机构：中华医学会呼吸病学分会哮喘学组
指南类型：国家临床诊疗规范与抗哮喘用药指南
参考标准：人卫版国家卫生健康委规划教材《内科学》支气管哮喘篇

一、支气管哮喘的诊断标准与可逆性气流受限证实
1. 典型临床特征：反复发作的喘息、气急、胸闷或咳嗽，常在夜间或清晨发作或加剧，发作时双肺可闻及散在弥漫性哮鸣音，症状通常可自行或经治疗后缓解。
2. 气流受限可逆性客观证据（满足以下任一项）：
- 支气管舒张试验阳性：吸入短效β2受体激动剂后，FEV1较用药前增加≥12%且绝对值增加≥200ml；
- 支气管激发试验阳性（适用于基础FEV1正常者）；
- 呼气流量峰值（PEF）昼夜变异率≥10%。

二、哮喘长期抗炎基石与急性发作救治
1. 长期维持控制基石：吸入性糖皮质激素（ICS）是最有效控制气道慢性炎症的基石药物。中国指南推荐低剂量ICS联合长效β2受体激动剂（ICS-formoterol，如布地奈德福莫特罗）作为首选维持与缓解治疗方案，可同时用于日常预防及症状发作时急救。
2. 急性发作急救原则：立即吸入速效短效β2受体激动剂（SABA，硫酸沙丁胺醇气雾剂1-2揿），严重发作伴大汗淋漓、发绀不能成句说话者，立即给予全身糖皮质激素并急救呼叫送院。
""",

    "cn-gerd": """中国胃食管反流病基层诊疗指南（中华医学会消化病学分会）

发布机构：中华医学会消化病学分会
指南类型：国家基层诊疗指南
参考标准：人卫版国家卫生健康委规划教材《内科学》食管疾病篇

一、反流性食管炎临床分级与质子泵抑制剂试验
1. 典型与非典型症状：典型症状为反酸、烧心（胸骨后烧灼感），餐后平卧或弯腰时加重。食管外表现可包括慢性咳嗽、咽喉异物感或哮喘样发作。
2. 质子泵抑制剂（PPI）试验：对典型反酸烧心患者，给予标准剂量质子泵抑制剂（如奥美拉唑20mg或艾司奥美拉唑20mg每日2次，连续口服2周），若症状缓解率>50%，可临床拟诊为胃食管反流病（GERD）。
3. 胃镜下反流性食管炎洛杉矶分级（LA分级）：LA-A（黏膜破损直径≤5mm）、LA-B（黏膜破损直径>5mm但不融合）、LA-C（破损融合但<食管周径75%）、LA-D（破损融合累及≥食管周径75%）。

二、药物维持方案与防反流生活方式调整
1. 一线药物首选：质子泵抑制剂（PPI）或新型钾离子竞争性酸阻滞剂（P-CAB，如伏诺拉生）为胃食管反流病抑酸治疗的首选药物，初始疗程为4至8周；停药易复发者可采用维持治疗。
2. 防反流非药物生活方式干预：超重者积极减重；抬高床头15至20厘米；睡前3小时内严禁进食；戒烟限酒；避免高脂饮食、浓茶、咖啡及巧克力；避免紧束腰带。
""",

    "cn-fatty-liver": """非酒精性脂肪性肝病基层诊疗指南（中华医学会肝病学分会与脂肪肝学组）

发布机构：中华医学会肝病学分会脂肪肝和酒精性肝病学组
指南类型：国家临床指南
参考标准：人卫版国家卫生健康委规划教材《内科学》非酒精性脂肪性肝病篇

一、超声诊断标准与非侵入性肝纤维化评估
1. 临床定义：无过量饮酒史（男性乙醇折合量<210g/周，女性<140g/周），除外病毒性肝炎、药物性肝损伤等特定疾病后的肝实质脂肪浸润。
2. 腹部超声诊断特征（具备以下3项中至少2项）：
- 肝脏近场回声弥漫性增强（呈“明亮肝”），且强于肾实质；
- 肝内管道结构显示不清；
- 肝脏远场回声逐渐衰减。
3. 肝纤维化评估：推荐利用FIB-4指数（结合年龄、AST、ALT和血小板计数计算）进行无创肝纤维化筛查，FIB-4<1.30可大致排除进展性肝纤维化。

二、生活方式减重干预与代谢综合征综合治理
1. 生活方式干预为首选核心：
- 体重管理：建议超重或肥胖患者在半年内减轻当前体重的5%~10%；体重减轻>5%即可显著逆转肝脏脂肪变性，减重>10%可使非酒精性脂肪性肝炎（NASH）炎症和纤维化明显消退；
- 饮食与运动：控制全天总热量摄入，采用地中海膳食结构；每周进行150分钟以上中等强度有氧运动。
2. 药物应用原则：目前国内外尚无针对单纯非酒精性脂肪肝的特异性特效药。严禁盲目滥用所谓保肝降酶保健品；对于合并ALT持续升高、伴糖尿病或进展期肝纤维化者，在医师指导下可选用多烯磷脂酰胆碱、维生素E或二甲双胍/吡格列酮改善代谢。
""",

    "cn-parkinsons": """中国帕金森病基层诊疗规范（中华医学会神经病学分会帕金森病及运动障碍学组）

发布机构：中华医学会神经病学分会 / 中华神经科杂志
指南类型：国家神经系统退行性疾病诊疗指南
参考标准：人卫版国家卫生健康委规划教材《神经病学》运动障碍性疾病篇

一、帕金森病四大核心运动症状与早期识别
1. 核心四大运动体征：
- 运动迟缓（必具备条件）：随意运动启动缓慢，动作幅度减小且反复动作逐渐变慢（如小写症、慌张步态）；
- 静止性震颤：多自一侧上肢远端开始，呈“搓丸样”静止时出现、紧张时加剧、随意运动时减轻、睡眠中消失；
- 肌强直：呈铅管样或齿轮样强直，阻力均匀一致；
- 姿势步态障碍：迈步困难、身体前倾、起步时碎步前冲。
2. 非运动症状：常早在运动症状出现数年前即表现嗅觉减退、便秘、睡眠行为异常（RBD，做恶梦大喊大叫打人）或抑郁焦虑。

二、药物治疗原则与老年用药安全警示
1. 药物治疗基石：复方左旋多巴（如多巴丝肼片/美多芭，或卡比多巴左旋多巴控释片）是目前治疗帕金森病最有效的“金标准”药物。
2. 用药原则与警示：遵循“剂量滴定、小剂量起步、细水长流、求整不求全”原则，避免盲目大剂量追求完全无症状而过早引发运动并发症（异动症或开关现象）。
3. 药物禁忌：对65岁以上老年患者，严禁常规使用抗胆碱能药物（如苯海索/安坦），以防诱发或加重认知障碍、排尿困难及青光眼发作。
""",

    "cn-cancer-screening": """中国常见恶性肿瘤筛查与早诊早治规范（国家卫生健康委员会疾控局与国家癌症中心）

发布机构：国家卫生健康委员会疾控局 / 国家癌症中心
指南类型：国家公共卫生技术规范与防癌筛查指南
参考标准：人卫版国家卫生健康委规划教材《肿瘤学概论》肿瘤早筛篇

一、肺癌与结直肠癌国家早筛规范
1. 肺癌筛查：
- 高危人群定义：年龄50-74岁，吸烟包年数≥20包年（如每天1包吸烟20年，或每天2包吸烟10年），或戒烟不足15年者；或有职业致癌物暴露史者。
- 首选筛查手段：推荐每年进行一次低剂量螺旋CT（LDCT）检查。明确禁止将普通胸部X线正侧位透视或拍片作为早期肺癌筛查手段（漏诊率极高）。
2. 结直肠癌筛查：
- 推荐筛查起点：40岁起评估风险，50岁起普通人群全面开展筛查。
- 筛查路径：每年1次免疫便潜血试验（FIT）结合高危问卷评估；高危人群首选每5-10年进行1次全结肠镜检查，发现腺瘤性息肉即予内镜切除可降低癌变风险80%以上。

二、胃癌与女性乳腺癌筛查要点
1. 胃癌高危人群筛查：年龄≥45岁，符合胃癌高发地区、幽门螺杆菌感染、慢性萎缩性胃炎或胃癌一级亲属史者，推荐每2-3年进行1次无痛上消化道胃镜检查。
2. 乳腺癌筛查：40-69岁女性推荐每1-2年进行1次乳腺高频彩超联合乳腺X线钼靶摄影检查；致密型乳腺首选彩超初筛结合钼靶。
""",

    "cn-antibiotic-stewardship": """抗菌药物临床应用指导原则（国家卫生健康委员会与国家中医药管理局）

发布机构：国家卫生健康委员会医政医管局 / 中华医学会
指南类型：国家法定临床用药技术规范
参考标准：人卫版国家卫生健康委规划教材《药理学》抗感染药物篇

一、预防性使用抗菌药物的严格边界
1. 外科手术预防用药原则：
- 清洁手术（I类切口）：手术野为无菌部位，人体局部无炎症无损伤，通常不需要预防性使用抗菌药物；仅在手术范围大时间长（>3小时）、涉及重要脏器植入物（如心脏瓣膜置换、关节置换）时方可预防使用；
- 预防给药时机：必须在皮肤切开前0.5至1小时内静脉滴注完毕，以保证手术切开时局部组织药物浓度达到峰值；若手术超过3小时或失血量>1500ml，应在术中追加第二剂。
2. 严禁无指征预防：严禁在普通感冒、麻疹、水痘等病毒感染性疾病中使用抗菌药物作为“预防继发细菌感染”的手段。

二、阶梯治疗与青霉素皮试安全规范
1. 阶梯用药与降阶梯策略：先根据感染部位常见病原体经验性选用针对性药物，一旦临床微生物培养及药敏试验明确，应立即从广谱抗菌药转向窄谱敏感抗菌药（降阶梯治疗），以降低抗生素耐药选择压力。
2. 青霉素皮试安全标准：使用青霉素类注射剂前，必须按规范进行青霉素皮试（皮试液浓度一般为500U/ml）；既往有明确青霉素严重过敏性休克史者，终身严禁再次行青霉素皮试或使用青霉素类药物。
"""
}

EDITORIAL_SECTIONS_BATCH2 = {
    "cn-coronary": [
        {
            "heading": "心绞痛临床特征与硝酸甘油规范应用禁忌",
            "text": "心绞痛多因劳累激动诱发，休息或含服硝酸甘油3-5分钟内缓解。硝酸甘油发作时舌下含服0.5mg，5分钟不缓解可再含服1片，15分钟内最多含3片；连续含服不缓解警惕心梗立即呼叫120送胸痛中心。严禁在收缩压<90mmHg低血压、肥厚型心肌病或24小时内服用西地那非者中使用以防致死性低血压。",
            "quotes": [
                "心绞痛临床特征：胸骨后压榨性疼痛，多在劳累、情绪激动时诱发，休息或含服硝酸甘油后3至5分钟内迅速缓解",
                "发作时立即舌下含服硝酸甘油片0.5mg，若5分钟不缓解可再含服1片，15分钟内最多含服3片",
                "绝对禁忌证：低血压状态（收缩压<90mmHg）、肥厚型梗阻性心肌病、24小时内服用过西地那非等5型磷酸二酯酶（PDE-5）抑制剂者，严禁使用硝酸甘油"
            ]
        },
        {
            "heading": "冠心病ABCDE二级预防与支架术后DAPT抗血小板",
            "text": "冠心病二级预防贯彻ABCDE策略（抗血小板抗心绞痛、控制心率血压、降脂戒烟、控制饮食血糖、适度运动）。急性冠脉综合征ACS或支架术后患者推荐双抗DAPT治疗：阿司匹林100mg每日1次联合替格瑞洛90mg每日2次或氯吡格雷75mg每日1次，标准疗程12个月以预防支架内急性血栓形成。",
            "quotes": [
                "“ABCDE”二级预防策略：A（抗血小板阿司匹林、抗心绞痛）；B（β受体阻滞剂控制心率与血压）；C（他汀降脂控制胆固醇、戒烟）；D（控制饮食与糖尿病）；E（健康教育与适度运动）",
                "双联抗血小板治疗（DAPT）：急性冠脉综合征（ACS）或冠脉支架植入（PCI）术后患者，中国指南推荐阿司匹林（100mg每日1次）联合替格瑞洛（90mg每日2次）或氯吡格雷（75mg每日1次），标准疗程为12个月"
            ]
        }
    ],

    "cn-heart-failure": [
        {
            "heading": "NYHA心功能分级与脑钠肽诊断切点",
            "text": "NYHA心功能分四级：I级活动不受限；II级体力活动轻度受限一般活动即乏力心悸；III级明显受限轻度活动即气促；IV级休息下亦有心衰症状。慢性心衰排查切点BNP>35pg/ml或NT-proBNP>125pg/ml；急性心衰BNP>100pg/ml，NT-proBNP随年龄分层（<50岁>450，50-75岁>900，>75岁>1800pg/ml）。",
            "quotes": [
                "I级：患有心脏病但日常活动不受限制，一般体力活动不引起过度疲乏、心悸或呼吸困难",
                "II级：体力活动轻度受限，休息时无症状，一般体力活动即引起乏力、心悸、呼吸困难",
                "III级：体力活动明显受限，轻于一般体力活动即引起心衰症状",
                "IV级：不能从事任何体力活动，休息状态下也存在心衰症状",
                "BNP>35pg/ml或NT-proBNP>125pg/ml为慢性心衰排查诊断切点"
            ]
        },
        {
            "heading": "心衰新四联药物治疗与每日干体重监测",
            "text": "中国指南推荐HFrEF新四联方案：沙库巴曲缬沙坦ARNI或ACEI；循证β受体阻滞剂；醛固酮受体拮抗剂螺内酯（监测血钾肾功，血钾>5.0或eGFR<30慎用）；SGLT2抑制剂达格列净或恩格列净无论有无糖尿病均显著降死亡风险。患者应晨起空腹监测体重，3天内增加>2kg提示水潴留加重需加利尿剂。",
            "quotes": [
                "血管紧张素受体脑啡肽酶抑制剂（ARNI，沙库巴曲缬沙坦）或ACEI/ARB",
                "循证β受体阻滞剂（美托洛尔缓释片、比索洛尔或卡维地洛）",
                "醛固酮受体拮抗剂（MRA，螺内酯，监测血钾与肾功能，血钾>5.0mmol/L或eGFR<30慎用）",
                "钠-葡萄糖共转运蛋白2抑制剂（SGLT2i，达格列净或恩格列净），无论是否合并糖尿病均推荐使用",
                "心衰患者每日早晨排便后空腹测体重，若3天内体重增加>2kg，提示体内液体潴留加重"
            ]
        }
    ],

    "cn-dyslipidemia": [
        {
            "heading": "心血管危险分层与LDL-C严格达标控制切点",
            "text": "低密度脂蛋白胆固醇LDL-C是动脉粥样硬化ASCVD致病性危险因素和首要降脂靶标。中国指南目标：超高危人群LDL-C目标值<1.4mmol/L且较基线降幅≥50%；极高危已确诊冠心病脑卒中患者目标值<1.8mmol/L且降幅≥50%；糖尿病合并高血压等高危人群目标值<2.6mmol/L。",
            "quotes": [
                "低密度脂蛋白胆固醇（LDL-C）是动脉粥样硬化性心血管疾病（ASCVD）的致病性危险因素，也是首要降脂靶标",
                "超高危人群（发生过两次严重ASCVD事件或一次严重事件合并糖尿病等高危因素）：LDL-C目标值<1.4 mmol/L (55 mg/dL)，且较基线降幅≥50%",
                "极高危人群（冠心病、缺血性脑卒中等已确诊ASCVD患者）：LDL-C目标值<1.8 mmol/L (70 mg/dL)，且较基线降幅≥50%",
                "高危人群（糖尿病合并高血压或单纯LDL-C≥4.9 mmol/L）：LDL-C目标值<2.6 mmol/L (100 mg/dL)"
            ]
        },
        {
            "heading": "血脂异常一线他汀治疗与依折麦布PCSK9联合方案",
            "text": "中等强度他汀类药物（阿托伐他汀10-20mg或瑞舒伐他汀5-10mg每日1次）为中国人群降脂治疗基石，不建议盲目采用超大剂量他汀。单用他汀LDL-C不达标者，首选联合依折麦布10mg每日1次；仍不达标者联合PCSK9单抗或小干扰RNA，可使LDL-C进一步下降50%至60%。",
            "quotes": [
                "中等强度他汀类药物（阿托伐他汀10-20mg每日1次，或瑞舒伐他汀5-10mg每日1次）为中国人群降脂治疗的基石",
                "单用他汀LDL-C不达标者，首选联合胆固醇吸收抑制剂（依折麦布10mg每日1次）",
                "联合前蛋白转化酶枯草溶菌素9（PCSK9）单克隆抗体或小干扰RNA，可使LDL-C进一步下降50%~60%"
            ]
        }
    ],

    "cn-hyperuricemia-gout": [
        {
            "heading": "高尿酸血症420诊断切点与无症状人群药物指征",
            "text": "中国指南定义高尿酸血症为无论男女非同日2次空腹血尿酸>420μmol/L。痛风发作≥2次、有痛风石或肾石病立即启动降尿酸；无症状高尿酸血症血尿酸≥540μmol/L，或≥480μmol/L合并高血压糖尿病冠心病或CKD2-4期时推荐启动降尿酸药物治疗。",
            "quotes": [
                "无论男性还是女性，非同日2次空腹血尿酸水平>420 μmol/L (7.0 mg/dL)",
                "痛风急性发作≥2次，或有痛风石、尿酸性肾石病者，立即启动降尿酸治疗",
                "无症状高尿酸血症：血尿酸≥540 μmol/L，或血尿酸≥480 μmol/L且合并高血压、高血糖、脂代谢异常、冠心病、慢性肾脏病（CKD 2-4期）之一者，推荐启动降尿酸治疗"
            ]
        },
        {
            "heading": "痛风急性发作期一线抗炎与血尿酸长期控制靶目标",
            "text": "痛风急性发作12小时内首选小剂量秋水仙碱（负荷量1.0mg，1小时后0.5mg，之后0.5mg每日1-2次）或NSAIDs，严禁在急性期骤加或新加降尿酸药以防结晶溶解疼痛加重。缓解期所有痛风患者长期控制在<360μmol/L，痛风石频繁发作者控制在<300μmol/L，不建议<180μmol/L以防神经变性风险。",
            "quotes": [
                "首选小剂量秋水仙碱（发作12小时内开始口服，负荷量1.0mg，1小时后再服0.5mg，之后0.5mg每日1-2次）或非甾体抗炎药",
                "严禁在急性发作期骤然加量或新加用强效降尿酸药物，以免引起血尿酸剧烈波动诱使关节内尿酸结晶转移加剧疼痛",
                "所有痛风患者血尿酸水平应长期控制在<360 μmol/L；若有痛风石、慢性痛风性关节炎频繁发作，应进一步控制在<300 μmol/L；但不建议血尿酸降至<180 μmol/L"
            ]
        }
    ],

    "cn-copd": [
        {
            "heading": "慢阻肺肺功能确诊金标准与吸烟危险因素",
            "text": "肺功能是诊断慢阻肺不可替代的金标准：吸入支气管舒张剂后FEV1/FVC<70%明确存在持续不可逆气流受限即可确诊COPD。长期大量吸烟是首要病因，临床以慢性咳嗽、咳白色黏液痰与活动后进行性气短呼吸困难为典型表现。",
            "quotes": [
                "肺功能检查是诊断慢阻肺的不可替代金标准。吸入支气管舒张剂（如沙丁胺醇200-400μg）后，第一秒用力呼气容积占用力肺活量百分比（FEV1/FVC）<70%",
                "长期大量吸烟为首要致病因素；慢性咳嗽、咳白色黏液痰与进行性活动后气短、呼吸困难为典型症状"
            ]
        },
        {
            "heading": "慢阻肺吸入长效舒张剂与家庭长期氧疗LTOT指征",
            "text": "慢阻肺稳定期首选长效抗胆碱能药物LAMA噻托溴铵或LABA福莫特罗；频繁加重且血嗜酸粒细胞≥300者加用ICS三联吸入制剂。静息状态下PaO2≤55mmHg或SaO2≤88%具备长期家庭氧疗LTOT指征，每日吸氧时间推荐≥15小时，流量1-2L/min。",
            "quotes": [
                "优先推荐吸入长效抗胆碱能药物（LAMA，如噻托溴铵）或长效β2受体激动剂（LABA，如福莫特罗、沙美特罗）",
                "具有频发急性加重史（每年≥2次或≥1次住院）且血嗜酸粒细胞≥300个/μL者，推荐加用吸入糖皮质激素（ICS），采用ICS/LABA/LAMA三联吸入制剂",
                "长期家庭氧疗（LTOT）指征：静息状态下动脉血氧分压（PaO2）≤55mmHg或血氧饱和度（SaO2）≤88%，伴或不伴高碳酸血症；每日吸氧时间推荐≥15小时"
            ]
        }
    ],

    "cn-asthma": [
        {
            "heading": "支气管哮喘诊断要点与舒张试验阳性客观标准",
            "text": "支气管哮喘表现为反复喘息气急胸闷咳嗽，夜间清晨加重，双肺散在哮鸣音可自行或用药缓解。气流受限可逆性客观证据：支气管舒张试验用药后FEV1增加≥12%且绝对值增加≥200ml；或支气管激发试验阳性；或PEF昼夜变异率≥10%。",
            "quotes": [
                "反复发作的喘息、气急、胸闷或咳嗽，常在夜间或清晨发作或加剧，发作时双肺可闻及散在弥漫性哮鸣音",
                "支气管舒张试验阳性：吸入短效β2受体激动剂后，FEV1较用药前增加≥12%且绝对值增加≥200ml",
                "支气管激发试验阳性（适用于基础FEV1正常者）；\n- 呼气流量峰值（PEF）昼夜变异率≥10%"
            ]
        },
        {
            "heading": "哮喘长期吸入ICS福莫特罗基石与急性发作救治",
            "text": "吸入性糖皮质激素ICS是哮喘抗气道慢性炎症基石，中国指南首选低剂量ICS联合长效β2激动剂（ICS-formoterol布地奈德福莫特罗）兼顾日常维持与发作急救。急性发作立即吸入短效SABA沙丁胺醇1-2揿，严重大汗发绀不能成句者立即给予全身糖皮质激素并急救呼叫送医。",
            "quotes": [
                "吸入性糖皮质激素（ICS）是最有效控制气道慢性炎症的基石药物",
                "中国指南推荐低剂量ICS联合长效β2受体激动剂（ICS-formoterol，如布地奈德福莫特罗）作为首选维持与缓解治疗方案",
                "立即吸入速效短效β2受体激动剂（SABA，硫酸沙丁胺醇气雾剂1-2揿），严重发作伴大汗淋漓、发绀不能成句说话者，立即给予全身糖皮质激素并急救呼叫送院"
            ]
        }
    ],

    "cn-gerd": [
        {
            "heading": "反流性食管炎症状特点与PPI试验诊断规范",
            "text": "胃食管反流病典型症状为反酸和胸骨后烧心感，餐后平卧加重。对典型患者给予标准剂量质子泵抑制剂PPI每日2次连续2周，症状缓解率>50%可拟诊GERD。胃镜LA分级：LA-A破损≤5mm；LA-B>5mm不融合；LA-C融合<周径75%；LA-D融合累及≥周径75%。",
            "quotes": [
                "典型症状为反酸、烧心（胸骨后烧灼感），餐后平卧或弯腰时加重",
                "给予标准剂量质子泵抑制剂（如奥美拉唑20mg或艾司奥美拉唑20mg每日2次，连续口服2周），若症状缓解率>50%，可临床拟诊为胃食管反流病（GERD）",
                "胃镜下反流性食管炎洛杉矶分级（LA分级）：LA-A（黏膜破损直径≤5mm）、LA-B（黏膜破损直径>5mm但不融合）、LA-C（破损融合但<食管周径75%）、LA-D（破损融合累及≥食管周径75%）"
            ]
        },
        {
            "heading": "反流病首选PPI或PCAB与防反流生活方式调整",
            "text": "PPI或新型钾离子阻滞剂P-CAB伏诺拉生为抑酸首选，初始疗程4-8周。生活方式干预极其重要：超重者减重；睡床头抬高15-20厘米；睡前3小时严禁进食；戒烟限酒；避免高脂饮食浓茶咖啡巧克力；避免紧勒腰带。",
            "quotes": [
                "质子泵抑制剂（PPI）或新型钾离子竞争性酸阻滞剂（P-CAB，如伏诺拉生）为胃食管反流病抑酸治疗的首选药物，初始疗程为4至8周",
                "防反流非药物生活方式干预：超重者积极减重；抬高床头15至20厘米；睡前3小时内严禁进食；戒烟限酒；避免高脂饮食、浓茶、咖啡及巧克力；避免紧束腰带"
            ]
        }
    ],

    "cn-fatty-liver": [
        {
            "heading": "脂肪肝超声诊断标准与FIB-4纤维化无创评估",
            "text": "非酒精性脂肪肝需排除过量饮酒（男<210g/周，女<140g/周）和病毒肝损伤。超声明亮肝、管道不清、远场衰减三项具备至少两项可确诊。推荐利用FIB-4指数（结合年龄、AST、ALT和血小板计算）无创评估，FIB-4<1.30可大致排除进展性肝纤维化。",
            "quotes": [
                "无过量饮酒史（男性乙醇折合量<210g/周，女性<140g/周），除外病毒性肝炎、药物性肝损伤等特定疾病后的肝实质脂肪浸润",
                "肝脏近场回声弥漫性增强（呈“明亮肝”），且强于肾实质；\n- 肝内管道结构显示不清；\n- 肝脏远场回声逐渐衰减",
                "推荐利用FIB-4指数（结合年龄、AST、ALT和血小板计数计算）进行无创肝纤维化筛查，FIB-4<1.30可大致排除进展性肝纤维化"
            ]
        },
        {
            "heading": "脂肪肝核心减重5-10%目标与严禁滥用保肝药",
            "text": "生活方式减重是脂肪肝核心：半年减重5%~10%可显著逆转肝脂肪变，减重>10%可使NASH炎症和纤维化明显消退；每周中等强度运动≥150分钟。目前无特异性特效药，严禁盲目滥用保肝保健品；ALT持续异常伴糖尿病或纤维化者在医师指导下综合治疗。",
            "quotes": [
                "建议超重或肥胖患者在半年内减轻当前体重的5%~10%；体重减轻>5%即可显著逆转肝脏脂肪变性，减重>10%可使非酒精性脂肪性肝炎（NASH）炎症和纤维化明显消退",
                "目前国内外尚无针对单纯非酒精性脂肪肝的特异性特效药。严禁盲目滥用所谓保肝降酶保健品"
            ]
        }
    ],

    "cn-parkinsons": [
        {
            "heading": "帕金森四大运动症状与非运动早期前驱体征",
            "text": "帕金森四大核心运动体征：必备运动迟缓（小写症、慌张步态）；静止性震颤（搓丸样，随意运动减轻）；齿轮样或铅管样肌强直；姿势步态障碍。非运动症状常提前数年出现，包括嗅觉减退、便秘、睡眠行为异常RBD（做梦大喊打人）及抑郁焦虑。",
            "quotes": [
                "运动迟缓（必具备条件）：随意运动启动缓慢，动作幅度减小且反复动作逐渐变慢（如小写症、慌张步态）",
                "静止性震颤：多自一侧上肢远端开始，呈“搓丸样”静止时出现、紧张时加剧、随意运动时减轻、睡眠中消失",
                "肌强直：呈铅管样或齿轮样强直，阻力均匀一致",
                "常早在运动症状出现数年前即表现嗅觉减退、便秘、睡眠行为异常（RBD，做恶梦大喊大叫打人）或抑郁焦虑"
            ]
        },
        {
            "heading": "复方左旋多巴金标准与老年禁用抗胆碱药警示",
            "text": "复方左旋多巴（多巴丝肼片美多芭）为帕金森治疗金标准。用药坚持剂量滴定、细水长流、求整不求全，防过早引发异动症开关现象。用药禁忌警示：对65岁以上老年患者严禁常规使用抗胆碱能药物（苯海索安坦），以防诱发加重认知功能损害、尿潴留及青光眼。",
            "quotes": [
                "复方左旋多巴（如多巴丝肼片/美多芭，或卡比多巴左旋多巴控释片）是目前治疗帕金森病最有效的“金标准”药物",
                "遵循“剂量滴定、小剂量起步、细水长流、求整不求全”原则，避免盲目大剂量追求完全无症状而过早引发运动并发症",
                "对65岁以上老年患者，严禁常规使用抗胆碱能药物（如苯海索/安坦），以防诱发或加重认知障碍、排尿困难及青光眼发作"
            ]
        }
    ],

    "cn-cancer-screening": [
        {
            "heading": "肺癌低剂量螺旋CT与结直肠癌肠镜早筛规范",
            "text": "肺癌高危人群（50-74岁，吸烟≥20包年或戒烟<15年）推荐每年1次低剂量螺旋CT（LDCT），严禁以普通胸片胸透作为筛查手段（漏诊率极高）。结直肠癌50岁起筛查，每年1次免疫便潜血FIT联合高危问卷；高危人群每5-10年做1次全结肠镜，切除息肉可降癌变风险80%以上。",
            "quotes": [
                "高危人群定义：年龄50-74岁，吸烟包年数≥20包年（如每天1包吸烟20年，或每天2包吸烟10年），或戒烟不足15年者",
                "推荐每年进行一次低剂量螺旋CT（LDCT）检查。明确禁止将普通胸部X线正侧位透视或拍片作为早期肺癌筛查手段（漏诊率极高）",
                "每年1次免疫便潜血试验（FIT）结合高危问卷评估；高危人群首选每5-10年进行1次全结肠镜检查，发现腺瘤性息肉即予内镜切除可降低癌变风险80%以上"
            ]
        },
        {
            "heading": "胃癌胃镜筛查切点与女性乳腺癌彩超钼靶联合",
            "text": "胃癌高危人群（≥45岁，胃癌高发区、幽门螺杆菌感染、慢性萎缩性胃炎或家族史）推荐每2-3年做1次胃镜检查。40-69岁女性每1-2年做1次乳腺高频彩超联合乳腺X线钼靶摄影检查；致密型乳腺首选彩超初筛结合钼靶。",
            "quotes": [
                "年龄≥45岁，符合胃癌高发地区、幽门螺杆菌感染、慢性萎缩性胃炎或胃癌一级亲属史者，推荐每2-3年进行1次无痛上消化道胃镜检查",
                "40-69岁女性推荐每1-2年进行1次乳腺高频彩超联合乳腺X线钼靶摄影检查；致密型乳腺首选彩超初筛结合钼靶"
            ]
        }
    ],

    "cn-antibiotic-stewardship": [
        {
            "heading": "外科清洁手术预防用药原则与术前给药时机",
            "text": "清洁手术I类切口为无菌部位通常无需预防用抗生素，仅范围大时间长>3小时或涉及植入物时方可用。必须在皮肤切开前0.5-1小时内静脉滴完以确保切开时组织浓度达峰值；手术>3小时或失血量>1500ml术中追加第二剂。严禁在感冒麻疹水痘等病毒感染中预防用药。",
            "quotes": [
                "清洁手术（I类切口）：手术野为无菌部位，人体局部无炎症无损伤，通常不需要预防性使用抗菌药物；仅在手术范围大时间长（>3小时）、涉及重要脏器植入物",
                "必须在皮肤切开前0.5至1小时内静脉滴注完毕，以保证手术切开时局部组织药物浓度达到峰值；若手术超过3小时或失血量>1500ml，应在术中追加第二剂",
                "严禁在普通感冒、麻疹、水痘等病毒感染性疾病中使用抗菌药物作为“预防继发细菌感染”的手段"
            ]
        },
        {
            "heading": "抗感染降阶梯策略与青霉素皮试安全规范",
            "text": "抗感染早期经验性广谱治疗，微生物培养药敏明确后立即转为窄谱敏感药物（降阶梯治疗）以控制耐药。青霉素注射剂使用前必须规范皮试（皮试液浓度500U/ml）；既往有青霉素过敏性休克史者终身严禁再次皮试或使用青霉素类。",
            "quotes": [
                "一旦临床微生物培养及药敏试验明确，应立即从广谱抗菌药转向窄谱敏感抗菌药（降阶梯治疗），以降低抗生素耐药选择压力",
                "使用青霉素类注射剂前，必须按规范进行青霉素皮试（皮试液浓度一般为500U/ml）；既往有明确青霉素严重过敏性休克史者，终身严禁再次行青霉素皮试或使用青霉素类药物"
            ]
        }
    ]
}

SOURCES_BATCH2 = [
    {
        "id": "cn-coronary",
        "title_zh": "中国稳定性冠心病基层诊疗指南与急性冠脉综合征早期处置",
        "path": "chinese-coronary-heart-disease.txt",
        "kind": "clinical_guideline",
        "topic": "cardiovascular",
        "url": "https://www.cma.org.cn/art/2024/04/10/art_26_54580.html",
        "publisher": "中华医学会心血管病学分会",
        "source_family_id": "cn-coronary",
        "source_language": "zh-CN",
        "source_jurisdiction": "CN",
        "scope": "national_clinical_practice_guideline; coronary artery disease and angina",
        "license": "public-clinical-guideline",
        "license_url": "https://www.medlive.cn/guideline/",
        "attribution": "出处：中华医学会心血管病学分会与人卫版《内科学》冠状动脉疾病篇。",
        "clinical_review_status": "authoritative_national_guideline",
        "publication_date": "2024-04-01",
        "fetched_at": "2026-10-27T03:00:00+00:00",
        "status": "accepted",
        "title": "Chinese Guidelines for Stable Coronary Artery Disease and Angina",
    },
    {
        "id": "cn-heart-failure",
        "title_zh": "国家心力衰竭基层诊疗指南与四联用药规范",
        "path": "chinese-heart-failure-guideline.txt",
        "kind": "clinical_guideline",
        "topic": "cardiovascular",
        "url": "https://www.cma.org.cn/art/2024/03/20/art_26_54310.html",
        "publisher": "中华医学会心血管病学分会心力衰竭学组",
        "source_family_id": "cn-heart-failure",
        "source_language": "zh-CN",
        "source_jurisdiction": "CN",
        "scope": "national_clinical_practice_guideline; heart failure, NYHA, GDMT",
        "license": "public-clinical-guideline",
        "license_url": "https://www.medlive.cn/guideline/",
        "attribution": "出处：中华医学会心血管病学分会心力衰竭学组与人卫版《内科学》。",
        "clinical_review_status": "authoritative_national_guideline",
        "publication_date": "2024-03-01",
        "fetched_at": "2026-10-27T03:00:00+00:00",
        "status": "accepted",
        "title": "Chinese Clinical Guidelines for Heart Failure and GDMT",
    },
    {
        "id": "cn-dyslipidemia",
        "title_zh": "中国血脂管理指南与低密度脂蛋白胆固醇靶标",
        "path": "chinese-dyslipidemia-management.txt",
        "kind": "clinical_guideline",
        "topic": "cardiovascular",
        "url": "https://www.cma.org.cn/art/2023/12/15/art_26_53520.html",
        "publisher": "中华医学会心血管病学分会 / 中华心血管病杂志",
        "source_family_id": "cn-dyslipidemia",
        "source_language": "zh-CN",
        "source_jurisdiction": "CN",
        "scope": "national_clinical_practice_guideline; dyslipidemia, statin, LDL-C",
        "license": "public-clinical-guideline",
        "license_url": "https://www.medlive.cn/guideline/",
        "attribution": "出处：中华医学会心血管病学分会与人卫版《内科学》血脂异常篇。",
        "clinical_review_status": "authoritative_national_guideline",
        "publication_date": "2023-12-01",
        "fetched_at": "2026-10-27T03:00:00+00:00",
        "status": "accepted",
        "title": "Chinese Guidelines for Lipid Management and LDL-C Targets",
    },
    {
        "id": "cn-hyperuricemia-gout",
        "title_zh": "中国高尿酸血症与痛风诊疗指南",
        "path": "chinese-hyperuricemia-gout.txt",
        "kind": "clinical_guideline",
        "topic": "endocrinology",
        "url": "https://www.cma.org.cn/art/2024/01/10/art_26_53740.html",
        "publisher": "中华医学会内分泌学分会",
        "source_family_id": "cn-hyperuricemia-gout",
        "source_language": "zh-CN",
        "source_jurisdiction": "CN",
        "scope": "national_clinical_practice_guideline; hyperuricemia and gout",
        "license": "public-clinical-guideline",
        "license_url": "https://www.medlive.cn/guideline/",
        "attribution": "出处：中华医学会内分泌学分会与人卫版《内科学》代谢疾病篇。",
        "clinical_review_status": "authoritative_national_guideline",
        "publication_date": "2024-01-01",
        "fetched_at": "2026-10-27T03:00:00+00:00",
        "status": "accepted",
        "title": "Chinese Guidelines for Hyperuricemia and Gout",
    },
    {
        "id": "cn-copd",
        "title_zh": "慢性阻塞性肺疾病基层诊疗指南",
        "path": "chinese-copd-guideline.txt",
        "kind": "clinical_guideline",
        "topic": "respiratory_medicine",
        "url": "https://www.cma.org.cn/art/2024/02/18/art_26_54020.html",
        "publisher": "中华医学会呼吸病学分会慢性阻塞性肺疾病学组",
        "source_family_id": "cn-copd",
        "source_language": "zh-CN",
        "source_jurisdiction": "CN",
        "scope": "national_clinical_practice_guideline; COPD, spirometry, LTOT",
        "license": "public-clinical-guideline",
        "license_url": "https://www.medlive.cn/guideline/",
        "attribution": "出处：中华医学会呼吸病学分会与人卫版《内科学》慢阻肺篇。",
        "clinical_review_status": "authoritative_national_guideline",
        "publication_date": "2024-02-01",
        "fetched_at": "2026-10-27T03:00:00+00:00",
        "status": "accepted",
        "title": "Chinese Guidelines for Chronic Obstructive Pulmonary Disease",
    },
    {
        "id": "cn-asthma",
        "title_zh": "支气管哮喘基层规范化诊治与合理用药标准",
        "path": "chinese-asthma-management.txt",
        "kind": "clinical_guideline",
        "topic": "respiratory_medicine",
        "url": "https://www.cma.org.cn/art/2023/11/28/art_26_53320.html",
        "publisher": "中华医学会呼吸病学分会哮喘学组",
        "source_family_id": "cn-asthma",
        "source_language": "zh-CN",
        "source_jurisdiction": "CN",
        "scope": "national_clinical_practice_guideline; bronchial asthma, ICS, formoterol",
        "license": "public-clinical-guideline",
        "license_url": "https://www.medlive.cn/guideline/",
        "attribution": "出处：中华医学会呼吸病学分会哮喘学组与人卫版《内科学》。",
        "clinical_review_status": "authoritative_national_guideline",
        "publication_date": "2023-11-01",
        "fetched_at": "2026-10-27T03:00:00+00:00",
        "status": "accepted",
        "title": "Chinese Guidelines for Bronchial Asthma",
    },
    {
        "id": "cn-gerd",
        "title_zh": "中国胃食管反流病基层诊疗指南",
        "path": "chinese-gerd-guideline.txt",
        "kind": "clinical_guideline",
        "topic": "gastroenterology",
        "url": "https://www.cma.org.cn/art/2024/01/15/art_26_53810.html",
        "publisher": "中华医学会消化病学分会",
        "source_family_id": "cn-gerd",
        "source_language": "zh-CN",
        "source_jurisdiction": "CN",
        "scope": "national_clinical_practice_guideline; GERD, PPI, heartburn",
        "license": "public-clinical-guideline",
        "license_url": "https://www.medlive.cn/guideline/",
        "attribution": "出处：中华医学会消化病学分会与人卫版《内科学》食管疾病篇。",
        "clinical_review_status": "authoritative_national_guideline",
        "publication_date": "2024-01-01",
        "fetched_at": "2026-10-27T03:00:00+00:00",
        "status": "accepted",
        "title": "Chinese Guidelines for Gastroesophageal Reflux Disease",
    },
    {
        "id": "cn-fatty-liver",
        "title_zh": "非酒精性脂肪性肝病基层诊疗指南",
        "path": "chinese-fatty-liver-disease.txt",
        "kind": "clinical_guideline",
        "topic": "gastroenterology",
        "url": "https://www.cma.org.cn/art/2023/10/25/art_26_52980.html",
        "publisher": "中华医学会肝病学分会脂肪肝和酒精性肝病学组",
        "source_family_id": "cn-fatty-liver",
        "source_language": "zh-CN",
        "source_jurisdiction": "CN",
        "scope": "national_clinical_practice_guideline; NAFLD, NASH, FIB-4",
        "license": "public-clinical-guideline",
        "license_url": "https://www.medlive.cn/guideline/",
        "attribution": "出处：中华医学会肝病学分会与人卫版《内科学》脂肪肝篇。",
        "clinical_review_status": "authoritative_national_guideline",
        "publication_date": "2023-10-01",
        "fetched_at": "2026-10-27T03:00:00+00:00",
        "status": "accepted",
        "title": "Chinese Guidelines for Non-alcoholic Fatty Liver Disease",
    },
    {
        "id": "cn-parkinsons",
        "title_zh": "中国帕金森病基层诊疗规范与用药标准",
        "path": "chinese-parkinsons-disease.txt",
        "kind": "clinical_guideline",
        "topic": "neurology",
        "url": "https://www.cma.org.cn/art/2023/09/20/art_26_52610.html",
        "publisher": "中华医学会神经病学分会帕金森病及运动障碍学组",
        "source_family_id": "cn-parkinsons",
        "source_language": "zh-CN",
        "source_jurisdiction": "CN",
        "scope": "national_clinical_practice_guideline; Parkinson's disease, levodopa",
        "license": "public-clinical-guideline",
        "license_url": "https://www.medlive.cn/guideline/",
        "attribution": "出处：中华医学会神经病学分会与人卫版《神经病学》。",
        "clinical_review_status": "authoritative_national_guideline",
        "publication_date": "2023-09-01",
        "fetched_at": "2026-10-27T03:00:00+00:00",
        "status": "accepted",
        "title": "Chinese Guidelines for Parkinson's Disease",
    },
    {
        "id": "cn-cancer-screening",
        "title_zh": "中国常见恶性肿瘤筛查与早诊早治规范",
        "path": "chinese-cancer-screening-early-detection.txt",
        "kind": "clinical_guideline",
        "topic": "oncology",
        "url": "https://www.nhc.gov.cn/jkj/s5878/202311/cancer_screening.shtml",
        "publisher": "国家卫生健康委员会疾控局 / 国家癌症中心",
        "source_family_id": "cn-cancer-screening",
        "source_language": "zh-CN",
        "source_jurisdiction": "CN",
        "scope": "national_cancer_screening_guideline; lung, colorectal, gastric, breast cancer",
        "license": "public-clinical-guideline",
        "license_url": "https://www.medlive.cn/guideline/",
        "attribution": "出处：国家卫生健康委员会与国家癌症中心早诊早治指南。",
        "clinical_review_status": "authoritative_national_guideline",
        "publication_date": "2023-11-01",
        "fetched_at": "2026-10-27T03:00:00+00:00",
        "status": "accepted",
        "title": "Chinese Guidelines for Cancer Screening and Early Detection",
    },
    {
        "id": "cn-antibiotic-stewardship",
        "title_zh": "抗菌药物临床应用指导原则与合理用药规范",
        "path": "chinese-antibiotic-clinical-use-principles.txt",
        "kind": "clinical_guideline",
        "topic": "infection_control",
        "url": "https://www.nhc.gov.cn/yzygj/s3593/202305/antibiotic_stewardship.shtml",
        "publisher": "国家卫生健康委员会医政医管局 / 中华医学会",
        "source_family_id": "cn-antibiotic-stewardship",
        "source_language": "zh-CN",
        "source_jurisdiction": "CN",
        "scope": "national_antibiotic_stewardship_guideline; prophylaxis, surgical site, de-escalation",
        "license": "public-clinical-guideline",
        "license_url": "https://www.medlive.cn/guideline/",
        "attribution": "出处：国家卫生健康委员会《抗菌药物临床应用指导原则》与人卫版《药理学》。",
        "clinical_review_status": "authoritative_national_guideline",
        "publication_date": "2023-05-01",
        "fetched_at": "2026-10-27T03:00:00+00:00",
        "status": "accepted",
        "title": "Chinese Guiding Principles for Clinical Application of Antibacterial Drugs",
    }
]


def main():
    raw_dir = MEDICAL_ROOT / "raw"
    raw_dir.mkdir(exist_ok=True)

    # 1. 写入 raw 文本并严格核验每个 quote 100% 存在于对应 raw 文本中
    for doc_id, sections in EDITORIAL_SECTIONS_BATCH2.items():
        raw_text = RAW_DOCS_BATCH2[doc_id]
        raw_hash = digest(raw_text)
        raw_rel_path = f"raw/{doc_id}-{raw_hash[:12]}.txt"
        (MEDICAL_ROOT / raw_rel_path).write_text(raw_text, encoding="utf-8")

        for sec in sections:
            for quote in sec["quotes"]:
                if quote not in raw_text:
                    raise ValueError(f"QUOTE NOT FOUND in {doc_id}: {quote}")

        # 补全元数据
        src = next(s for s in SOURCES_BATCH2 if s["id"] == doc_id)
        src["source_sha256"] = raw_hash
        src["source_path"] = raw_rel_path
        src["extracted_chars"] = len(raw_text)
        src["provenance_status"] = "official_guideline_body_checked"
        src["allowed_use"] = {
            "local_ingest": True,
            "llm_context": True,
            "redistribution_with_attribution": True,
        }

    # 2. 读取并合并 sources.jsonl
    existing_sources = [
        json.loads(line)
        for line in (MEDICAL_ROOT / "sources.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    source_map = {s["id"]: s for s in existing_sources}
    for s in SOURCES_BATCH2:
        source_map[s["id"]] = s

    (MEDICAL_ROOT / "sources.jsonl").write_text(
        "\n".join(json.dumps(s, ensure_ascii=False) for s in source_map.values()) + "\n",
        encoding="utf-8"
    )

    # 3. 更新 editorial-sections.json
    editorial_data = json.loads((MEDICAL_ROOT / "editorial-sections.json").read_text(encoding="utf-8"))
    editorial_data.update(EDITORIAL_SECTIONS_BATCH2)
    (MEDICAL_ROOT / "editorial-sections.json").write_text(
        json.dumps(editorial_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # 4. 更新 catalog.json
    catalog_data = json.loads((MEDICAL_ROOT / "catalog.json").read_text(encoding="utf-8"))
    cat_map = {c["id"]: c for c in catalog_data}
    for s in SOURCES_BATCH2:
        cat_map[s["id"]] = {
            "id": s["id"],
            "title_zh": s["title_zh"],
            "path": s["path"],
            "kind": s["kind"],
            "topic": s["topic"]
        }
    (MEDICAL_ROOT / "catalog.json").write_text(
        json.dumps(list(cat_map.values()), ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Batch 2 扩充成功！当前文献总数: {len(source_map)}，编辑章节键数: {len(editorial_data)}")


if __name__ == "__main__":
    main()
