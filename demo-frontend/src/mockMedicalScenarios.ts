import type {
  ExecutionEventItem,
  MessageItem,
  ProviderCallItem,
  RunOut,
  SessionSummaryItem,
} from './types.ts'
import {
  POLICY_NOTICE,
  buildVerifiedEvidenceAnchor,
  buildVerifiedSource,
  composeReviewedAnswerAndClaims,
} from './verifiedNlmFixture.ts'

export interface MockTurn {
  id: string
  question: string
  createdAt: string
  run: RunOut
  events: ExecutionEventItem[]
  providerCalls: ProviderCallItem[]
}

export interface MockSessionScenario {
  id: string
  title: string
  categoryTag: string
  statusBadge: 'completed' | 'partial' | 'failed' | 'no_source'
  statusText: string
  summaryText: string
  isUserCreated?: boolean
  turns: MockTurn[]
  followUpSuggestions: Array<{
    label: string
    question: string
    presetTurn?: MockTurn
  }>
  sessionSummary?: SessionSummaryItem
}

// ============================================================================
// Preset Follow-up Turn: eGFR vs UACR Comparison (Verified against NLM Snapshot)
// ============================================================================
const egfrEv0 = buildVerifiedEvidenceAnchor('e0', 'nlm-gfr-test', 0, 0) // creatinine levels alone
const egfrEv1 = buildVerifiedEvidenceAnchor('e1', 'nlm-gfr-test', 0, 1) // cystatin C
const egfrEv2 = buildVerifiedEvidenceAnchor('e2', 'nlm-gfr-test', 0, 2) // complicated and not widely available
const egfrEv3 = buildVerifiedEvidenceAnchor('e3', 'nlm-gfr-test', 1, 0) // early stage no symptoms
const egfrEv4 = buildVerifiedEvidenceAnchor('e4', 'nlm-gfr-test', 1, 3) // don't stop taking any medicine
const uacrEv0 = buildVerifiedEvidenceAnchor('e5', 'nlm-uacr-test', 0, 0) // compares albumin to creatinine

const egfrComposed = composeReviewedAnswerAndClaims([
  {
    kind: 'medical_fact',
    support_status: 'supported',
    text: 'eGFR 是对肾小球滤过率的估算，用于了解肾脏过滤血液中废物的能力；UACR 则是将尿液中的白蛋白与肌酐进行比较，反映尿白蛋白漏出情况，两者检查维度不同、不能简单互相替代。',
    note: '由 NLM eGFR 与 UACR 两份公开资料共同支持：分别评估肾脏滤过废物能力与尿白蛋白排出比值。',
    evidence: [egfrEv0, uacrEv0],
    review_round: 1,
    review_claim_index: 0,
    paragraphBreakAfter: true,
  },
  {
    kind: 'medical_fact',
    support_status: 'supported',
    text: '直接测量肾小球滤过率（mGFR）需要注入标记物并多次监测清除情况，较为复杂且不普遍；因此医护人员常结合血肌酐及年龄、性别、体重等信息估算 eGFR，某些情况下也会使用胱抑素 C。',
    note: 'NLM eGFR 检测页第一小节 3 处英文原文锚点直接支持血肌酐、胱抑素 C 与 mGFR 复杂性说明。',
    evidence: [egfrEv0, egfrEv1, egfrEv2],
    review_round: 1,
    review_claim_index: 1,
    paragraphBreakAfter: true,
  },
  {
    kind: 'medical_fact',
    support_status: 'supported',
    text: '早期肾病通常没有明显症状，糖尿病与高血压人群属于高风险人群。检查前准备与日常用药应先询问医护人员，除非医护人员明确要求，不要自行停用任何药物，也不应仅凭单次估算值自行判断病因。',
    note: 'NLM eGFR 检测页第二小节支持早期肾病无症状及不自行停药边界。',
    evidence: [egfrEv3, egfrEv4],
    policy_rules: ['no_diagnosis_or_prescribing'],
    review_round: 1,
    review_claim_index: 2,
  },
])

const FOLLOW_UP_EGFR_TURN: MockTurn = {
  id: 'sim-turn-egfr-02',
  question: '那么 eGFR（估算肾小球滤过率）和刚才说的 UACR 有什么区别？可以互相替代吗？',
  createdAt: '10:18',
  run: {
    run_id: 'sim-run-egfr-02',
    request_id: 'sim-req-egfr-02',
    session_id: 'sim-session-1',
    run_status: 'finished',
    result_status: 'completed',
    answer: egfrComposed.answer,
    safe_error_code: null,
    mode: 'offline_fake',
    graph_version: 3,
    checkpoint_id: 'sim-ckpt-egfr-02',
    stage: 'persist_result',
    plan_status: 'completed',
    plan_reason:
      '结构模拟演示：追问涉及 eGFR 与前序 UACR 两个检查指标对比，拆分为检索两份 NLM 肾脏检查资料与对比解释两个子任务。',
    knowledge_profile: 'medical',
    agent_id: 'consultation_agent',
    model_calls: 6,
    tool_calls: 2,
    worker_iterations: 2,
    context_status: 'simulated',
    response_origin: 'agent',
    safety_policy: null,
    task_count: 2,
    distinct_agent_count: 2,
    planned_agent_count: 2,
    started_task_count: 2,
    completed_task_count: 2,
    failed_task_count: 0,
    blocked_task_count: 0,
    evidence_status: 'passed',
    reviewer_status: 'completed',
    atomization_status: 'completed',
    review_rewrite_count: 0,
    review_rewrite_status: 'not_needed',
    citation_support_status: 'model_reviewed',
    clinical_review_status: 'not_run',
    reviewer_error_code: null,
    omitted_claim_count: egfrComposed.omitted_claim_count,
    reviewed_answer_sha256: 'sim-sha256-egfr-02',
    refinement_count: 0,
    schema_repair_count: 0,
    memory_write_status: 'done',
    summary_write_status: 'not_run',
    maintenance_error_code: null,
    context_details: {
      memory_status: 'simulated',
      summary_status: 'empty',
      memory_count: 1,
      older_history_omitted: false,
      history_truncated: false,
    },
    sources: [
      buildVerifiedSource('nlm-gfr-test', 0),
      buildVerifiedSource('nlm-gfr-test', 1),
      buildVerifiedSource('nlm-uacr-test', 0, [0]),
    ],
    task_results: [
      {
        task_id: 'retrieve_renal_tests',
        agent_id: 'research_agent',
        description: '检索 NLM 知识库中 eGFR 与 UACR 检查的测试对象、估算指标与适用范围章节',
        depends_on: [],
        status: 'completed',
        safe_error_code: null,
        model_calls: 2,
        tool_calls: 2,
        worker_iterations: 1,
        refined: false,
        started: true,
      },
      {
        task_id: 'compare_egfr_uacr',
        agent_id: 'consultation_agent',
        description: '基于已检索的两份 NLM 资料对比解释 eGFR 与 UACR 的检查维度差异与用药准备注意',
        depends_on: ['retrieve_renal_tests'],
        status: 'completed',
        safe_error_code: null,
        model_calls: 1,
        tool_calls: 0,
        worker_iterations: 1,
        refined: false,
        started: true,
      },
    ],
    review_packet_summary: {
      claims: 4,
      evidence: 6,
      chars: 1126,
      documents: 2,
    },
    claim_reviews: egfrComposed.claim_reviews,
  },
  events: [
    { stage: 'safety_gate', task_id: null, status: 'completed' },
    { stage: 'load_context', task_id: null, status: 'completed' },
    { stage: 'route', task_id: null, status: 'completed' },
    { stage: 'plan', task_id: null, status: 'completed' },
    { stage: 'dispatch', task_id: null, status: 'completed' },
    { stage: 'task_worker', task_id: 'retrieve_renal_tests', status: 'completed' },
    { stage: 'task_tools', task_id: 'retrieve_renal_tests', status: 'completed' },
    { stage: 'task_result', task_id: 'retrieve_renal_tests', status: 'completed' },
    { stage: 'task_worker', task_id: 'compare_egfr_uacr', status: 'completed' },
    { stage: 'task_result', task_id: 'compare_egfr_uacr', status: 'completed' },
    { stage: 'check_evidence', task_id: null, status: 'completed' },
    { stage: 'synthesize', task_id: null, status: 'completed' },
    { stage: 'review_answer', task_id: null, status: 'completed' },
    { stage: 'persist_result', task_id: null, status: 'completed' },
  ],
  providerCalls: [
    {
      provider: 'local_simulation',
      operation: 'sim_plan + sim_workers + sim_review',
      status: 'simulated_ok',
      http_status: null,
      safe_error_code: null,
      elapsed_seconds: null,
      usage: {},
    },
  ],
}

// ============================================================================
// Scenario 1: Completed Answer (UACR) - Verified against nlm-uacr-test
// ============================================================================
const uacrAnchorCompare = buildVerifiedEvidenceAnchor('e0', 'nlm-uacr-test', 0, 0) // [991..1065] compares the levels of albumin...
const uacrAnchorNoSymptom = buildVerifiedEvidenceAnchor('e1', 'nlm-uacr-test', 0, 1) // [1965..2020] Early kidney disease usually doesn't have any symptoms.
const uacrAnchorDiabetes = buildVerifiedEvidenceAnchor('e2', 'nlm-uacr-test', 0, 2) // [1508..1521] Have diabetes
const uacrAnchorHtn = buildVerifiedEvidenceAnchor('e3', 'nlm-uacr-test', 0, 3) // [1524..1548] Have high blood pressure
const uacrAnchor24h = buildVerifiedEvidenceAnchor('e4', 'nlm-uacr-test', 1, 0) // [3134..3156] A 24-hour urine sample
const uacrAnchorRandom = buildVerifiedEvidenceAnchor('e5', 'nlm-uacr-test', 1, 1) // [2729..2762] A "random" or "spot" urine sample

const uacrScenarioComposed = composeReviewedAnswerAndClaims([
  {
    kind: 'medical_fact',
    support_status: 'supported',
    text: '尿白蛋白肌酐比（UACR）是将尿液中的白蛋白水平与肌酐水平进行比较的检查，用于评估身体是否以加快的速度排出白蛋白。',
    note: 'NLM 尿白蛋白肌酐比检测页直接支持：比较尿中白蛋白与肌酐水平以评估异常白蛋白排出。',
    evidence: [uacrAnchorCompare],
    review_round: 1,
    review_claim_index: 0,
  },
  {
    kind: 'medical_fact',
    support_status: 'supported',
    text: '由于早期肾病通常没有任何症状，糖尿病与高血压等高风险人群常通过该项检查筛查早期肾损伤征象。',
    note: '由第 2 轮证据约束改写后复审通过，同时绑定“早期肾病通常无症状”“患有糖尿病”“患有高血压” 3 处原文锚点。',
    evidence: [uacrAnchorNoSymptom, uacrAnchorDiabetes, uacrAnchorHtn],
    review_round: 2,
    review_claim_index: 0,
    original_draft_spans: [
      {
        index: 1,
        start: 56,
        end: 90,
        text: '正常肾脏只让极少白蛋白进入尿液，超过特定数值即可直接确诊早期肾病。',
      },
    ],
    paragraphBreakAfter: true,
  },
  {
    kind: 'medical_fact',
    support_status: 'supported',
    text: 'UACR 检查可使用随机尿、晨尿或 24 小时尿等样本采集方式，具体采样与复查安排应遵循医护人员说明。',
    note: 'NLM UACR 第二小节支持随机尿/定点尿与 24 小时尿两处英文原文锚点。',
    evidence: [uacrAnchorRandom, uacrAnchor24h],
    review_round: 1,
    review_claim_index: 2,
  },
  {
    kind: 'medical_fact',
    support_status: 'supported',
    text: '该比值反映的是白蛋白漏出信息，不等同于直接测量肾小球滤过率（GFR），单次异常结果通常需要结合更多检查确认，不能直接用于自行给慢性肾病分期。',
    note: 'NLM UACR 第二小节支持不等同于直接测 GFR、需结合其他检查解释且不能自行分期。',
    evidence: [uacrAnchor24h],
    policy_rules: ['no_diagnosis_or_prescribing'],
    review_round: 1,
    review_claim_index: 3,
  },
])

// ============================================================================
// Scenario 2: Partial Answer with Omitted Claims (HbA1c vs SMBG)
// ============================================================================
const a1cAnchorMonths = buildVerifiedEvidenceAnchor('e0', 'nlm-a1c-test', 0, 0) // [159..193] over the past two to three months.
const a1cAnchorNoType1Diag = buildVerifiedEvidenceAnchor('e1', 'nlm-a1c-test', 0, 1) // [2323..2374] The A1C test isn't used to diagnose type 1 diabetes
const a1cAnchorMonitor = buildVerifiedEvidenceAnchor('e2', 'nlm-a1c-test', 0, 2) // [2379..2432] may be used for monitoring your blood glucose levels.
const a1cAnchorAnemia = buildVerifiedEvidenceAnchor('e3', 'nlm-a1c-test', 1, 2) // [5964..5978] such as anemia
const a1cAnchorKidneyLiver = buildVerifiedEvidenceAnchor('e4', 'nlm-a1c-test', 1, 3) // [6071..6132] Kidney failure and liver disease can also affect A1C results.
const bgAnchorSensor = buildVerifiedEvidenceAnchor('e5', 'nlm-blood-glucose', 1, 0) // [2032..2089] The sensor measures your glucose level every few minutes.
const bgAnchorLowDanger = buildVerifiedEvidenceAnchor('e6', 'nlm-blood-glucose', 1, 2) // [4087..4164] Low blood glucose can be dangerous...
const dtAnchorRandom = buildVerifiedEvidenceAnchor('e7', 'nlm-diabetes-tests', 0, 0) // [5646..5701] Random blood sugar. This test can be taken at any time.
const dtAnchorNoFast = buildVerifiedEvidenceAnchor('e8', 'nlm-diabetes-tests', 1, 0) // [6017..6054] No fasting is required for this test.
const fastAnchor8to12 = buildVerifiedEvidenceAnchor('e9', 'nlm-fasting-test', 0, 1) // [634..647] 8 to 12 hours
const fastAnchorWater = buildVerifiedEvidenceAnchor('e10', 'nlm-fasting-test', 0, 0) // [153..171] except plain water
const fastAnchorNotAll = buildVerifiedEvidenceAnchor('e11', 'nlm-fasting-test', 0, 2) // [1840..1883] Not all blood glucose tests require fasting

const hba1cScenarioComposed = composeReviewedAnswerAndClaims([
  {
    kind: 'medical_fact',
    support_status: 'supported',
    text: '糖化血红蛋白（HbA1c）反映过去约 2–3 个月的平均血糖水平，通过检测血液中葡萄糖与红细胞内血红蛋白结合的比例来评估长期趋势。',
    note: 'NLM HbA1c 检测页第一小节直接支持：反映过去 2–3 个月的平均血糖水平。',
    evidence: [a1cAnchorMonths],
    review_round: 1,
    review_claim_index: 0,
  },
  {
    kind: 'medical_fact',
    support_status: 'supported',
    text: '居家指尖血糖或随机血糖检测反映的则是采血当时那一刻的即时血糖水平，两者反映的时间尺度不同，不能简单互相替代。',
    note: 'NLM 糖尿病检测页与 HbA1c 页共同支持即时采血与数月平均的时间尺度差异。',
    evidence: [a1cAnchorMonths, dtAnchorRandom],
    review_round: 1,
    review_claim_index: 1,
    paragraphBreakAfter: true,
  },
  {
    kind: 'medical_fact',
    support_status: 'supported',
    text: 'HbA1c 可用于筛查或诊断 2 型糖尿病与糖尿病前期，也可用于监测血糖控制情况；HbA1c 不用于诊断 1 型糖尿病，但可用于其血糖监测。',
    note: 'NLM HbA1c 检测页第一小节两处英文锚点直接支持适用范围与 1 型糖尿病限制。',
    evidence: [a1cAnchorNoType1Diag, a1cAnchorMonitor],
    review_round: 1,
    review_claim_index: 2,
  },
  {
    kind: 'medical_fact',
    support_status: 'supported',
    text: '此外，贫血等影响红细胞的情况以及肾衰竭、肝病可能影响 HbA1c 结果的准确性，结果异常时需结合其他检查由医护人员解释。',
    note: 'NLM HbA1c 检测页第二小节两处英文原文锚点支持贫血、肾衰竭与肝病对结果的影响。',
    evidence: [a1cAnchorAnemia, a1cAnchorKidneyLiver],
    review_round: 1,
    review_claim_index: 3,
    paragraphBreakAfter: true,
  },
  {
    kind: 'medical_fact',
    support_status: 'unsupported',
    text: '如果患者每天在家规律测量 7 次指尖血糖，就能够通过固定线性公式直接换算出准确的 HbA1c 百分比数值，从而免去医院静脉抽血。',
    note: '未进入最终回答：当前 NLM 公开资料快照中未包含“每日 7 次指尖血糖线性换算替代静脉 HbA1c 抽血”的依据，第 2 轮复审判定为缺乏原文支持（unsupported）并保守省略。',
    evidence: [a1cAnchorMonths, bgAnchorSensor],
    review_round: 2,
    review_claim_index: 1,
    original_draft_spans: [
      {
        index: 2,
        start: 229,
        end: 294,
        text: '每天测 7 次指尖血糖即可通过公式直接换算出准确的 HbA1c 百分比。',
      },
    ],
  },
  {
    kind: 'medical_fact',
    support_status: 'partially_supported',
    text: '因为 HbA1c 会把高血糖和低血糖相互平均抵消，所以只要想发现夜间无症状低血糖就必须佩戴连续血糖监测（CGM）传感器。',
    note: '未进入最终回答：NLM 资料说明 CGM 可每几分钟记录血糖变化、低血糖可能危险需及时处理，但未作出“HbA1c 高低抵消故必须佩戴 CGM”的绝对因果结论，判定为仅部分支持（partially_supported）并保守省略。',
    evidence: [bgAnchorSensor, bgAnchorLowDanger],
    review_round: 2,
    review_claim_index: 2,
    original_draft_spans: [
      {
        index: 3,
        start: 294,
        end: 355,
        text: '由于 HbA1c 平均抵消高低血糖，发现夜间低血糖必须佩戴 CGM。',
      },
    ],
  },
  {
    kind: 'medical_fact',
    support_status: 'supported',
    text: '并非所有血糖检查都需要空腹：HbA1c 检测与随机血糖通常不需要空腹，而空腹血糖和口服葡萄糖耐量试验（OGTT）需要空腹（一般为 8–12 小时，期间除白水外不进食或饮用其他饮料），去医院抽血前应先向医护人员确认所开具的具体项目。',
    note: 'NLM 糖尿病检测页与验血前空腹准备页 4 处英文原文锚点支持：HbA1c 无需空腹，空腹检查一般 8–12 小时且仅可饮白水。',
    evidence: [dtAnchorNoFast, fastAnchorNotAll, fastAnchor8to12, fastAnchorWater],
    review_round: 1,
    review_claim_index: 4,
  },
])

// ============================================================================
// Exported 5 Preset Simulation Scenarios
// ============================================================================
export const MOCK_SCENARIOS: MockSessionScenario[] = [
  {
    id: 'sim-session-1',
    title: 'UACR 尿检与早期肾病筛查',
    categoryTag: '单任务 · 完整回答',
    statusBadge: 'completed',
    statusText: '已完成',
    summaryText:
      '本地结构模拟演示：展示单任务检索 NLM 尿白蛋白肌酐比资料、逐事实绑定英文原文快照锚点及同会话继续追问 eGFR。',
    sessionSummary: {
      status: 'ready',
      content:
        '用户正在了解糖尿病与高血压相关的肾脏早期筛查指标（UACR 尿白蛋白肌酐比、eGFR 估算肾小球滤过率）及其适用边界。',
      covered_until_seq: 2,
      version: 1,
    },
    followUpSuggestions: [
      {
        label: '追问：eGFR 与 UACR 有何区别？',
        question: '那么 eGFR（估算肾小球滤过率）和刚才说的 UACR 有什么区别？可以互相替代吗？',
        presetTurn: FOLLOW_UP_EGFR_TURN,
      },
      {
        label: '追问：检查前能自己停降压药吗？',
        question: '做这类肾脏或血液检查前，需要自己先停掉平时吃的降压药或降糖药吗？',
      },
    ],
    turns: [
      {
        id: 'sim-turn-uacr-01',
        question: '医生让我查尿白蛋白肌酐比（UACR），这个指标主要比较什么？为什么说它能帮助发现早期肾病？',
        createdAt: '10:15',
        run: {
          run_id: 'sim-run-uacr-01',
          request_id: 'sim-req-uacr-01',
          session_id: 'sim-session-1',
          run_status: 'finished',
          result_status: 'completed',
          answer: uacrScenarioComposed.answer,
          safe_error_code: null,
          mode: 'offline_fake',
          graph_version: 3,
          checkpoint_id: 'sim-ckpt-uacr-01',
          stage: 'persist_result',
          plan_status: 'completed',
          plan_reason:
            '结构模拟演示：问题聚焦于 UACR 单一检查指标的比较对象、早期肾病筛查意义与采样要求，由 1 个 consultation_agent 任务完成检索与解释。',
          knowledge_profile: 'medical',
          agent_id: 'consultation_agent',
          model_calls: 8,
          tool_calls: 1,
          worker_iterations: 2,
          context_status: 'simulated',
          response_origin: 'agent',
          safety_policy: null,
          task_count: 1,
          distinct_agent_count: 1,
          planned_agent_count: 1,
          started_task_count: 1,
          completed_task_count: 1,
          failed_task_count: 0,
          blocked_task_count: 0,
          evidence_status: 'passed',
          reviewer_status: 'completed',
          atomization_status: 'completed',
          review_rewrite_count: 1,
          review_rewrite_status: 'completed',
          citation_support_status: 'model_reviewed',
          clinical_review_status: 'not_run',
          reviewer_error_code: null,
          omitted_claim_count: uacrScenarioComposed.omitted_claim_count,
          reviewed_answer_sha256: 'sim-sha256-uacr-01',
          refinement_count: 0,
          schema_repair_count: 0,
          memory_write_status: 'done',
          summary_write_status: 'ready',
          maintenance_error_code: null,
          context_details: {
            memory_status: 'simulated',
            summary_status: 'ready',
            memory_count: 0,
            older_history_omitted: false,
            history_truncated: false,
          },
          sources: [
            buildVerifiedSource('nlm-uacr-test', 0),
            buildVerifiedSource('nlm-uacr-test', 1),
          ],
          task_results: [
            {
              task_id: 'explain_uacr',
              agent_id: 'consultation_agent',
              description:
                '解释 UACR（尿白蛋白/肌酐比值）比较的两项指标、为何能反映早期肾损伤、高风险适用人群与采样方式，并明确美国 NLM 科普资料边界。',
              depends_on: [],
              status: 'completed',
              safe_error_code: null,
              model_calls: 2,
              tool_calls: 1,
              worker_iterations: 2,
              refined: false,
              started: true,
            },
          ],
          review_packet_summary: {
            claims: 4,
            evidence: 6,
            chars: 452,
            documents: 1,
          },
          review_batch_progress: {
            round: 2,
            completed_batches: 1,
            total_batches: 1,
          },
          claim_reviews: uacrScenarioComposed.claim_reviews,
        },
        events: [
          { stage: 'safety_gate', task_id: null, status: 'completed' },
          { stage: 'load_context', task_id: null, status: 'completed' },
          { stage: 'route', task_id: null, status: 'completed' },
          { stage: 'plan', task_id: null, status: 'completed' },
          { stage: 'worker', task_id: null, status: 'completed' },
          { stage: 'tools', task_id: null, status: 'completed' },
          { stage: 'worker', task_id: null, status: 'completed' },
          { stage: 'validate_output', task_id: null, status: 'completed' },
          { stage: 'review_answer', task_id: null, status: 'completed' },
          { stage: 'persist_result', task_id: null, status: 'completed' },
        ],
        providerCalls: [
          {
            provider: 'local_simulation',
            operation: 'sim_single_worker + sim_review_2_rounds',
            status: 'simulated_ok',
            http_status: null,
            safe_error_code: null,
            elapsed_seconds: null,
            usage: {},
          },
        ],
      },
    ],
  },
  {
    id: 'sim-session-2',
    title: 'HbA1c 与指尖血糖对比及空腹要求',
    categoryTag: '多任务 DAG · 部分完成',
    statusBadge: 'partial',
    statusText: '部分完成 (省略2条)',
    summaryText:
      '本地结构模拟演示：展示 3 个子任务依赖调度（检索 → 时间尺度解释 + 空腹规则核查），以及审核器将 2 条超出 NLM 原文快照的延伸断言保守省略（未进入最终回答）。',
    followUpSuggestions: [
      {
        label: '追问：空腹验血期间能喝咖啡或嚼口香糖吗？',
        question: '如果医生明确要求做空腹血糖检查，空腹期间可以喝黑咖啡或嚼无糖口香糖吗？',
      },
    ],
    turns: [
      {
        id: 'sim-turn-hba1c-01',
        question:
          '糖化血红蛋白（HbA1c）和我在家测的指尖血糖有什么区别？为什么不能只靠其中一个替代另一个？去医院抽血查这项一定要空腹吗？',
        createdAt: '10:22',
        run: {
          run_id: 'sim-run-hba1c-01',
          request_id: 'sim-req-hba1c-01',
          session_id: 'sim-session-2',
          run_status: 'finished',
          result_status: 'partial',
          answer: hba1cScenarioComposed.answer,
          safe_error_code: 'REVIEW_SUPPORT_INCOMPLETE',
          mode: 'offline_fake',
          graph_version: 3,
          checkpoint_id: 'sim-ckpt-hba1c-01',
          stage: 'persist_result',
          plan_status: 'completed',
          plan_reason:
            '结构模拟演示：问题同时包含“HbA1c 与指尖血糖的时间尺度对比”和“医院抽血空腹准备规则”两个子主题，拆分为资料检索、机制对比说明与检查准备边界核查 3 个依赖子任务。',
          knowledge_profile: 'medical',
          agent_id: 'consultation_agent',
          model_calls: 10,
          tool_calls: 3,
          worker_iterations: 4,
          context_status: 'simulated',
          response_origin: 'agent',
          safety_policy: null,
          task_count: 3,
          distinct_agent_count: 3,
          planned_agent_count: 3,
          started_task_count: 3,
          completed_task_count: 3,
          failed_task_count: 0,
          blocked_task_count: 0,
          evidence_status: 'passed',
          reviewer_status: 'completed',
          atomization_status: 'completed',
          review_rewrite_count: 1,
          review_rewrite_status: 'completed',
          citation_support_status: 'model_reviewed',
          clinical_review_status: 'not_run',
          reviewer_error_code: null,
          omitted_claim_count: hba1cScenarioComposed.omitted_claim_count,
          reviewed_answer_sha256: 'sim-sha256-hba1c-01',
          refinement_count: 0,
          schema_repair_count: 1,
          contract_repair_counts: { review_again: 1 },
          memory_write_status: 'done',
          summary_write_status: 'not_run',
          maintenance_error_code: null,
          context_details: {
            memory_status: 'simulated',
            summary_status: 'empty',
            memory_count: 0,
          },
          sources: [
            buildVerifiedSource('nlm-a1c-test', 0),
            buildVerifiedSource('nlm-a1c-test', 1),
            buildVerifiedSource('nlm-blood-glucose', 1),
            buildVerifiedSource('nlm-diabetes-tests', 0, [0]),
            buildVerifiedSource('nlm-diabetes-tests', 1, [0]),
            buildVerifiedSource('nlm-fasting-test', 0),
          ],
          task_results: [
            {
              task_id: 'retrieve_a1c_and_smbg',
              agent_id: 'research_agent',
              description: '检索 NLM 知识库中 HbA1c、居家血糖监测与糖尿病血液检查空腹要求章节',
              depends_on: [],
              status: 'completed',
              safe_error_code: null,
              model_calls: 2,
              tool_calls: 3,
              worker_iterations: 2,
              refined: false,
              started: true,
            },
            {
              task_id: 'explain_timescale_diff',
              agent_id: 'consultation_agent',
              description: '依赖检索结果，解释 HbA1c（2–3个月平均）与指尖血糖（即时时点）的时间尺度差异与适用场景',
              depends_on: ['retrieve_a1c_and_smbg'],
              status: 'completed',
              safe_error_code: null,
              model_calls: 1,
              tool_calls: 0,
              worker_iterations: 1,
              refined: false,
              started: true,
            },
            {
              task_id: 'verify_fasting_and_scope',
              agent_id: 'diagnostic_agent',
              description: '依赖检索结果，核查 HbA1c 与空腹血糖在进食准备上的差异及红细胞干扰因素边界',
              depends_on: ['retrieve_a1c_and_smbg'],
              status: 'completed',
              safe_error_code: null,
              model_calls: 1,
              tool_calls: 0,
              worker_iterations: 1,
              refined: false,
              started: true,
            },
          ],
          review_packet_summary: {
            claims: 6,
            evidence: 12,
            chars: 1890,
            documents: 4,
          },
          review_batch_progress: {
            round: 2,
            completed_batches: 1,
            total_batches: 1,
          },
          claim_reviews: hba1cScenarioComposed.claim_reviews,
        },
        events: [
          { stage: 'safety_gate', task_id: null, status: 'completed' },
          { stage: 'load_context', task_id: null, status: 'completed' },
          { stage: 'route', task_id: null, status: 'completed' },
          { stage: 'plan', task_id: null, status: 'completed' },
          { stage: 'dispatch', task_id: null, status: 'completed' },
          { stage: 'task_worker', task_id: 'retrieve_a1c_and_smbg', status: 'completed' },
          { stage: 'task_tools', task_id: 'retrieve_a1c_and_smbg', status: 'completed' },
          { stage: 'task_result', task_id: 'retrieve_a1c_and_smbg', status: 'completed' },
          { stage: 'task_worker', task_id: 'explain_timescale_diff', status: 'completed' },
          { stage: 'task_result', task_id: 'explain_timescale_diff', status: 'completed' },
          { stage: 'task_worker', task_id: 'verify_fasting_and_scope', status: 'completed' },
          { stage: 'task_result', task_id: 'verify_fasting_and_scope', status: 'completed' },
          { stage: 'check_evidence', task_id: null, status: 'completed' },
          { stage: 'synthesize', task_id: null, status: 'completed' },
          { stage: 'review_answer', task_id: null, status: 'partial' },
          { stage: 'persist_result', task_id: null, status: 'partial' },
        ],
        providerCalls: [
          {
            provider: 'local_simulation',
            operation: 'sim_3_task_dag + sim_review_partial',
            status: 'simulated_partial',
            http_status: null,
            safe_error_code: 'REVIEW_SUPPORT_INCOMPLETE',
            elapsed_seconds: null,
            usage: {},
          },
        ],
      },
    ],
  },
  {
    id: 'sim-session-3',
    title: '降压药机制与具体剂量询问',
    categoryTag: '审核拦截 · 阻断未审原稿',
    statusBadge: 'partial',
    statusText: '审核未通过',
    summaryText:
      '本地结构模拟演示：当草稿包含无原文锚点支持的具体毫克剂量断言且契约校验未通过（REVIEW_MEDICAL_EVIDENCE_REQUIRED）时，系统拒绝发布未审核医学原稿。',
    followUpSuggestions: [
      {
        label: '改问：NLM 资料中降压药主要有哪些一般机制？',
        question: '不问个人具体剂量了，请按 NLM 资料介绍一下利尿剂和钙通道阻滞剂帮助控制血压的一般机制。',
      },
    ],
    turns: [
      {
        id: 'sim-turn-bpmed-01',
        question: '我血压 145/95，应该吃氨氯地平还是氢氯噻嗪？每天早上吃几毫克合适？',
        createdAt: '10:25',
        run: {
          run_id: 'sim-run-bpmed-01',
          request_id: 'sim-req-bpmed-01',
          session_id: 'sim-session-3',
          run_status: 'finished',
          result_status: 'partial',
          answer:
            '本轮逐项引用审核未完成，暂不返回未经审核的医学结论。请查看运行状态，或提供具体原文后再试。',
          safe_error_code: 'REVIEW_MEDICAL_EVIDENCE_REQUIRED',
          mode: 'offline_fake',
          graph_version: 3,
          checkpoint_id: 'sim-ckpt-bpmed-01',
          stage: 'persist_result',
          plan_status: 'completed',
          plan_reason:
            '结构模拟演示：用户询问降压药机制与具体选药剂量，由单任务检索 NLM 降压药资料并触发 Reviewer 证据契约校验。',
          knowledge_profile: 'medical',
          agent_id: 'consultation_agent',
          model_calls: 6,
          tool_calls: 1,
          worker_iterations: 2,
          context_status: 'simulated',
          response_origin: 'agent',
          safety_policy: null,
          task_count: 1,
          distinct_agent_count: 1,
          planned_agent_count: 1,
          started_task_count: 1,
          completed_task_count: 1,
          failed_task_count: 0,
          blocked_task_count: 0,
          evidence_status: 'passed',
          reviewer_status: 'failed',
          atomization_status: 'completed',
          review_rewrite_count: 0,
          review_rewrite_status: 'not_run',
          citation_support_status: 'unverified',
          clinical_review_status: 'not_run',
          reviewer_error_code: 'REVIEW_MEDICAL_EVIDENCE_REQUIRED',
          omitted_claim_count: 0,
          reviewed_answer_sha256: null,
          refinement_count: 0,
          schema_repair_count: 1,
          contract_repair_counts: { review: 1 },
          contract_diagnostics: [
            {
              stage: 'review',
              code: 'REVIEW_MEDICAL_EVIDENCE_REQUIRED',
              claim_index: 2,
              global_claim_index: 2,
            },
          ],
          memory_write_status: 'done',
          summary_write_status: 'not_run',
          maintenance_error_code: null,
          context_details: {
            memory_status: 'simulated',
            summary_status: 'empty',
            memory_count: 0,
          },
          sources: [],
          task_results: [
            {
              task_id: 'bp_med_mechanism',
              agent_id: 'consultation_agent',
              description: '检索 NLM 降压药资料，解释利尿剂与钙通道阻滞剂一般机制并拒绝提供个体剂量',
              depends_on: [],
              status: 'completed',
              safe_error_code: null,
              model_calls: 2,
              tool_calls: 1,
              worker_iterations: 2,
              refined: false,
              started: true,
            },
          ],
          review_packet_summary: {
            claims: 3,
            evidence: 2,
            chars: 277,
            documents: 1,
          },
          review_trace: [
            {
              round: 1,
              question_sha256: 'sim-question-sha256-bpmed-01',
              packet_sha256: 'sim-packet-sha256-bpmed-01',
              corpus_scope:
                '当前正式库为20份NLM/MedlinePlus公开成人高血压和2型糖尿病原文，中文为编辑摘述、非官方翻译、未专业复核；无个人实时病历。',
              status: 'failed',
              claims: [
                {
                  index: 0,
                  start: 0,
                  end: 23,
                  text: '利尿剂通过帮助身体排出多余的水和钠来降低血压。',
                  draft_ids: [0],
                  required_kind: 'medical_fact',
                },
                {
                  index: 1,
                  start: 23,
                  end: 45,
                  text: '钙通道阻滞剂通过帮助血管放松来发挥降压作用。',
                  draft_ids: [1],
                  required_kind: 'medical_fact',
                },
                {
                  index: 2,
                  start: 45,
                  end: 82,
                  text: '氨氯地平通常起始剂量为每天 5 mg，氢氯噻嗪为 12.5–25 mg。',
                  draft_ids: [2],
                  required_kind: 'medical_fact',
                },
              ],
              draft_spans: [
                {
                  index: 2,
                  start: 45,
                  end: 82,
                  text: '氨氯地平通常起始剂量为每天 5 mg，氢氯噻嗪为 12.5–25 mg。',
                },
              ],
              evidence: [
                buildVerifiedEvidenceAnchor('e0', 'nlm-bp-medicines', 1, 1), // Diuretics remove extra water and sodium
                buildVerifiedEvidenceAnchor('e1', 'nlm-bp-medicines', 1, 2), // two or more medicines work better than one
              ],
              policy_rules: {
                no_diagnosis_or_prescribing: '禁止提供个体选药、剂量或停药方案',
              },
              attempts: [
                {
                  batch: 1,
                  global_offset: 0,
                  claim_count: 3,
                  status: 'failed',
                  format_repair: false,
                  started_at: '2026-10-15T00:25:12Z',
                  diagnostic: {
                    stage: 'review',
                    code: 'REVIEW_MEDICAL_EVIDENCE_REQUIRED',
                    claim_index: 2,
                    global_claim_index: 2,
                  },
                  judgments: [
                    {
                      local_index: 0,
                      global_index: 0,
                      kind: 'medical_fact',
                      support_status: 'supported',
                      note: '利尿剂排出多余水和钠有 e0 原文支持。',
                      evidence_ids: ['e0'],
                      policy_rules: [],
                    },
                    {
                      local_index: 2,
                      global_index: 2,
                      kind: 'medical_fact',
                      support_status: 'supported',
                      note: '断言 #2 含具体毫克剂量但未绑定有效原文 evidence_ids，触发 REVIEW_MEDICAL_EVIDENCE_REQUIRED 契约阻断。',
                      evidence_ids: [],
                      policy_rules: [],
                    },
                  ],
                },
                {
                  batch: 1,
                  global_offset: 0,
                  claim_count: 3,
                  status: 'failed',
                  format_repair: true,
                  started_at: '2026-10-15T00:25:18Z',
                  diagnostic: {
                    stage: 'review',
                    code: 'REVIEW_MEDICAL_EVIDENCE_REQUIRED',
                    claim_index: 2,
                    global_claim_index: 2,
                  },
                },
              ],
            },
          ],
        },
        events: [
          { stage: 'safety_gate', task_id: null, status: 'completed' },
          { stage: 'load_context', task_id: null, status: 'completed' },
          { stage: 'route', task_id: null, status: 'completed' },
          { stage: 'plan', task_id: null, status: 'completed' },
          { stage: 'worker', task_id: null, status: 'completed' },
          { stage: 'tools', task_id: null, status: 'completed' },
          { stage: 'validate_output', task_id: null, status: 'completed' },
          { stage: 'review_answer', task_id: null, status: 'failed' },
          { stage: 'persist_result', task_id: null, status: 'partial' },
        ],
        providerCalls: [
          {
            provider: 'local_simulation',
            operation: 'sim_review_contract_check (REVIEW_MEDICAL_EVIDENCE_REQUIRED)',
            status: 'contract_blocked',
            http_status: null,
            safe_error_code: 'REVIEW_MEDICAL_EVIDENCE_REQUIRED',
            elapsed_seconds: null,
            usage: {},
          },
        ],
      },
    ],
  },
  {
    id: 'sim-session-4',
    title: '疑似酮症酸中毒急症风险信号',
    categoryTag: '紧急规则出口 · 0任务',
    statusBadge: 'no_source',
    statusText: '安全规则直出',
    summaryText:
      '本地结构模拟演示：当问题包含疑似酮症酸中毒、严重低血糖或高血压危象等紧急信号时，系统跳过常规检索与模型调用，直出就医提示且不虚构引用来源。',
    followUpSuggestions: [
      {
        label: '测试：超出正式库范围的罕见病提问（无来源）',
        question:
          '请问原发性醛固酮增多症导致的继发性高血压，肾上腺静脉采血（AVS）的左右侧皮质醇比值标准是多少？',
      },
    ],
    turns: [
      {
        id: 'sim-turn-urgent-01',
        question:
          '2型糖尿病患者现在测血糖很高，而且一直恶心呕吐、肚子痛、呼吸急促、口气有烂苹果味，还能在家先观察吃点降糖药吗？',
        createdAt: '10:28',
        run: {
          run_id: 'sim-run-urgent-01',
          request_id: 'sim-req-urgent-01',
          session_id: 'sim-session-4',
          run_status: 'finished',
          result_status: 'completed',
          answer:
            '你描述的情况包含可能危及生命的紧急医疗风险信号（如疑似糖尿病酮症酸中毒、严重低血糖或高血压急症表现）。请立即拨打急救电话或前往最近的急诊就医，不要等待本系统的常规知识整理，也不要自行加服或更改药物剂量。\n' +
            POLICY_NOTICE,
          safe_error_code: null,
          mode: 'offline_fake',
          graph_version: 3,
          checkpoint_id: 'sim-ckpt-urgent-01',
          stage: 'persist_result',
          plan_status: 'skipped',
          plan_reason: null,
          knowledge_profile: 'medical',
          agent_id: 'consultation_agent',
          model_calls: 0,
          tool_calls: 0,
          worker_iterations: 0,
          context_status: 'skipped_urgent',
          response_origin: 'urgent_policy',
          safety_policy: 'urgent',
          task_count: 0,
          distinct_agent_count: 0,
          planned_agent_count: 0,
          started_task_count: 0,
          completed_task_count: 0,
          failed_task_count: 0,
          blocked_task_count: 0,
          evidence_status: 'not_run',
          reviewer_status: 'skipped_policy',
          atomization_status: 'not_run',
          review_rewrite_count: 0,
          review_rewrite_status: 'not_run',
          citation_support_status: 'not_run',
          clinical_review_status: 'not_run',
          reviewer_error_code: null,
          omitted_claim_count: 0,
          reviewed_answer_sha256: null,
          refinement_count: 0,
          schema_repair_count: 0,
          memory_write_status: 'skipped_urgent_policy',
          summary_write_status: 'not_run',
          maintenance_error_code: null,
          context_details: {
            memory_status: 'skipped_urgent',
            summary_status: 'skipped_urgent',
            memory_count: 0,
          },
          sources: [],
          task_results: [],
          claim_reviews: [],
        },
        events: [
          { stage: 'safety_gate', task_id: null, status: 'completed' },
          { stage: 'persist_result', task_id: null, status: 'completed' },
        ],
        providerCalls: [],
      },
    ],
  },
  {
    id: 'sim-session-5',
    title: '血压 120/80 含义与测前准备',
    categoryTag: '服务暂不可用 · 失败状态',
    statusBadge: 'failed',
    statusText: '服务暂不可用',
    summaryText:
      '本地结构模拟演示：模拟上游模型服务返回 HTTP 503 导致子任务中断与下游任务阻断（DEPENDENCY_FAILED）。用户可点击重试体验恢复后的完整回答。',
    followUpSuggestions: [
      {
        label: '模拟服务恢复后重试此问题',
        question: '血压读数 120/80 mmHg 里的两个数字分别代表什么？测量血压前 30 分钟需要注意什么？',
      },
    ],
    turns: [
      {
        id: 'sim-turn-bp503-01',
        question: '血压读数 120/80 mmHg 里的两个数字分别代表什么？测量血压前 30 分钟需要注意什么？',
        createdAt: '10:30',
        run: {
          run_id: 'sim-run-bp503-01',
          request_id: 'sim-req-bp503-01',
          session_id: 'sim-session-5',
          run_status: 'failed',
          result_status: 'failed',
          answer: '本轮未完成，具体原因请查看运行状态。',
          safe_error_code: 'UPSTREAM_ERROR',
          mode: 'offline_fake',
          graph_version: 3,
          checkpoint_id: 'sim-ckpt-bp503-01',
          stage: 'persist_result',
          plan_status: 'completed',
          plan_reason:
            '结构模拟演示：问题涵盖血压收缩压/舒张压定义与血压测量前准备规范，拆分为检索 NLM 高血压基础与血压测量两份资料后汇总。',
          knowledge_profile: 'medical',
          agent_id: 'research_agent',
          model_calls: 2,
          tool_calls: 1,
          worker_iterations: 1,
          context_status: 'simulated',
          response_origin: 'agent',
          safety_policy: null,
          task_count: 2,
          distinct_agent_count: 1,
          planned_agent_count: 2,
          started_task_count: 1,
          completed_task_count: 0,
          failed_task_count: 1,
          blocked_task_count: 1,
          evidence_status: 'not_run',
          reviewer_status: 'not_run',
          atomization_status: 'not_run',
          review_rewrite_count: 0,
          review_rewrite_status: 'not_run',
          citation_support_status: 'not_run',
          clinical_review_status: 'not_run',
          reviewer_error_code: null,
          omitted_claim_count: 0,
          reviewed_answer_sha256: null,
          refinement_count: 0,
          schema_repair_count: 0,
          memory_write_status: 'skipped',
          summary_write_status: 'not_run',
          maintenance_error_code: null,
          context_details: {
            memory_status: 'simulated',
            summary_status: 'empty',
            memory_count: 0,
          },
          sources: [],
          task_results: [
            {
              task_id: 'retrieve_bp_docs',
              agent_id: 'research_agent',
              description: '检索 NLM 高血压基础知识（120/80 收缩压/舒张压）与血压测量准备章节',
              depends_on: [],
              status: 'failed',
              safe_error_code: 'UPSTREAM_ERROR',
              model_calls: 1,
              tool_calls: 1,
              worker_iterations: 1,
              refined: false,
              started: true,
            },
            {
              task_id: 'explain_bp_reading',
              agent_id: 'consultation_agent',
              description: '依赖检索结果，解释收缩压、舒张压含义及测前 30 分钟准备要求',
              depends_on: ['retrieve_bp_docs'],
              status: 'blocked',
              safe_error_code: 'DEPENDENCY_FAILED',
              model_calls: 0,
              tool_calls: 0,
              worker_iterations: 0,
              refined: false,
              started: false,
            },
          ],
        },
        events: [
          { stage: 'safety_gate', task_id: null, status: 'completed' },
          { stage: 'load_context', task_id: null, status: 'completed' },
          { stage: 'route', task_id: null, status: 'completed' },
          { stage: 'plan', task_id: null, status: 'completed' },
          { stage: 'dispatch', task_id: null, status: 'failed' },
          { stage: 'task_worker', task_id: 'retrieve_bp_docs', status: 'completed' },
          { stage: 'task_tools', task_id: 'retrieve_bp_docs', status: 'completed' },
          { stage: 'task_worker', task_id: 'retrieve_bp_docs', status: 'failed' },
          { stage: 'task_result', task_id: 'retrieve_bp_docs', status: 'failed' },
          { stage: 'persist_result', task_id: null, status: 'failed' },
        ],
        providerCalls: [
          {
            provider: 'local_simulation (deepseek_mock)',
            operation: 'chat.completions (plan)',
            status: 'simulated_ok',
            http_status: 200,
            safe_error_code: null,
            elapsed_seconds: null,
            usage: {},
          },
          {
            provider: 'local_simulation (deepseek_mock)',
            operation: 'chat.completions (task_worker:retrieve_bp_docs)',
            status: 'simulated_error',
            http_status: 503,
            safe_error_code: 'UPSTREAM_ERROR',
            elapsed_seconds: null,
            usage: {},
          },
        ],
      },
    ],
  },
]

export function generateSimulatedTurn(question: string, sessionId: string, turnIndex: number): MockTurn {
  const q = question.trim()
  const nowTime = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
  const safeSessionId = sessionId.startsWith('sim-') ? sessionId : `sim-${sessionId}`
  const suffix = `${turnIndex}-${Date.now().toString(36)}`

  // 1. eGFR vs UACR follow-up
  if (/egfr|滤过率/i.test(q)) {
    return {
      ...FOLLOW_UP_EGFR_TURN,
      id: `sim-turn-egfr-${suffix}`,
      question: q,
      createdAt: nowTime,
      run: {
        ...FOLLOW_UP_EGFR_TURN.run,
        run_id: `sim-run-egfr-${suffix}`,
        request_id: `sim-req-egfr-${suffix}`,
        checkpoint_id: `sim-ckpt-egfr-${suffix}`,
        session_id: safeSessionId,
      },
    }
  }

  // 2. Blood pressure 120/80 or measurement prep (e.g. retry of scenario 5)
  if (/120\/80|收缩压|舒张压|测量血压|30\s*分钟/i.test(q)) {
    const bpSys = buildVerifiedEvidenceAnchor('e0', 'nlm-hypertension', 0, 0)
    const bpDia = buildVerifiedEvidenceAnchor('e1', 'nlm-hypertension', 0, 1)
    const bp120 = buildVerifiedEvidenceAnchor('e2', 'nlm-hypertension', 0, 2)
    const bp30m = buildVerifiedEvidenceAnchor('e3', 'nlm-bp-test', 0, 0)
    const bpBath = buildVerifiedEvidenceAnchor('e4', 'nlm-bp-test', 0, 1)
    const bpArm = buildVerifiedEvidenceAnchor('e5', 'nlm-bp-test', 0, 2)
    const bpDays = buildVerifiedEvidenceAnchor('e6', 'nlm-bp-test', 1, 1)

    const bpComposed = composeReviewedAnswerAndClaims([
      {
        kind: 'medical_fact',
        support_status: 'supported',
        text: '血压是血液对动脉壁产生的压力，通常第一个数是收缩压（代表心脏搏动时的压力），第二个数是舒张压（代表心脏在两次搏动之间休息时的压力）；因此 120/80 表示收缩压 120、舒张压 80。',
        note: 'NLM 高血压基础知识页 3 处英文原文锚点直接支持收缩压、舒张压定义与 120/80 示例。',
        evidence: [bpSys, bpDia, bp120],
        review_round: 1,
        review_claim_index: 0,
        paragraphBreakAfter: true,
      },
      {
        kind: 'medical_fact',
        support_status: 'supported',
        text: '根据 NLM 血压测量资料，测量前至少 30 分钟应避免运动、酒精、烟草及含咖啡因饮食，并在检查前排空膀胱；测量时应坐下、双脚平放、手臂与心脏同高。医护人员通常结合不同日期两次或更多次偏高读数综合判断，单次读数不等于确诊高血压。',
        note: 'NLM 血压测量页支持测前 30 分钟准备、排空膀胱、手臂与心脏同高及不同日期多次读数判断。',
        evidence: [bp30m, bpBath, bpArm, bpDays],
        policy_rules: ['no_diagnosis_or_prescribing'],
        review_round: 1,
        review_claim_index: 1,
      },
    ])

    return {
      id: `sim-turn-bp-${suffix}`,
      question: q,
      createdAt: nowTime,
      run: {
        run_id: `sim-run-bp-${suffix}`,
        request_id: `sim-req-bp-${suffix}`,
        session_id: safeSessionId,
        run_status: 'finished',
        result_status: 'completed',
        answer: bpComposed.answer,
        safe_error_code: null,
        mode: 'offline_fake',
        graph_version: 3,
        checkpoint_id: `sim-ckpt-bp-${suffix}`,
        stage: 'persist_result',
        plan_status: 'completed',
        plan_reason: '结构模拟演示：合并检索 NLM 高血压基础知识（120/80 定义）与血压测量前准备规范，由单任务完成解释。',
        knowledge_profile: 'medical',
        agent_id: 'consultation_agent',
        model_calls: 5,
        tool_calls: 2,
        worker_iterations: 2,
        context_status: 'simulated',
        response_origin: 'agent',
        safety_policy: null,
        task_count: 1,
        distinct_agent_count: 1,
        planned_agent_count: 1,
        started_task_count: 1,
        completed_task_count: 1,
        failed_task_count: 0,
        blocked_task_count: 0,
        evidence_status: 'passed',
        reviewer_status: 'completed',
        atomization_status: 'completed',
        review_rewrite_count: 0,
        review_rewrite_status: 'not_needed',
        citation_support_status: 'model_reviewed',
        clinical_review_status: 'not_run',
        reviewer_error_code: null,
        omitted_claim_count: bpComposed.omitted_claim_count,
        reviewed_answer_sha256: `sim-sha256-bp-${suffix}`,
        refinement_count: 0,
        schema_repair_count: 0,
        memory_write_status: 'done',
        summary_write_status: 'not_run',
        maintenance_error_code: null,
        context_details: {
          memory_status: 'simulated',
          summary_status: 'empty',
          memory_count: 0,
        },
        sources: [
          buildVerifiedSource('nlm-hypertension', 0),
          buildVerifiedSource('nlm-bp-test', 0),
          buildVerifiedSource('nlm-bp-test', 1, [1]),
        ],
        task_results: [
          {
            task_id: 'explain_bp_and_prep',
            agent_id: 'consultation_agent',
            description: '检索 NLM 高血压定义与血压测量准备章节，解释 120/80 与测前 30 分钟注意事项',
            depends_on: [],
            status: 'completed',
            safe_error_code: null,
            model_calls: 2,
            tool_calls: 2,
            worker_iterations: 2,
            refined: false,
            started: true,
          },
        ],
        claim_reviews: bpComposed.claim_reviews,
      },
      events: [
        { stage: 'safety_gate', task_id: null, status: 'completed' },
        { stage: 'load_context', task_id: null, status: 'completed' },
        { stage: 'route', task_id: null, status: 'completed' },
        { stage: 'plan', task_id: null, status: 'completed' },
        { stage: 'worker', task_id: null, status: 'completed' },
        { stage: 'tools', task_id: null, status: 'completed' },
        { stage: 'validate_output', task_id: null, status: 'completed' },
        { stage: 'review_answer', task_id: null, status: 'completed' },
        { stage: 'persist_result', task_id: null, status: 'completed' },
      ],
      providerCalls: [
        {
          provider: 'local_simulation',
          operation: 'sim_retry_success (nlm-hypertension + nlm-bp-test)',
          status: 'simulated_ok',
          http_status: null,
          safe_error_code: null,
          elapsed_seconds: null,
          usage: {},
        },
      ],
    }
  }

  // 3. Stopping medicine / antihypertensive mechanisms / fasting coffee or gum
  if (/停药|利尿剂|钙通道|降压药|空腹|咖啡|口香糖/i.test(q)) {
    const medDiuretic = buildVerifiedEvidenceAnchor('e0', 'nlm-bp-medicines', 1, 1)
    const medLifestyle = buildVerifiedEvidenceAnchor('e1', 'nlm-bp-medicines', 0, 1)
    const fastNoStop = buildVerifiedEvidenceAnchor('e2', 'nlm-fasting-test', 1, 0)
    const fastResched = buildVerifiedEvidenceAnchor('e3', 'nlm-fasting-test', 1, 1)
    const fastCoffee = buildVerifiedEvidenceAnchor('e4', 'nlm-fasting-test', 1, 2)
    const fastWater = buildVerifiedEvidenceAnchor('e5', 'nlm-fasting-test', 0, 0)

    const medComposed = composeReviewedAnswerAndClaims([
      {
        kind: 'medical_fact',
        support_status: 'supported',
        text: '根据 NLM 降压药物资料，利尿剂通过帮助身体排出多余的水和钠来降低血压，钙通道阻滞剂帮助血管放松；服药期间仍需保持健康生活方式。',
        note: 'NLM 降压药页面两处章节支持利尿剂机制与保持健康生活方式。',
        evidence: [medDiuretic, medLifestyle],
        review_round: 1,
        review_claim_index: 0,
        paragraphBreakAfter: true,
      },
      {
        kind: 'medical_fact',
        support_status: 'supported',
        text: '进行空腹验血时，除白水外通常不能进食或饮用咖啡、果汁、汽水等饮料，也应避免嚼口香糖、吸烟和运动；除非医护人员明确要求，不应自行停用日常药物，若误进食或喝了非白水饮料应告知医护人员以确认是否重新安排检查。',
        note: 'NLM 验血前空腹准备页 4 处英文原文锚点支持仅饮白水、禁饮咖啡/果汁、不自行停药及误饮后联系医护。',
        evidence: [fastWater, fastCoffee, fastNoStop, fastResched],
        policy_rules: ['no_diagnosis_or_prescribing'],
        review_round: 1,
        review_claim_index: 1,
      },
    ])

    return {
      id: `sim-turn-med-${suffix}`,
      question: q,
      createdAt: nowTime,
      run: {
        run_id: `sim-run-med-${suffix}`,
        request_id: `sim-req-med-${suffix}`,
        session_id: safeSessionId,
        run_status: 'finished',
        result_status: 'completed',
        answer: medComposed.answer,
        safe_error_code: null,
        mode: 'offline_fake',
        graph_version: 3,
        checkpoint_id: `sim-ckpt-med-${suffix}`,
        stage: 'persist_result',
        plan_status: 'completed',
        plan_reason: '结构模拟演示：检索 NLM 降压药一般机制与空腹验血准备边界，单任务完成解释。',
        knowledge_profile: 'medical',
        agent_id: 'consultation_agent',
        model_calls: 5,
        tool_calls: 2,
        worker_iterations: 2,
        context_status: 'simulated',
        response_origin: 'agent',
        safety_policy: null,
        task_count: 1,
        distinct_agent_count: 1,
        planned_agent_count: 1,
        started_task_count: 1,
        completed_task_count: 1,
        failed_task_count: 0,
        blocked_task_count: 0,
        evidence_status: 'passed',
        reviewer_status: 'completed',
        atomization_status: 'completed',
        review_rewrite_count: 0,
        review_rewrite_status: 'not_needed',
        citation_support_status: 'model_reviewed',
        clinical_review_status: 'not_run',
        reviewer_error_code: null,
        omitted_claim_count: medComposed.omitted_claim_count,
        reviewed_answer_sha256: `sim-sha256-med-${suffix}`,
        refinement_count: 0,
        schema_repair_count: 0,
        memory_write_status: 'done',
        summary_write_status: 'not_run',
        maintenance_error_code: null,
        context_details: {
          memory_status: 'simulated',
          summary_status: 'empty',
          memory_count: 0,
        },
        sources: [
          buildVerifiedSource('nlm-bp-medicines', 0, [1]),
          buildVerifiedSource('nlm-bp-medicines', 1, [1]),
          buildVerifiedSource('nlm-fasting-test', 0, [0]),
          buildVerifiedSource('nlm-fasting-test', 1),
        ],
        task_results: [
          {
            task_id: 'explain_med_and_fasting',
            agent_id: 'consultation_agent',
            description: '检索 NLM 降压药机制与空腹验血用药规则，说明不能自行停药及误饮处理',
            depends_on: [],
            status: 'completed',
            safe_error_code: null,
            model_calls: 2,
            tool_calls: 2,
            worker_iterations: 2,
            refined: false,
            started: true,
          },
        ],
        claim_reviews: medComposed.claim_reviews,
      },
      events: [
        { stage: 'safety_gate', task_id: null, status: 'completed' },
        { stage: 'load_context', task_id: null, status: 'completed' },
        { stage: 'route', task_id: null, status: 'completed' },
        { stage: 'plan', task_id: null, status: 'completed' },
        { stage: 'worker', task_id: null, status: 'completed' },
        { stage: 'tools', task_id: null, status: 'completed' },
        { stage: 'validate_output', task_id: null, status: 'completed' },
        { stage: 'review_answer', task_id: null, status: 'completed' },
        { stage: 'persist_result', task_id: null, status: 'completed' },
      ],
      providerCalls: [
        {
          provider: 'local_simulation',
          operation: 'sim_turn (nlm-bp-medicines + nlm-fasting-test)',
          status: 'simulated_ok',
          http_status: null,
          safe_error_code: null,
          elapsed_seconds: null,
          usage: {},
        },
      ],
    }
  }

  // 4. Fallback out-of-scope / no-source response in local simulation mode
  return {
    id: `sim-turn-nosc-${suffix}`,
    question: q,
    createdAt: nowTime,
    run: {
      run_id: `sim-run-nosc-${suffix}`,
      request_id: `sim-req-nosc-${suffix}`,
      session_id: safeSessionId,
      run_status: 'finished',
      result_status: 'partial',
      answer:
        '当前正式医学知识库仅包含 20 份美国 NLM/MedlinePlus 成人高血压与 2 型糖尿病公开健康教育资料（40 个中英对齐章节片段）。你询问的内容超出当前已入库快照的直接覆盖范围（未命中有效原文锚点），系统不编造库外医学依据或临床指南结论。\n' +
        '建议切换至已入库主题（如：120/80 收缩压/舒张压含义、血压测量前准备、降压药一般机制、HbA1c 与指尖血糖区别、UACR 与 eGFR 肾脏检查、空腹验血准备），或切换到“后端联调”连接本地 8010 服务进行检索。\n' +
        POLICY_NOTICE,
      safe_error_code: 'EVIDENCE_MISSING',
      mode: 'offline_fake',
      graph_version: 3,
      checkpoint_id: `sim-ckpt-nosc-${suffix}`,
      stage: 'persist_result',
      plan_status: 'completed',
      plan_reason: '结构模拟演示：在本地 20 份 NLM 正式库快照中未匹配到支撑片段，明确返回无来源边界，不生成无依据医学断言。',
      knowledge_profile: 'medical',
      agent_id: 'research_agent',
      model_calls: 2,
      tool_calls: 1,
      worker_iterations: 1,
      context_status: 'simulated',
      response_origin: 'agent',
      safety_policy: null,
      task_count: 1,
      distinct_agent_count: 1,
      planned_agent_count: 1,
      started_task_count: 1,
      completed_task_count: 0,
      failed_task_count: 1,
      blocked_task_count: 0,
      evidence_status: 'issues',
      reviewer_status: 'not_run',
      atomization_status: 'not_run',
      review_rewrite_count: 0,
      review_rewrite_status: 'not_run',
      citation_support_status: 'unverified',
      clinical_review_status: 'not_run',
      reviewer_error_code: null,
      omitted_claim_count: 0,
      reviewed_answer_sha256: null,
      refinement_count: 1,
      schema_repair_count: 0,
      memory_write_status: 'done',
      summary_write_status: 'not_run',
      maintenance_error_code: null,
      context_details: {
        memory_status: 'simulated',
        summary_status: 'empty',
        memory_count: 0,
      },
      sources: [],
      task_results: [
        {
          task_id: 'search_medical_corpus',
          agent_id: 'research_agent',
          description: '在 20 份 NLM/MedlinePlus 成人高血压与 2 型糖尿病知识库中检索匹配原文片段',
          depends_on: [],
          status: 'partial',
          safe_error_code: 'EVIDENCE_MISSING',
          model_calls: 2,
          tool_calls: 1,
          worker_iterations: 1,
          refined: true,
          started: true,
        },
      ],
      evidence_diagnostics: [
        {
          task_id: 'search_medical_corpus',
          stage: 'retrieval',
          tool: 'search_medical_knowledge',
          status: 'no_match',
          retrieved_count: 0,
          retrieved_ids: [],
          refinement: true,
          safe_error_code: 'EVIDENCE_MISSING',
        },
      ],
    },
    events: [
      { stage: 'safety_gate', task_id: null, status: 'completed' },
      { stage: 'load_context', task_id: null, status: 'completed' },
      { stage: 'route', task_id: null, status: 'completed' },
      { stage: 'plan', task_id: null, status: 'completed' },
      { stage: 'worker', task_id: null, status: 'completed' },
      { stage: 'tools', task_id: null, status: 'completed' },
      { stage: 'check_evidence', task_id: null, status: 'rechecking' },
      { stage: 'persist_result', task_id: null, status: 'partial' },
    ],
    providerCalls: [],
  }
}

export function turnsToMessages(turns: MockTurn[]): MessageItem[] {
  const items: MessageItem[] = []
  let seq = 1
  for (const t of turns) {
    items.push({
      id: `${t.id}-u`,
      run_id: t.run.run_id,
      seq: seq++,
      role: 'user',
      content: t.question,
      created_at: t.createdAt,
    })
    if (t.run.answer) {
      items.push({
        id: `${t.id}-a`,
        run_id: t.run.run_id,
        seq: seq++,
        role: 'assistant',
        content: t.run.answer,
        created_at: t.createdAt,
      })
    }
  }
  return items
}
