import { computed, ref, nextTick } from 'vue'
import type {
  ExecutionEventItem,
  HealthStatus,
  MaintenanceJobItem,
  MemoryFactItem,
  MessageItem,
  ProviderCallItem,
  RunOut,
  SessionItem,
  SessionSummaryItem,
} from '../types'

export interface UseBackendOptions {
  showToast?: (msg: string) => void
  scrollBottom?: () => void
  onResetSelection?: () => void
  onSessionChange?: () => void
}

export function useBackend(options: UseBackendOptions = {}) {
  const backendHealth = ref<HealthStatus | null>(null)
  const backendHealthError = ref('')
  const token = ref('')
  const username = ref('')
  const password = ref('')
  const signedIn = ref('')
  const backendError = ref('')
  const backendBusy = ref(false)
  const backendChatPending = ref(false)
  const backendProgressStale = ref(false)

  const sessions = ref<SessionItem[]>([])
  const sessionId = ref('')
  const messages = ref<MessageItem[]>([])
  const moreHistory = ref(false)
  const sessionRuns = ref<RunOut[]>([])
  const selectedBackendRunId = ref('')
  const backendEvents = ref<ExecutionEventItem[]>([])
  const backendProviderCalls = ref<ProviderCallItem[]>([])
  const backendSummary = ref<SessionSummaryItem | null>(null)

  const backendQuestion = ref('')
  const clarificationInput = ref('')
  const pendingRequest = ref<{ question: string; request_id: string } | null>(null)

  const pendingBackendRun = computed(() =>
    sessionRuns.value.find(
      r =>
        r.request_id === pendingRequest.value?.request_id &&
        r.session_id === sessionId.value,
    ) || null,
  )

  const facts = ref<MemoryFactItem[]>([])
  const factDrafts = ref<Record<string, string>>({})
  const maintenanceJobs = ref<MaintenanceJobItem[]>([])

  let statusEpoch = 0
  let runSelectEpoch = 0
  const runAuditCache = ref<Record<string, { events: ExecutionEventItem[]; calls: ProviderCallItem[] }>>({})
  let pollingTimer: ReturnType<typeof setInterval> | undefined
  let pollingInFlight = false

  async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
    const requestToken = token.value
    let response: Response
    try {
      response = await fetch(`/api${path}`, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...(token.value ? { Authorization: `Bearer ${token.value}` } : {}),
        },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      })
    } catch {
      throw new Error(
        '无法连接本地 8010 后端服务。请确认已在 backend 目录启动服务，或切换至“本地模拟演示”模式。',
      )
    }
    const data = await response.json().catch(() => ({}))
    if (requestToken !== token.value) {
      throw new Error('登录状态已变更，请重新操作。')
    }
    if (!response.ok) {
      if (response.status === 401 && token.value) {
        logoutBackend()
        backendError.value =
          'JWT 登录凭证已过期或失效，请重新登录以读取本人 SQL 会话与历史记录。'
      }
      throw new Error(
        data.error?.message || `后端请求未成功 (HTTP ${response.status})`,
      )
    }
    return data as T
  }

  async function checkBackendHealth() {
    try {
      backendHealth.value = await api<HealthStatus>('/health')
      backendHealthError.value = ''
    } catch (e) {
      backendHealth.value = null
      backendHealthError.value = (e as Error).message
    }
  }

  async function runBackendAction(work: () => Promise<void>) {
    backendError.value = ''
    backendBusy.value = true
    try {
      await work()
    } catch (e) {
      backendError.value = (e as Error).message
    } finally {
      backendBusy.value = false
    }
  }

  async function performAuth(uname: string, pwd: string, register = false) {
    const body = { username: uname.trim(), password: pwd }
    if (register) {
      await api('/auth/register', 'POST', body)
    }
    const res = await api<{ access_token: string }>('/auth/login', 'POST', body)
    token.value = res.access_token
    password.value = ''
    const me = await api<{ username: string }>('/auth/me')
    signedIn.value = me.username
    const sessList = await api<{ items: SessionItem[] }>('/sessions')
    sessions.value = sessList.items
    await loadMaintenanceState()
    if (sessions.value.length > 0) {
      sessionId.value = sessions.value[0]!.id
      await loadBackendSessionData()
    } else {
      options.onResetSelection?.()
    }
    options.showToast?.(`已登录账号：${signedIn.value}`)
  }

  async function authenticateBackend(register = false) {
    await runBackendAction(async () => {
      await performAuth(username.value, password.value, register)
    })
  }

  async function quickLoginResearcher() {
    backendError.value = ''
    backendBusy.value = true
    // 使用随机后缀生成独立研究员账号，避免多人共用同一账号导致会话与记忆交叉
    const suffix = Math.random().toString(36).slice(2, 8)
    const uname = `researcher_${suffix}`
    const pwd = `MedRes_${suffix}_${Date.now()}`
    username.value = uname
    try {
      // 首次使用：直接注册并登录
      await performAuth(uname, pwd, true)
    } catch {
      try {
        // 如果注册失败（极小概率用户名冲突），尝试纯登录
        await performAuth(uname, pwd, false)
      } catch (err) {
        backendError.value = (err as Error).message
      }
    } finally {
      backendBusy.value = false
    }
  }

  function logoutBackend() {
    statusEpoch++
    clearInterval(pollingTimer)
    token.value = ''
    signedIn.value = ''
    sessionId.value = ''
    sessions.value = []
    messages.value = []
    sessionRuns.value = []
    selectedBackendRunId.value = ''
    backendEvents.value = []
    backendProviderCalls.value = []
    backendSummary.value = null
    pendingRequest.value = null
    backendChatPending.value = false
    backendProgressStale.value = false
    facts.value = []
    factDrafts.value = {}
    maintenanceJobs.value = []
    options.onResetSelection?.()
  }

  async function loadMaintenanceState() {
    await checkBackendHealth()
    if (!token.value) return
    facts.value = (await api<{ items: MemoryFactItem[] }>('/memories')).items
    for (const f of facts.value) {
      if (!(f.id in factDrafts.value)) factDrafts.value[f.id] = f.content
    }
    maintenanceJobs.value = (
      await api<{ items: MaintenanceJobItem[] }>('/maintenance/jobs')
    ).items
    if (sessionId.value) {
      const reqSession = sessionId.value
      const s = await api<SessionSummaryItem>(`/sessions/${reqSession}/summary`)
      if (reqSession === sessionId.value) backendSummary.value = s
    } else {
      backendSummary.value = null
    }
  }

  async function loadBackendHistory(append = false) {
    if (!sessionId.value) return
    const after = append ? messages.value.at(-1)?.seq || 0 : 0
    const data = await api<{ items: MessageItem[]; has_more: boolean }>(
      `/sessions/${sessionId.value}/messages?limit=100&after_seq=${after}`,
    )
    messages.value = append ? [...messages.value, ...data.items] : data.items
    moreHistory.value = data.has_more
  }

  async function refreshBackendStatus(light = false) {
    if (!sessionId.value) {
      await loadMaintenanceState()
      return
    }
    const epoch = ++statusEpoch
    const reqSession = sessionId.value
    const waitingForFirstRecord =
      backendChatPending.value && !pendingBackendRun.value
    const runs = await api<RunOut[]>(
      `/sessions/${reqSession}/runs?limit=${light ? 1 : 30}`,
    )
    if (epoch !== statusEpoch || reqSession !== sessionId.value) return
    sessionRuns.value = light
      ? [
          ...runs,
          ...sessionRuns.value.filter(old => !runs.some(r => r.run_id === old.run_id)),
        ]
      : runs

    const targetRun =
      runs.find(r => r.request_id === pendingRequest.value?.request_id) ||
      runs.find(r => r.run_id === selectedBackendRunId.value) ||
      runs[0] ||
      null

    if (light && targetRun?.request_id !== pendingRequest.value?.request_id) return
    if (light && waitingForFirstRecord && pendingBackendRun.value)
      options.scrollBottom?.()

    if (targetRun) {
      if (selectedBackendRunId.value !== targetRun.run_id) {
        options.onResetSelection?.()
      }
      selectedBackendRunId.value = targetRun.run_id
      const [evRes, callRes] = await Promise.all([
        api<{ items: ExecutionEventItem[] }>(`/runs/${targetRun.run_id}/events`).catch(() => ({ items: [] })),
        light
          ? Promise.resolve(null)
          : api<{ items: ProviderCallItem[] }>(
              `/runs/${targetRun.run_id}/providers`,
            ).catch(() => ({ items: [] })),
      ])
      if (epoch !== statusEpoch || reqSession !== sessionId.value || selectedBackendRunId.value !== targetRun.run_id) return
      backendEvents.value = evRes.items
      if (callRes) backendProviderCalls.value = callRes.items
      runAuditCache.value[targetRun.run_id] = {
        events: evRes.items,
        calls: callRes ? callRes.items : (runAuditCache.value[targetRun.run_id]?.calls || []),
      }
    } else {
      selectedBackendRunId.value = ''
      options.onResetSelection?.()
      backendEvents.value = []
      backendProviderCalls.value = []
    }
    if (!light) await loadMaintenanceState()
  }

  async function fetchRunAudit(runId: string): Promise<{ events: ExecutionEventItem[]; calls: ProviderCallItem[] }> {
    if (!runId) return { events: [], calls: [] }
    if (runAuditCache.value[runId]) {
      return runAuditCache.value[runId]!
    }
    const [evRes, callRes] = await Promise.all([
      api<{ items: ExecutionEventItem[] }>(`/runs/${runId}/events`).catch(() => ({ items: [] })),
      api<{ items: ProviderCallItem[] }>(`/runs/${runId}/providers`).catch(() => ({ items: [] })),
    ])
    const data = { events: evRes.items, calls: callRes.items }
    runAuditCache.value[runId] = data
    return data
  }

  async function selectBackendRun(runId: string) {
    if (!runId) {
      selectedBackendRunId.value = ''
      backendEvents.value = []
      backendProviderCalls.value = []
      options.onResetSelection?.()
      return
    }
    const currentEpoch = ++runSelectEpoch
    selectedBackendRunId.value = runId
    options.onResetSelection?.()

    // Immediately reflect cached records if available
    if (runAuditCache.value[runId]) {
      backendEvents.value = runAuditCache.value[runId]!.events
      backendProviderCalls.value = runAuditCache.value[runId]!.calls
    }

    try {
      const [evRes, callRes] = await Promise.all([
        api<{ items: ExecutionEventItem[] }>(`/runs/${runId}/events`).catch(() => ({ items: [] })),
        api<{ items: ProviderCallItem[] }>(`/runs/${runId}/providers`).catch(() => ({ items: [] })),
      ])
      // Drop late responses if user has switched runs or new selection happened
      if (currentEpoch !== runSelectEpoch || selectedBackendRunId.value !== runId) return
      backendEvents.value = evRes.items
      backendProviderCalls.value = callRes.items
      runAuditCache.value[runId] = { events: evRes.items, calls: callRes.items }
    } catch {
      /* ignore */
    }
  }

  async function loadBackendSessionData() {
    statusEpoch++
    pendingRequest.value = null
    clarificationInput.value = ''
    options.onResetSelection?.()
    if (!sessionId.value) {
      messages.value = []
      sessionRuns.value = []
      selectedBackendRunId.value = ''
      backendEvents.value = []
      backendProviderCalls.value = []
      backendSummary.value = null
      return
    }
    await loadBackendHistory(false)
    await refreshBackendStatus()
    options.scrollBottom?.()
  }

  async function chooseBackendSession(id: string) {
    sessionId.value = id
    options.onSessionChange?.()
    await runBackendAction(loadBackendSessionData)
  }

  async function createBackendSession() {
    await runBackendAction(async () => {
      const title = `医学问答会话 ${sessions.value.length + 1}`
      const created = await api<SessionItem>('/sessions', 'POST', { title })
      sessions.value = (await api<{ items: SessionItem[] }>('/sessions')).items
      sessionId.value = created.id
      options.onSessionChange?.()
      await loadBackendSessionData()
    })
  }

  async function sendBackendQuestion(retryQuestionText?: string) {
    const text = (retryQuestionText ?? backendQuestion.value).trim()
    if (!text || !sessionId.value || backendBusy.value || backendChatPending.value)
      return
    if (retryQuestionText) {
      backendQuestion.value = retryQuestionText
    }
    if (!pendingRequest.value || pendingRequest.value.question !== text) {
      pendingRequest.value = { question: text, request_id: crypto.randomUUID() }
    }
    const submitted = { ...pendingRequest.value }
    const reqSession = sessionId.value
    backendChatPending.value = true
    backendProgressStale.value = false
    options.scrollBottom?.()
    await runBackendAction(async () => {
      pollingTimer = setInterval(async () => {
        if (pollingInFlight || reqSession !== sessionId.value || !token.value)
          return
        pollingInFlight = true
        try {
          await refreshBackendStatus(true)
          backendProgressStale.value = false
        } catch {
          backendProgressStale.value = true
        } finally {
          pollingInFlight = false
        }
      }, 1000)
      try {
        const latestRun = await api<RunOut>(
          `/sessions/${reqSession}/chat`,
          'POST',
          submitted,
        )
        if (reqSession !== sessionId.value) return
        selectedBackendRunId.value = latestRun.run_id
        backendQuestion.value = ''
        pendingRequest.value = null
        options.onResetSelection?.()
        await loadBackendHistory(false)
        await refreshBackendStatus()
        options.scrollBottom?.()
      } finally {
        clearInterval(pollingTimer)
        backendChatPending.value = false
      }
    })
  }

  async function resumeBackendRun() {
    const activeRun = currentBackendRun.value
    if (!activeRun?.checkpoint_id) return
    await runBackendAction(async () => {
      const resumed = await api<RunOut>(`/runs/${activeRun.run_id}/resume`, 'POST', {
        checkpoint_id: activeRun.checkpoint_id,
        ...(clarificationInput.value.trim()
          ? { clarification: clarificationInput.value.trim() }
          : {}),
      })
      selectedBackendRunId.value = resumed.run_id
      clarificationInput.value = ''
      await loadBackendHistory(false)
      await refreshBackendStatus()
    })
  }

  async function cancelBackendRun() {
    const activeRun = currentBackendRun.value
    if (!activeRun) return
    try {
      await api<RunOut>(`/runs/${activeRun.run_id}/cancel`, 'POST')
      if (!backendBusy.value) {
        await loadBackendHistory(false)
        await refreshBackendStatus()
      }
    } catch (e) {
      backendError.value = (e as Error).message
    }
  }

  async function editMemoryFact(
    fact: MemoryFactItem,
    operation: 'update' | 'delete',
  ) {
    await runBackendAction(async () => {
      await api(`/memories/${fact.id}`, 'POST', {
        operation,
        ...(operation === 'update' ? { content: factDrafts.value[fact.id] } : {}),
      })
      await loadMaintenanceState()
      options.showToast?.(
        operation === 'delete' ? '已撤回该条长期记忆' : '已更新长期记忆',
      )
    })
  }

  async function retryMaintenanceJobs() {
    await runBackendAction(async () => {
      await api('/maintenance/retry', 'POST', {})
      await refreshBackendStatus()
      options.showToast?.('已触发后台维护任务有界重试')
    })
  }

  const backendTurns = computed(() => {
    const runMap = new Map<string, RunOut>()
    for (const r of sessionRuns.value) {
      runMap.set(r.run_id, r)
    }

    const grouped = new Map<
      string,
      {
        id: string
        runId: string
        question: string
        answer: string | null
        createdAt: string
        run: RunOut | null
      }
    >()

    for (const m of messages.value) {
      const rId = m.run_id || m.id
      if (!grouped.has(rId)) {
        grouped.set(rId, {
          id: rId,
          runId: rId,
          question: '',
          answer: null,
          createdAt: m.created_at
            ? new Date(m.created_at).toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit',
                hour12: false,
              })
            : '',
          run: runMap.get(rId) || null,
        })
      }
      const entry = grouped.get(rId)!
      if (m.role === 'user') {
        entry.question = entry.question
          ? `${entry.question}\n${m.content}`
          : m.content
      } else {
        entry.answer = m.content
      }
    }

    for (const r of sessionRuns.value) {
      if (!grouped.has(r.run_id)) {
        grouped.set(r.run_id, {
          id: r.run_id,
          runId: r.run_id,
          question:
            pendingRequest.value?.request_id === r.request_id
              ? pendingRequest.value.question
              : '（未完成运行记录）',
          answer: r.answer,
          createdAt: '',
          run: r,
        })
      }
    }

    return Array.from(grouped.values())
  })

  const currentBackendRun = computed(() => {
    if (!sessionRuns.value.length) return null
    return (
      sessionRuns.value.find(r => r.run_id === selectedBackendRunId.value) ||
      sessionRuns.value[0] ||
      null
    )
  })

  return {
    backendHealth,
    backendHealthError,
    token,
    username,
    password,
    signedIn,
    backendError,
    backendBusy,
    backendChatPending,
    backendProgressStale,
    sessions,
    sessionId,
    messages,
    moreHistory,
    sessionRuns,
    selectedBackendRunId,
    backendEvents,
    backendProviderCalls,
    backendSummary,
    backendQuestion,
    clarificationInput,
    pendingRequest,
    pendingBackendRun,
    currentBackendRun,
    backendTurns,
    facts,
    factDrafts,
    maintenanceJobs,
    api,
    checkBackendHealth,
    runBackendAction,
    authenticateBackend,
    quickLoginResearcher,
    logoutBackend,
    loadMaintenanceState,
    loadBackendHistory,
    refreshBackendStatus,
    selectBackendRun,
    loadBackendSessionData,
    chooseBackendSession,
    createBackendSession,
    sendBackendQuestion,
    resumeBackendRun,
    cancelBackendRun,
    editMemoryFact,
    retryMaintenanceJobs,
    runAuditCache,
    fetchRunAudit,
  }
}
