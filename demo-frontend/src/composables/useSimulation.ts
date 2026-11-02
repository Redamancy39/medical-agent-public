import { computed, ref, nextTick } from 'vue'
import {
  MOCK_SCENARIOS,
  generateSimulatedTurn,
  type MockSessionScenario,
  type MockTurn,
} from '../mockMedicalScenarios'

export interface UseSimulationOptions {
  onSessionChange?: () => void
  onTurnCreated?: () => void
  showToast?: (msg: string) => void
  scrollBottom?: () => void
}

export function useSimulation(options: UseSimulationOptions = {}) {
  const simSessions = ref<MockSessionScenario[]>(
    JSON.parse(JSON.stringify(MOCK_SCENARIOS)) as MockSessionScenario[],
  )
  const simActiveSessionId = ref<string>(simSessions.value[0]?.id || 'sim-session-1')
  const simSelectedTurnId = ref<string>(simSessions.value[0]?.turns[0]?.id || '')
  const simInput = ref('')
  const simBusy = ref(false)

  const userSimSessions = computed(() => simSessions.value.filter(s => s.isUserCreated))
  const presetSimSessions = computed(() => simSessions.value.filter(s => !s.isUserCreated))

  const currentSimSession = computed(
    () => simSessions.value.find(s => s.id === simActiveSessionId.value) || null,
  )
  const currentSimTurn = computed(() => {
    const sess = currentSimSession.value
    if (!sess || !sess.turns.length) return null
    return (
      sess.turns.find(t => t.id === simSelectedTurnId.value) ||
      sess.turns[sess.turns.length - 1]
    )
  })

  function selectSimSession(id: string) {
    simActiveSessionId.value = id
    const sess = simSessions.value.find(s => s.id === id)
    simSelectedTurnId.value = sess?.turns[sess.turns.length - 1]?.id || ''
    options.onSessionChange?.()
    options.scrollBottom?.()
  }

  function createSimSession() {
    const customCount = userSimSessions.value.length + 1
    const newId = `sim-session-custom-${Date.now()}`
    const newSess: MockSessionScenario = {
      id: newId,
      title: `新建问答会话 #${customCount}`,
      categoryTag: '我的模拟提问',
      statusBadge: 'completed',
      statusText: '新会话',
      summaryText:
        '本地结构模拟会话：可选择下方示例问题或直接输入成人高血压、2 型糖尿病问题。',
      isUserCreated: true,
      turns: [],
      followUpSuggestions: [
        {
          label: '血压 120/80 代表什么及测前 30 分钟准备',
          question:
            '血压读数 120/80 mmHg 里的两个数字分别代表什么？测量血压前 30 分钟需要注意什么？',
        },
        {
          label: 'eGFR 与 UACR 两项肾脏检查有什么区别',
          question:
            '那么 eGFR（估算肾小球滤过率）和 UACR 有什么区别？可以互相替代吗？',
        },
        {
          label: '降压药一般作用机制与空腹验血能否停药',
          question:
            '请按 NLM 资料介绍一下利尿剂和钙通道阻滞剂帮助控制血压的一般机制，验血前能自己停药吗？',
        },
      ],
    }
    simSessions.value.unshift(newSess)
    simActiveSessionId.value = newId
    simSelectedTurnId.value = ''
    options.onSessionChange?.()
  }

  function resetSimSessions() {
    simSessions.value = JSON.parse(
      JSON.stringify(MOCK_SCENARIOS),
    ) as MockSessionScenario[]
    selectSimSession(simSessions.value[0]!.id)
    options.showToast?.('已恢复 5 个预设模拟演示场景')
  }

  function sendSimQuestion(customText?: string, presetTurn?: MockTurn) {
    const text = (customText ?? simInput.value).trim()
    if (!text || simBusy.value) return
    if (!currentSimSession.value) {
      createSimSession()
    }
    const sess = currentSimSession.value!
    simInput.value = ''
    simBusy.value = true

    setTimeout(() => {
      const turn: MockTurn = presetTurn
        ? (JSON.parse(JSON.stringify(presetTurn)) as MockTurn)
        : generateSimulatedTurn(text, sess.id, sess.turns.length + 1)

      sess.turns.push(turn)
      if (sess.turns.length === 1 && sess.isUserCreated) {
        sess.title = text.slice(0, 20) + (text.length > 20 ? '…' : '')
      }
      const rStatus = turn.run.result_status || turn.run.run_status
      sess.statusBadge =
        rStatus === 'completed'
          ? turn.run.sources.length
            ? 'completed'
            : 'no_source'
          : rStatus === 'failed'
            ? 'failed'
            : 'partial'
      sess.statusText =
        rStatus === 'completed'
          ? '已完成'
          : rStatus === 'failed'
            ? '服务暂不可用'
            : '部分完成'

      simSelectedTurnId.value = turn.id
      simBusy.value = false
      options.onTurnCreated?.()
      options.scrollBottom?.()
    }, 320)
  }

  return {
    simSessions,
    simActiveSessionId,
    simSelectedTurnId,
    simInput,
    simBusy,
    userSimSessions,
    presetSimSessions,
    currentSimSession,
    currentSimTurn,
    selectSimSession,
    createSimSession,
    resetSimSessions,
    sendSimQuestion,
  }
}
