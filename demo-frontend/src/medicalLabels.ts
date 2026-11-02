import type {
  ClaimReviewItem,
  EvidenceAnchor,
  ExecutionEventItem,
  RunOut,
  SourceItem,
  TaskResultItem,
} from './types.ts'

export const STATUS_LABELS: Record<string, string> = {
  running: '执行中',
  finished: '已结束',
  completed: '已完成',
  partial: '部分完成',
  failed: '运行失败',
  cancelled: '已取消',
  timed_out: '执行超时',
  awaiting_input: '等待补充说明',
  paused: '已暂停（可恢复）',
  blocked: '前置依赖未完成',
  passed: '任务引用核对通过',
  issues: '存在证据缺口',
  rechecking: '定向补查中',
  not_run: '未执行',
  not_needed: '无需改写',
  not_available: '未启用',
  skipped_policy: '规则安全出口跳过',
  skipped_urgent: '紧急出口跳过',
  skipped_urgent_policy: '紧急出口跳过',
  urgent_policy: '紧急医疗规则出口',
  agent: 'Agent 编排流程',
  model_reviewed: '引用核对完成',
  unverified: '引用未完成核对',
  pending: '待执行',
  ready: '已就绪',
  empty: '无记录或无命中',
  stale: '摘要待更新',
  invalidated: '旧摘要已失效',
  budget_omitted: '受上下文预算省略',
  done: '已完成',
  processing: '后台维护中',
  uncertain: '结果待核对',
  awaiting_remote: '远端同步中',
  superseded: '已被新版替代',
  skipped: '跳过',
  deleted: '已撤回',
  active: '有效',
  offline_fake: '离线模拟 (offline_fake)',
  cloud_real: '真实云模型 (cloud_real)',
  hybrid: '混合检索模式 (hybrid)',
  simulated: '本地模拟',
  degraded: '上下文降级运行',
  supported: '原文支持 (进入回答)',
  partially_supported: '仅部分支持 (未进入最终回答)',
  unsupported: '缺乏原文支持 (未进入最终回答)',
  contradicted: '与原文冲突 (未进入最终回答)',
}

export const STAGE_LABELS: Record<string, string> = {
  safety_gate: '紧急安全规则门禁',
  load_context: '加载会话上下文与记忆',
  route: '复杂度路由判断',
  clarify: '请求用户澄清',
  plan: 'Lead 规划任务拓扑',
  worker: '单任务 Worker 推理',
  tools: '调用本地知识检索工具',
  validate_output: '输出与引用标识校验',
  dispatch: '多任务 DAG 并发调度',
  task_worker: '子任务 Worker 推理',
  task_tools: '子任务检索工具调用',
  task_validate: '子任务输出与引用校验',
  task_result: '子任务持久化结果',
  check_evidence: '多任务证据一致性核查',
  synthesize: 'Lead 汇总多任务输出',
  review_answer: '原子事实拆分与两轮引用审核',
  persist_result: '事务写入最终回复与审计',
  cancel_requested: '收到取消请求',
  cancel: '终止运行',
}

export const AGENT_ROLE_LABELS: Record<string, { name: string; shortName: string; duty: string }> = {
  consultation_agent: {
    name: '健康知识解释 (consultation_agent)',
    shortName: '健康知识解释',
    duty: '通俗解释疾病机制、检查准备与生活方式管理，声明资料适用范围',
  },
  research_agent: {
    name: '医学资料检索 (research_agent)',
    shortName: '医学资料检索',
    duty: '检索 NLM/MedlinePlus 原始中英对照章节并绑定原文位置快照',
  },
  diagnostic_agent: {
    name: '规则与边界核查 (diagnostic_agent)',
    shortName: '规则与边界核查',
    duty: '核查前置证据覆盖、测量条件差异与适用范围边界（不作临床诊断）',
  },
}

export const CLAIM_KIND_LABELS: Record<string, string> = {
  medical_fact: '医学事实断言',
  project_behavior: '项目安全与医疗边界声明',
  corpus_scope: '知识库固定范围说明',
  editorial: '结构组织语句',
}

export interface UserFacingFailureSummary {
  whatHappened: string
  whatIsIncomplete: string
  nextStep: string
  technicalCode: string | null
}

export function describeUserFacingFailure(
  run: RunOut | null | undefined,
): UserFacingFailureSummary | null {
  if (!run) return null
  const code = run.safe_error_code || run.reviewer_error_code
  const isFailed = run.run_status === 'failed' || run.result_status === 'failed'
  const isReviewerBlocked = run.reviewer_status === 'failed'
  const isTimedOut = run.run_status === 'timed_out' || run.result_status === 'timed_out'
  const isCancelled = run.run_status === 'cancelled' || run.result_status === 'cancelled'

  if (!isFailed && !isReviewerBlocked && !isTimedOut && !isCancelled && code !== 'EVIDENCE_MISSING') {
    return null
  }

  if (code === 'UPSTREAM_ERROR') {
    return {
      whatHappened: '上游模型服务暂时不可用，本轮请求在执行中途中断。',
      whatIsIncomplete: '检索后的回答生成与逐句引用核对尚未完成，系统未输出未经核对的医学内容。',
      nextStep: '可点击下方“重试本轮提问”再次发起，或打开右侧“执行与审核”查看失败节点详情。',
      technicalCode: code,
    }
  }

  if (isReviewerBlocked || code === 'REVIEW_MEDICAL_EVIDENCE_REQUIRED') {
    return {
      whatHappened: '回答初稿中包含缺少 NLM 原文锚点支持的医学断言（如具体毫克剂量或个体选药），未通过安全审核。',
      whatIsIncomplete: '初稿已被安全拦截，未作为正式医学回答展示。',
      nextStep: '可改问药物的一般作用机制，或打开右侧“执行与审核”查看被拦截的原稿断言与原因。',
      technicalCode: code || 'REVIEW_FAILED',
    }
  }

  if (code === 'EVIDENCE_MISSING') {
    return {
      whatHappened: '当前 20 份 NLM 成人高血压与 2 型糖尿病知识库中未检索到直接支持该问题的原文片段。',
      whatIsIncomplete: '系统拒绝在无原文依据时编造库外医学结论。',
      nextStep: '建议改问已入库的高血压或 2 型糖尿病常见检查与管理问题。',
      technicalCode: code,
    }
  }

  if (isTimedOut || code === 'RUN_TIMEOUT' || code === 'STEP_TIMEOUT') {
    return {
      whatHappened: '本轮处理超出最大允许等待时间，运行已安全终止。',
      whatIsIncomplete: '完整回答汇总或引用审核尚未完成。',
      nextStep: '可简化问题范围后点击“重试本轮提问”。',
      technicalCode: code || 'RUN_TIMEOUT',
    }
  }

  if (isCancelled || code === 'CANCELLED') {
    return {
      whatHappened: '本轮运行已由用户主动取消。',
      whatIsIncomplete: '后续任务节点与回答生成已停止。',
      nextStep: '可随时重新提交提问或切换其他会话。',
      technicalCode: 'CANCELLED',
    }
  }

  return {
    whatHappened: '本轮处理未能完整完成。',
    whatIsIncomplete: '部分任务或引用核对步骤未产出最终结果。',
    nextStep: '可点击“重试本轮提问”，或展开技术详情查看诊断信息。',
    technicalCode: code || null,
  }
}

export const SAFE_ERROR_DESCRIPTIONS: Record<string, { title: string; detail: string }> = {
  UPSTREAM_ERROR: {
    title: '上游模型服务暂时不可用 (HTTP 503 / UPSTREAM_ERROR)',
    detail: '模型接口返回 503 或连接超时。系统拒绝将失败请求静默降级为假回答，未生成未经审核的医学结论。',
  },
  REVIEW_SUPPORT_INCOMPLETE: {
    title: '部分原子事实缺乏充分原文支持，已由审核器保守省略',
    detail: 'Reviewer 对回答进行了逐句原子事实核对与一次有界改写复审；超出 NLM 原文快照的延伸表述已被剔除，仅保留有明确原文依据的结论。',
  },
  REVIEW_MEDICAL_EVIDENCE_REQUIRED: {
    title: '医学事实断言缺少原文锚点支持 (REVIEW_MEDICAL_EVIDENCE_REQUIRED)',
    detail: '审核器检测到包含具体数值、因果或医疗判断的语句未绑定有效 NLM 原文片段，已阻断未审核原稿输出。',
  },
  REVIEW_POLICY_CLASSIFICATION_INVALID: {
    title: '审核分类契约不匹配 (REVIEW_POLICY_CLASSIFICATION_INVALID)',
    detail: '安全边界声明与医学事实分类未通过本地强校验，已阻断未完成核对的原稿。',
  },
  REVIEW_FACT_CLASSIFICATION_INVALID: {
    title: '医学事实被误标为普通说明 (REVIEW_FACT_CLASSIFICATION_INVALID)',
    detail: '包含生理机制、剂量单位或风险变化的语句必须按 medical_fact 绑定原文证据。',
  },
  EVIDENCE_MISSING: {
    title: '未检索到匹配的医学知识库来源 (EVIDENCE_MISSING)',
    detail: '当前 20 份 NLM/MedlinePlus 成人高血压与 2 型糖尿病正式库中未找到支持该问题的直接证据。',
  },
  MODEL_BUDGET_EXCEEDED: {
    title: '达到单轮模型调用预算上限 (MODEL_BUDGET_EXCEEDED)',
    detail: '单轮最多允许 16 次模型调用（含规划、Worker、汇总与两轮审核）。',
  },
  TOOL_BUDGET_EXCEEDED: {
    title: '达到工具调用预算上限 (TOOL_BUDGET_EXCEEDED)',
    detail: '已达到本轮知识库检索工具调用上限，仅保留已获取的资料。',
  },
  DEPENDENCY_FAILED: {
    title: '前置依赖任务未完成 (DEPENDENCY_FAILED)',
    detail: 'DAG 中上游检索任务失败或超时，当前下游任务被自动阻断，不额外消耗模型调用。',
  },
  CANCELLED: {
    title: '运行已由用户取消 (CANCELLED)',
    detail: '已停止后续节点执行并保留当前会话状态。',
  },
  RUN_TIMEOUT: {
    title: '整轮运行超时 (RUN_TIMEOUT)',
    detail: '超出单轮最大允许执行时间（90秒），运行安全终止。',
  },
}

export function formatLabel(key: string | null | undefined): string {
  if (!key) return '未知'
  return STATUS_LABELS[key] || key
}

export function formatStage(stage: string | null | undefined): string {
  if (!stage) return '未记录阶段'
  return STAGE_LABELS[stage] || stage
}

export function formatAgentRole(agentId: string | null | undefined): {
  name: string
  shortName: string
  duty: string
} {
  if (!agentId) return { name: '未指定角色', shortName: '未指定角色', duty: '' }
  return (
    AGENT_ROLE_LABELS[agentId] || {
      name: agentId,
      shortName: agentId,
      duty: '执行分配的子任务',
    }
  )
}

export function describeSafeError(
  code: string | null | undefined,
): { title: string; detail: string } | null {
  if (!code) return null
  return (
    SAFE_ERROR_DESCRIPTIONS[code] || {
      title: `运行诊断代码：${code}`,
      detail: '请查看下方节点与审核详情了解具体阶段记录。',
    }
  )
}

export function isSimulatedRun(run: RunOut | null | undefined, isSimulationMode = false): boolean {
  if (isSimulationMode) return true
  if (!run) return false
  return run.run_id.startsWith('sim-') || run.mode === 'offline_fake'
}

export function formatCallCount(
  count: number | null | undefined,
  unit: string,
  simulated: boolean,
): string {
  if (count === null || count === undefined) return '未知'
  return `${simulated ? '模拟 ' : ''}${count} ${unit}`
}

/**
 * Normalizes the actual tasks that participated in a run.
 * Never hardcodes 3 experts: uses `task_results` when multi-task dispatch ran,
 * or synthesizes the single-task execution record when Lead selected a 1-task plan.
 */
export function resolveActualTasks(run: RunOut | null | undefined): TaskResultItem[] {
  if (!run) return []
  if (Array.isArray(run.task_results) && run.task_results.length > 0) {
    return run.task_results
  }
  if (
    run.response_origin === 'urgent_policy' ||
    (run.plan_status === 'skipped' && run.task_count === 0)
  ) {
    return []
  }
  if ((run.task_count === 1 || run.agent_id) && run.plan_status !== 'failed') {
    const status =
      run.run_status === 'running'
        ? 'running'
        : run.result_status === 'completed' || run.result_status === 'partial'
          ? 'completed'
          : run.result_status || run.run_status
    return [
      {
        task_id: 'single_worker',
        agent_id: run.agent_id || 'consultation_agent',
        description:
          run.plan_reason ||
          'Lead 判定为单一主题知识问答，由单任务直接完成本地医学库检索与回答生成。',
        depends_on: [],
        status,
        safe_error_code: null,
        model_calls: run.model_calls ?? 0,
        tool_calls: run.tool_calls ?? (run.sources?.length ? 1 : 0),
        worker_iterations: run.worker_iterations ?? undefined,
        refined: run.refinement_count > 0,
        started: true,
      },
    ]
  }
  return []
}

export interface FlowWave {
  waveIndex: number
  title: string
  tasks: TaskResultItem[]
}

/**
 * Organizes actual tasks into topological dependency waves for visual DAG rendering.
 */
export function buildTaskWaves(tasks: TaskResultItem[]): FlowWave[] {
  if (!tasks.length) return []
  const depthMap = new Map<string, number>()
  const byId = new Map<string, TaskResultItem>()
  for (const t of tasks) byId.set(t.task_id, t)

  function getDepth(taskId: string, visited = new Set<string>()): number {
    if (depthMap.has(taskId)) return depthMap.get(taskId)!
    if (visited.has(taskId)) return 0
    visited.add(taskId)
    const task = byId.get(taskId)
    if (!task || !task.depends_on || !task.depends_on.length) {
      depthMap.set(taskId, 0)
      return 0
    }
    let maxParent = 0
    for (const dep of task.depends_on) {
      if (byId.has(dep)) {
        maxParent = Math.max(maxParent, getDepth(dep, new Set(visited)) + 1)
      }
    }
    depthMap.set(taskId, maxParent)
    return maxParent
  }

  for (const t of tasks) getDepth(t.task_id)
  const waveGroups = new Map<number, TaskResultItem[]>()
  for (const t of tasks) {
    const d = depthMap.get(t.task_id) ?? 0
    const list = waveGroups.get(d) || []
    list.push(t)
    waveGroups.set(d, list)
  }

  return Array.from(waveGroups.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([depth, group]) => ({
      waveIndex: depth + 1,
      title:
        tasks.length === 1
          ? '单任务执行'
          : depth === 0
            ? '第 1 波（无前置依赖）'
            : `第 ${depth + 1} 波（依赖前置结果）`,
      tasks: group,
    }))
}

export function summarizeClaims(claims: ClaimReviewItem[] | undefined): {
  total: number
  supported: number
  omitted: number
  medicalFacts: number
  policyOrScope: number
} {
  if (!claims || !claims.length) {
    return { total: 0, supported: 0, omitted: 0, medicalFacts: 0, policyOrScope: 0 }
  }
  let supported = 0
  let omitted = 0
  let medicalFacts = 0
  let policyOrScope = 0
  for (const c of claims) {
    if (c.support_status === 'supported') supported++
    else omitted++
    if (c.kind === 'medical_fact') medicalFacts++
    else if (c.kind === 'project_behavior' || c.kind === 'corpus_scope') policyOrScope++
  }
  return { total: claims.length, supported, omitted, medicalFacts, policyOrScope }
}

export interface MappedAnswerClaim {
  kind: 'claim' | 'text'
  text: string
  start: number
  end: number
  separatorAfter?: string // Original line breaks between paragraphs, excluded from claim offsets.
  claim: ClaimReviewItem
  sourceNumbers: number[] // 1-based indices into run.sources
  evidenceAnchors: EvidenceAnchor[]
  isMedicalFactWithEvidence: boolean
  isPolicyOrScope: boolean
}

export const POLICY_NOTICE_TEXT =
  '资料来自美国NLM/MedlinePlus，中文为编辑解释，未经过医学专业复核；不替代个体诊断或用药建议。'
export const OMITTED_NOTICE_PREFIX = '部分内容缺少充分的原文或项目规则支持，已省略'
export const OMITTED_NOTICE_TEXT =
  OMITTED_NOTICE_PREFIX + '；如需更完整解释，请补充相关原文或向医护核对。'
export const BLOCKED_REVIEW_PREFIX = '本轮逐项引用审核未完成，暂不返回未经审核的医学结论'
export const FAILED_PLACEHOLDER_PREFIX = '本轮未完成，具体原因请查看运行状态'

/**
 * Builds a lookup array mapping Unicode code-point index (used by Python `len()`)
 * to JavaScript UTF-16 code-unit index (used by `String.prototype.slice()`).
 */
export function buildCodePointToUtf16Map(text: string): number[] {
  const map: number[] = [0]
  let utf16Pos = 0
  for (const ch of Array.from(text)) {
    utf16Pos += ch.length
    map.push(utf16Pos)
  }
  return map
}

/**
 * Resolves a claim's `[final_start, final_end]` against `bodyText`.
 * Primary rule: interprets `[final_start, final_end]` as Python Unicode code-point offsets.
 * Secondary rule: falls back to direct UTF-16 offsets if caller constructed offsets in JS UTF-16 units.
 * Strictly requires the sliced substring to equal `expectedText`. Never guesses by search.
 */
export function resolveClaimUtf16Range(
  bodyText: string,
  codePointMap: number[],
  finalStart: number | null | undefined,
  finalEnd: number | null | undefined,
  expectedText: string,
): { start: number; end: number; offsetMode: 'code_point' | 'utf16' } | null {
  if (
    typeof finalStart !== 'number' ||
    typeof finalEnd !== 'number' ||
    !Number.isInteger(finalStart) ||
    !Number.isInteger(finalEnd) ||
    finalStart < 0 ||
    finalEnd <= finalStart ||
    !expectedText
  ) {
    return null
  }

  // Rule 1: Python Unicode code-point offsets -> JS UTF-16 offsets
  if (finalEnd < codePointMap.length) {
    const uStart = codePointMap[finalStart]!
    const uEnd = codePointMap[finalEnd]!
    if (uEnd <= bodyText.length && bodyText.slice(uStart, uEnd) === expectedText) {
      return { start: uStart, end: uEnd, offsetMode: 'code_point' }
    }
  }

  // Rule 2: Direct JS UTF-16 offsets
  if (finalEnd <= bodyText.length && bodyText.slice(finalStart, finalEnd) === expectedText) {
    return { start: finalStart, end: finalEnd, offsetMode: 'utf16' }
  }

  return null
}

/**
 * Separates trailing system notices (`OMITTED_NOTICE` and `POLICY_NOTICE`) from the main body text
 * without altering the starting offset `0` of `bodyText`.
 */
export function extractAnswerBodyAndNotices(rawAnswer: string | null | undefined): {
  bodyText: string
  omittedNotice: string
  policyNotice: string
  isSystemFailurePlaceholder: boolean
} {
  if (!rawAnswer || !rawAnswer.trim()) {
    return {
      bodyText: '',
      omittedNotice: '',
      policyNotice: '',
      isSystemFailurePlaceholder: false,
    }
  }

  const source = rawAnswer
  let endIdx = source.length
  function stripExactSuffix(notice: string): string {
    const candidate = source.slice(0, endIdx).trimEnd()
    if (!candidate.endsWith(notice)) return ''
    const noticeStart = candidate.length - notice.length
    const before = source.slice(0, noticeStart)
    // Remove the separator of a standalone notice, never the preceding prose on its line.
    const separator = before.match(/(?:\r?\n)[ \t\r\n]*$/)
    endIdx = separator ? noticeStart - separator[0].length : noticeStart
    return notice
  }
  const policyNotice = stripExactSuffix(POLICY_NOTICE_TEXT)
  const omittedNotice = stripExactSuffix(OMITTED_NOTICE_TEXT)

  const bodyText = rawAnswer.slice(0, endIdx)
  const trimmedBody = bodyText.trim()
  const isSystemFailurePlaceholder =
    trimmedBody.startsWith(BLOCKED_REVIEW_PREFIX) ||
    trimmedBody.startsWith(FAILED_PLACEHOLDER_PREFIX)

  return {
    bodyText,
    omittedNotice,
    policyNotice,
    isSystemFailurePlaceholder,
  }
}

export interface AnswerSegmentationResult {
  hasReliableMapping: boolean
  mappingStatus: 'complete' | 'partial' | 'fallback_plain' | 'none'
  hasMappingAnomaly: boolean
  invalidClaimCount: number
  duplicateClaimCount: number
  overlapConflictCount: number
  bodyText: string
  omittedNotice: string
  policyNotice: string
  isSystemFailurePlaceholder: boolean
  paragraphs: MappedAnswerClaim[][]
  omittedClaims: ClaimReviewItem[]
}

export function reconstructVisibleBodyText(
  result: Pick<AnswerSegmentationResult, 'paragraphs'>,
): string {
  return result.paragraphs
    .map(para => para.map(seg => seg.text).join('') + (para.at(-1)?.separatorAfter ?? ''))
    .join('')
}

function makeUnmappedTextSegment(text: string, start: number, end: number): MappedAnswerClaim {
  return {
    kind: 'text',
    text,
    start,
    end,
    claim: {
      index: -1,
      kind: 'unmapped_text',
      support_status: 'supported',
      evidence_ids: [],
      evidence: [],
      policy_rules: [],
      note: '',
      text,
      draft_start: null,
      draft_end: null,
      final_start: start,
      final_end: end,
    },
    sourceNumbers: [],
    evidenceAnchors: [],
    isMedicalFactWithEvidence: false,
    isPolicyOrScope: false,
  }
}

/**
 * Partitions `run.answer` body text into contiguous segments so that `run.answer` is ALWAYS the
 * single source of truth for rendered prose:
 * - Valid non-overlapping claim spans get citation locators (`kind: 'claim'`).
 * - Unmapped prefixes, inter-sentence gaps, suffixes, or claims with invalid/corrupted offsets
 *   are preserved verbatim as plain text (`kind: 'text'`) without guessing citations.
 * - Omitted claims (`support_status !== 'supported'`) never re-enter the body text.
 */
export function resolveAnswerClaimSegments(
  run: RunOut | null | undefined,
  answerText: string | null | undefined,
): AnswerSegmentationResult {
  const omittedClaims = (run?.claim_reviews || []).filter(c => c.support_status !== 'supported')
  const raw = answerText ?? run?.answer ?? ''
  const extracted = extractAnswerBodyAndNotices(raw)

  if (!extracted.bodyText || extracted.isSystemFailurePlaceholder) {
    return {
      hasReliableMapping: false,
      mappingStatus: 'none',
      hasMappingAnomaly: false,
      invalidClaimCount: 0,
      duplicateClaimCount: 0,
      overlapConflictCount: 0,
      bodyText: extracted.bodyText,
      omittedNotice: extracted.omittedNotice,
      policyNotice: extracted.policyNotice,
      isSystemFailurePlaceholder: extracted.isSystemFailurePlaceholder,
      paragraphs: [],
      omittedClaims,
    }
  }

  const bodyText = extracted.bodyText
  const codePointMap = buildCodePointToUtf16Map(raw)

  const sources: SourceItem[] = run?.sources || []
  const sourceIndexById = new Map<string, number>()
  sources.forEach((s, idx) => {
    sourceIndexById.set(s.id, idx + 1)
  })

  const traceEvidenceById = new Map<string, EvidenceAnchor>()
  for (const tr of run?.review_trace || []) {
    for (const ev of tr.evidence || []) {
      traceEvidenceById.set(ev.id, ev)
    }
  }

  const bodySupportedClaims = (run?.claim_reviews || []).filter(
    c =>
      c.support_status === 'supported' &&
      c.origin !== 'program_policy' &&
      c.text !== POLICY_NOTICE_TEXT,
  )

  let invalidClaimCount = 0
  let duplicateClaimCount = 0
  let overlapConflictCount = 0

  interface CandidateSpan {
    start: number
    end: number
    claim: ClaimReviewItem
    evidenceSignature: string
  }

  const validCandidates: CandidateSpan[] = []
  for (const c of bodySupportedClaims) {
    const resolved = resolveClaimUtf16Range(
      bodyText,
      codePointMap,
      c.final_start,
      c.final_end,
      c.text,
    )
    if (!resolved) {
      invalidClaimCount++
      continue
    }
    const evSig = `${c.kind}|${(c.evidence_ids || []).join(',')}|${(c.evidence || [])
      .map(e => `${e.document_id}:${e.start}:${e.end}`)
      .join(',')}`
    validCandidates.push({
      start: resolved.start,
      end: resolved.end,
      claim: c,
      evidenceSignature: evSig,
    })
  }

  // Step 1: Group by exact [start, end] to handle duplicates vs conflicting same-span claims
  const byExactSpan = new Map<string, CandidateSpan[]>()
  for (const cand of validCandidates) {
    const key = `${cand.start}:${cand.end}`
    const group = byExactSpan.get(key) || []
    group.push(cand)
    byExactSpan.set(key, group)
  }

  const dedupedCandidates: CandidateSpan[] = []
  for (const group of byExactSpan.values()) {
    if (group.length === 1) {
      dedupedCandidates.push(group[0]!)
    } else {
      const firstSig = group[0]!.evidenceSignature
      const allSame = group.every(g => g.evidenceSignature === firstSig)
      if (allSame) {
        dedupedCandidates.push(group[0]!)
        duplicateClaimCount += group.length - 1
      } else {
        // Conflicting claims bound to the exact same span: drop citation binding on this span
        overlapConflictCount += group.length
      }
    }
  }

  dedupedCandidates.sort((a, b) => a.start - b.start || a.end - b.end)

  // Step 2: Detect partial overlaps between distinct intervals; exclude any overlapping pair
  const conflictedIndices = new Set<number>()
  for (let i = 0; i < dedupedCandidates.length; i++) {
    const a = dedupedCandidates[i]!
    for (let j = i + 1; j < dedupedCandidates.length; j++) {
      const b = dedupedCandidates[j]!
      if (b.start >= a.end) break
      // Since b.start < a.end and intervals are distinct, they overlap
      conflictedIndices.add(i)
      conflictedIndices.add(j)
    }
  }
  overlapConflictCount += conflictedIndices.size

  const acceptedSpans = dedupedCandidates.filter((_, idx) => !conflictedIndices.has(idx))

  function toMappedClaim(span: CandidateSpan): MappedAnswerClaim {
    const claim = span.claim
    const anchors: EvidenceAnchor[] =
      claim.evidence && claim.evidence.length
        ? claim.evidence
        : (claim.evidence_ids || [])
            .map(id => traceEvidenceById.get(id))
            .filter((x): x is EvidenceAnchor => !!x)

    const srcNums = new Set<number>()
    for (const a of anchors) {
      const num = sourceIndexById.get(a.source_id)
      if (num) {
        srcNums.add(num)
      } else {
        sources.forEach((s, idx) => {
          if (
            s.document_id === a.document_id &&
            s.source_sha256 === a.source_sha256 &&
            (s.source_spans || []).some(sp => sp.start <= a.start && sp.end >= a.end)
          ) {
            srcNums.add(idx + 1)
          }
        })
      }
    }

    const isPolicyOrScope = claim.kind === 'project_behavior' || claim.kind === 'corpus_scope'
    const isMedicalFactWithEvidence = claim.kind === 'medical_fact' && anchors.length > 0

    return {
      kind: 'claim',
      text: bodyText.slice(span.start, span.end),
      start: span.start,
      end: span.end,
      claim,
      sourceNumbers: Array.from(srcNums).sort((a, b) => a - b),
      evidenceAnchors: anchors,
      isMedicalFactWithEvidence,
      isPolicyOrScope,
    }
  }

  // Step 3: Partition [0, bodyText.length) into contiguous segments and split into paragraphs on \n+
  const paragraphs: MappedAnswerClaim[][] = []
  let currentPara: MappedAnswerClaim[] = []

  function appendPlainTextRange(rangeStart: number, rangeEnd: number) {
    if (rangeEnd <= rangeStart) return
    const rawSlice = bodyText.slice(rangeStart, rangeEnd)
    const parts = rawSlice.split(/((?:\r?\n)+)/)
    let offset = rangeStart
    for (const part of parts) {
      if (!part) continue
      const partEnd = offset + part.length
      if (/^(?:\r?\n)+$/.test(part)) {
        if (currentPara.length > 0) {
          currentPara[currentPara.length - 1]!.separatorAfter = part
          paragraphs.push(currentPara)
          currentPara = []
        } else {
          currentPara.push(makeUnmappedTextSegment(part, offset, partEnd))
        }
      } else {
        currentPara.push(makeUnmappedTextSegment(part, offset, partEnd))
      }
      offset = partEnd
    }
  }

  let cursor = 0
  for (const span of acceptedSpans) {
    if (span.start > cursor) {
      appendPlainTextRange(cursor, span.start)
    }
    currentPara.push(toMappedClaim(span))
    cursor = span.end
  }
  if (cursor < bodyText.length) {
    appendPlainTextRange(cursor, bodyText.length)
  }
  if (currentPara.length > 0) {
    paragraphs.push(currentPara)
  }

  const mappedMedicalClaimCount = paragraphs
    .flat()
    .filter(seg => seg.kind === 'claim' && seg.isMedicalFactWithEvidence).length

  const hasUnmappedProseSegment = paragraphs
    .flat()
    .some(seg => seg.kind === 'text' && seg.text.trim().length > 0)

  const hasMappingAnomaly =
    invalidClaimCount > 0 ||
    overlapConflictCount > 0 ||
    (mappedMedicalClaimCount > 0 && hasUnmappedProseSegment)

  const hasReliableMapping = mappedMedicalClaimCount > 0

  let mappingStatus: AnswerSegmentationResult['mappingStatus'] = 'none'
  if (mappedMedicalClaimCount > 0) {
    mappingStatus = hasMappingAnomaly ? 'partial' : 'complete'
  } else if (sources.length > 0 || bodySupportedClaims.length > 0) {
    mappingStatus = 'fallback_plain'
  }

  return {
    hasReliableMapping,
    mappingStatus,
    hasMappingAnomaly,
    invalidClaimCount,
    duplicateClaimCount,
    overlapConflictCount,
    bodyText,
    omittedNotice: extracted.omittedNotice,
    policyNotice: extracted.policyNotice,
    isSystemFailurePlaceholder: false,
    paragraphs,
    omittedClaims,
  }
}
