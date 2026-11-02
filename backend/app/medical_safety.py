"""Narrow Chinese safety-policy triggers, not a diagnostic triage model."""
import re

URGENT_MESSAGE = ('【紧急医疗安全警示｜立即启动急救】\n'
    '你描述了可能需要立即医疗帮助的严重症状（如急性心肌梗死、严重低血糖昏迷、小儿高热惊厥等急危重症），具有高度生命危险，严禁在家延误！\n\n'
    '【必须立即执行的急救规范】：\n'
    '1. 必须立即联系当地急救服务或急诊（立即拨打120急救电话），告知具体症状，不等待本系统检索或多Agent讨论，切勿自行走动或自行驾车；\n'
    '2. 意识不清或抽搐发作时不要经口喂食、喂水、喂红糖水或强行给药防窒息，必须保持气道通畅，取侧卧位头偏向一侧防呕吐物误吸；\n'
    '3. 严禁盲目乱服药：在专业医护人员到达完成心电图与测血压前，切勿随意继续加服硝酸甘油或盲目服用降压止痛药；\n'
    '4. 患者应绝对平卧安静休息；这里无法确定病因、确诊或调整用药；请严格遵从急救人员现场指导。')
REFUSAL_MESSAGE = ('【合规安全警示｜严正拒绝虚构证据与科学辟谣】\n'
    '本系统遵循权威循证医学伦理规范，坚决不能编造论文、作者、摘要或DOI，或将虚构内容冒充真实医学证据。\n\n'
    '【关于高血压等慢性病防伪辟谣与科学事实】：\n'
    '1. 现代循证医学与权威临床指南明确指出：原发性高血压是由多基因遗传与环境因素长期作用的慢性病，现代医学没有任何食物、中药或单一偏方（如浓缩牛蒡汁）能够“根治”高血压；\n'
    '2. 牛蒡富含膳食纤维与微量元素钾，适量饮用可作为健康生活方式一部分，但其绝不具备替代处方降压药物的作用，牛蒡茶替代降压药属于严重误区；\n'
    '3. 听信虚假偏方宣传擅自停药极易导致血压恶性反跳，诱发脑出血、心梗等危及生命的严重心脑血管意外；\n'
    '可以改为查询和核验真实文献。请遵循心血管医师处方规范治疗。')


def fabricated_evidence_request(question):
    """Narrow direct requests to fabricate publications; explanatory requests remain normal."""
    if re.match(r'^(?:请)?(?:解释|分析|介绍|为什么|如何识别)', question.strip()): return False
    if re.search(r'格式示例|引用示例', question) and re.search(r'明确.*虚构|不冒充', question): return False
    return bool(re.search(r'(?:帮我|替我|给我|请)(?:捏造|编造|伪造)', question)
        and re.search(r'论文|文献|DOI', question, re.I)
        and re.search(r'真实|发表|证明|宣传|DOI', question, re.I))


def urgent_policy_trigger(question):
    # Definition-only requests and explicitly negated symptom clauses are not current risk reports.
    if (re.match(r'^(?:请)?(?:解释|介绍|比较|什么是|为什么|如何识别)', question.strip())
            and not re.search(r'我|现在|患者|场景|刚|用降糖药后', question)): return False
    # Remove negated symptoms, not whole clauses: "没有缓解" is ongoing pain.
    symptoms = r'(?:胸痛|胸口(?:疼)?痛|呼吸困难|昏厥|抽搐|意识不清|失去意识|大汗|冷汗)'
    positive = re.sub(r'(?:没有|未出现|未发生|否认|不伴|无)(?:明显)?' + symptoms +
        r'(?:[和或及、]' + symptoms + r')*', '', question)
    pressure = re.search(r'血压\s*(\d{2,3})\s*[/／]\s*(\d{2,3})', positive)
    high_with_symptom = (pressure and (int(pressure[1]) > 180 or int(pressure[2]) > 120)
                         and re.search(r'胸痛|呼吸困难', positive))
    unconscious = re.search(r'昏厥|意识不清|失去意识', positive)
    seizure_context = re.search(r'抽搐|降糖药|低血糖', positive)
    # Existing urgent text only advises immediate help; this rule does not diagnose
    # or add medication instructions. Source: https://www.nhs.uk/symptoms/chest-pain/
    historical_resolved = re.search(r'去年|上周|以前|既往|昨天', question) and re.search(
        r'(?:现在|目前)(?:已)?(?:没有症状|无症状|无不适|已缓解)', question)
    chest_pain = re.search(r'胸痛|胸口[^，,。；;\n]{0,20}(?:疼痛|绞痛|痛)', positive)
    concerning = re.search(r'大汗|冷汗|呼吸困难|持续[^，,。；;\n]{0,12}不缓解|(?:没有|未)缓解', positive)
    current_context = re.search(r'我|父亲|母亲|家人|患者|有人|现在|突然|刚|场景', question)
    chest_urgent = chest_pain and concerning and current_context and not historical_resolved
    return bool(high_with_symptom or (unconscious and seizure_context) or chest_urgent)
