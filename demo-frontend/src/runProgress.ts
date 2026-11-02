import type { ExecutionEventItem, RunOut } from './types.ts'

const PHASES = [
  { id: 'understand', label: '理解问题' },
  { id: 'answer', label: '查询与作答' },
  { id: 'review', label: '核对引用' },
  { id: 'save', label: '保存结果' },
] as const

type Phase = typeof PHASES[number]['id']
const STAGE_PHASE: Record<string, Phase> = {
  safety_gate: 'understand', load_context: 'understand', route: 'understand',
  plan: 'understand', clarify: 'understand',
  worker: 'answer', tools: 'answer', validate_output: 'answer', dispatch: 'answer',
  task_worker: 'answer', task_tools: 'answer', task_validate: 'answer',
  task_result: 'answer', check_evidence: 'answer', synthesize: 'answer',
  review_answer: 'review', persist_result: 'save',
}

// Node stages are saved AFTER execution. They are checkpoints, not live start events.
// Never advance by wall-clock time or turn these steps into a percentage.
export function describeRunProgress(run: RunOut | null, events: ExecutionEventItem[] = []) {
  const observed = new Set(events.map(e => STAGE_PHASE[e.stage]).filter(Boolean))
  const stagePhase = run?.stage ? STAGE_PHASE[run.stage] : undefined
  if (stagePhase) observed.add(stagePhase)
  const reviewing = run?.reviewer_status === 'running' || run?.atomization_status === 'running'
    || ['running', 'awaiting_review'].includes(run?.review_rewrite_status || '')
  const terminal = run && !['running', 'awaiting_input', 'paused'].includes(run.run_status)
  const phase: Phase | undefined = reviewing && !terminal ? 'review' : stagePhase
  const urgent = run?.response_origin === 'urgent_policy'
  const paused = run?.run_status === 'paused' || run?.run_status === 'awaiting_input'
  const failed = ['failed', 'cancelled', 'timed_out'].includes(run?.result_status || run?.run_status || '')
  return {
    title: paused ? '等待你的补充' : terminal ? (failed ? '本轮处理已停止' : '本轮处理已结束') : '正在处理你的问题',
    detail: !run ? '正在提交，等待后端返回进度。'
      : paused ? '补充说明后可以继续，也可以取消本轮。'
      : urgent ? '已触发安全规则，常规检索和模型核对已跳过。'
      : reviewing && !terminal ? (run.review_rewrite_status === 'running' || run.review_rewrite_status === 'awaiting_review'
          ? '正在精简或修复原稿，并核对改写后的引用。' : '正在逐句核对回答与原文依据。')
      : phase ? `后端最近记录：${PHASES.find(p => p.id === phase)!.label}。`
      : '已收到运行记录，等待下一条进度。',
    active: Boolean(!terminal && !paused),
    steps: PHASES.map(p => ({ ...p, state: urgent && (p.id === 'answer' || p.id === 'review') ? 'skipped'
      : p.id === phase ? 'current' : observed.has(p.id) ? 'recorded' : 'waiting' })),
  }
}
