<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  Activity,
  AlertTriangle,
  ArrowUp,
  BookOpen,
  CheckCircle2,
  Database,
  FileText,
  GitBranch,
  KeyRound,
  LogOut,
  Menu,
  MessageSquarePlus,
  PanelRightOpen,
  RefreshCw,
  RotateCcw,
  Server,
  Sparkles,
  UserCheck,
  X,
} from 'lucide-vue-next'
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
  SourceItem,
} from './types'
import {
  formatLabel,
  formatStage,
  formatAgentRole,
  formatCallCount,
  describeSafeError,
  type MappedAnswerClaim,
} from './medicalLabels'
import { focusInitialElement, trapFocusOnTab } from './focusTrap'
import ConversationTurnCard from './ConversationTurnCard.vue'
import EvidenceAndTracePanel from './EvidenceAndTracePanel.vue'
import RunProgress from './RunProgress.vue'
import CitationPopover from './CitationPopover.vue'
import ExportDossierModal from './ExportDossierModal.vue'
import KnowledgeCatalogModal from './KnowledgeCatalogModal.vue'

// Modular Composables (Extracted in Scheme B & Phase 3)
import { useBackend } from './composables/useBackend'
import { useInspector } from './composables/useInspector'

// ============================================================================
// 1. TOP-LEVEL LAYOUT & MODAL STATE
// ============================================================================
const memoryModalOpen = ref(false)
const exportModalOpen = ref(false)
const catalogModalOpen = ref(false)
const mobileSidebarOpen = ref(false)
const isNarrowViewport = ref(typeof window !== 'undefined' ? window.innerWidth <= 1100 : false)
const isMobileViewport = ref(typeof window !== 'undefined' ? window.innerWidth <= 820 : false)

const chatScrollRef = ref<HTMLElement | null>(null)
const composerRef = ref<HTMLTextAreaElement | null>(null)
const sidebarRef = ref<HTMLElement | null>(null)
const inspectorColRef = ref<HTMLElement | null>(null)
const memoryModalRef = ref<HTMLElement | null>(null)
const mobileMenuBtnRef = ref<HTMLButtonElement | null>(null)
const evidencePanelRef = ref<InstanceType<typeof EvidenceAndTracePanel> | null>(null)

const focusTriggerStack: HTMLElement[] = []
const lastFocusTrigger = ref<HTMLElement | null>(null)

function saveTrigger(el?: EventTarget | HTMLElement | null) {
  const candidate =
    el instanceof HTMLElement
      ? el
      : typeof document !== 'undefined' && document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null
  if (candidate && candidate !== document.body) {
    lastFocusTrigger.value = candidate
    if (focusTriggerStack[focusTriggerStack.length - 1] !== candidate) {
      focusTriggerStack.push(candidate)
    }
  }
}

async function restoreTriggerFocus(fallbackEl?: HTMLElement | null) {
  const popped = focusTriggerStack.pop() || lastFocusTrigger.value || fallbackEl || null
  await nextTick()
  if (popped && typeof document !== 'undefined' && document.contains(popped)) {
    popped.focus()
  }
}

const isLeftDrawerModal = computed(() => isMobileViewport.value && mobileSidebarOpen.value)
const isRightDrawerModal = computed(
  () => isNarrowViewport.value && inspector.mobileInspectorOpen.value,
)
const anyModalOpen = computed(
  () =>
    catalogModalOpen.value ||
    exportModalOpen.value ||
    memoryModalOpen.value ||
    isRightDrawerModal.value ||
    isLeftDrawerModal.value,
)

const toastText = ref('')
let toastTimer: ReturnType<typeof setTimeout> | undefined

function showToast(msg: string) {
  toastText.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toastText.value = ''
  }, 4000)
}

function openCatalogModal(event?: MouseEvent) {
  if (event?.currentTarget instanceof HTMLElement) {
    saveTrigger(event.currentTarget)
  } else {
    saveTrigger()
  }
  catalogModalOpen.value = true
}

function closeCatalogModal() {
  catalogModalOpen.value = false
  restoreTriggerFocus()
}

function closeExportModal() {
  exportModalOpen.value = false
}

async function scrollConversationBottom() {
  await nextTick()
  chatScrollRef.value?.scrollTo({
    top: chatScrollRef.value.scrollHeight,
    behavior: 'smooth',
  })
}

function updateViewportFlag() {
  if (typeof window === 'undefined') return
  const width = window.innerWidth
  const nextNarrow = width <= 1100
  const nextMobile = width <= 820

  if (!nextMobile && mobileSidebarOpen.value) {
    mobileSidebarOpen.value = false
  }
  if (!nextNarrow && inspector.mobileInspectorOpen.value) {
    inspector.mobileInspectorOpen.value = false
    inspector.desktopInspectorOpen.value = true
  }

  isNarrowViewport.value = nextNarrow
  isMobileViewport.value = nextMobile
}

watch(anyModalOpen, val => {
  if (val) {
    inspector.closePopover()
  }
  if (typeof document !== 'undefined') {
    document.body.style.overflow = val ? 'hidden' : ''
  }
})

// ============================================================================
// 2. MODULAR COMPOSABLES INSTANTIATION
// ============================================================================

// Inspector Composable
const inspector = useInspector({
  saveTrigger,
  restoreTriggerFocus,
  onClaimFocused: () => {
    void evidencePanelRef.value?.focusSelectedClaimBox()
  },
  onOmittedSectionFocused: () => {
    void evidencePanelRef.value?.focusOmittedSection()
  },
})

const {
  rightInspectorTab,
  highlightedSourceId,
  selectedClaim,
  claimFilter,
  desktopInspectorOpen,
  mobileInspectorOpen,
  popoverClaim,
  popoverAnchorEl,
  popoverOpen,
  closePopover,
  handleFocusSourceCard,
} = inspector

// Backend Composable (Production Real Agent Flow)
const backend = useBackend({
  showToast,
  scrollBottom: scrollConversationBottom,
  onResetSelection: () => {
    inspector.resetSelection()
    inspector.desktopInspectorOpen.value = false
  },
  onSessionChange: () => {
    mobileSidebarOpen.value = false
    void restoreTriggerFocus(mobileMenuBtnRef.value)
  },
})

const {
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
} = backend

const BACKEND_QUESTION_EXAMPLES = [
  {
    label: '儿科临床规范：儿童发热退热药指征与用药禁忌',
    text: '儿童发热达到多少度需要使用退热药？对乙酰氨基酚和布洛芬的剂量是多少？为什么严禁使用阿司匹林？',
  },
  {
    label: '消化基层指南：幽门螺杆菌呼气试验与铋剂四联',
    text: '做13C/14C呼气试验前需要停用哪些药物？中国指南推荐的铋剂四联根除方案疗程为什么是14天？',
  },
  {
    label: '急诊急救规范：急性脑卒中 BE FAST 与溶栓窗口',
    text: '急性脑卒中的 BE FAST 早期识别口诀是什么？静脉溶栓的黄金时间窗是多久？院前为什么严禁盲目给药？',
  },
  {
    label: '妇产临床标准：妊娠期糖尿病 75g OGTT 诊断切点',
    text: '孕期75g口服葡萄糖耐量试验在孕多少周进行？空腹及餐后血糖的中国诊断切点分别是多少？',
  },
]

// Active turn for dossier report export
const activeTurnForExport = computed(() => {
  if (selectedBackendRunId.value) {
    const found = backendTurns.value.find(t => t.runId === selectedBackendRunId.value)
    if (found) return found
  }
  return backendTurns.value.at(-1) || null
})

const activeEventsForExport = computed(() => {
  const rId = activeTurnForExport.value?.runId || activeTurnForExport.value?.run?.run_id
  if (rId && runAuditCache.value[rId]?.events?.length) {
    return runAuditCache.value[rId]!.events
  }
  return backendEvents.value
})

const activeCallsForExport = computed(() => {
  const rId = activeTurnForExport.value?.runId || activeTurnForExport.value?.run?.run_id
  if (rId && runAuditCache.value[rId]?.calls?.length) {
    return runAuditCache.value[rId]!.calls
  }
  return backendProviderCalls.value
})

async function openExportModal() {
  const rId = activeTurnForExport.value?.runId || activeTurnForExport.value?.run?.run_id
  if (rId) {
    await fetchRunAudit(rId)
  }
  exportModalOpen.value = true
}

// ============================================================================
// 3. INSPECTOR BRIDGE & MODAL ACTIONS
// ============================================================================
const activeInspectorRun = computed<RunOut | null>(() => currentBackendRun.value)
const activeInspectorEvents = computed<ExecutionEventItem[]>(() => backendEvents.value)
const activeInspectorCalls = computed<ProviderCallItem[]>(() => backendProviderCalls.value)
const activeInspectorSummary = computed<SessionSummaryItem | null>(() => backendSummary.value)

const isRightPanelVisible = computed(() => {
  if (isNarrowViewport.value) {
    return inspector.mobileInspectorOpen.value
  }
  return inspector.desktopInspectorOpen.value && Boolean(activeInspectorRun.value)
})

async function openRightPanel(triggerEl?: HTMLElement | null, customFocusHandled = false) {
  saveTrigger(triggerEl)
  inspector.desktopInspectorOpen.value = true
  if (isNarrowViewport.value) {
    mobileSidebarOpen.value = false
    inspector.mobileInspectorOpen.value = true
    if (!customFocusHandled) {
      await nextTick()
      focusInitialElement(inspectorColRef.value, '.panel-collapse-btn')
    }
  }
}

function closeRightPanel() {
  if (isNarrowViewport.value) {
    inspector.mobileInspectorOpen.value = false
  } else {
    inspector.desktopInspectorOpen.value = false
  }
  void restoreTriggerFocus()
}

function toggleRightPanel(event: MouseEvent) {
  if (isRightPanelVisible.value) {
    closeRightPanel()
  } else {
    void openRightPanel(event.currentTarget as HTMLElement, false)
  }
}

async function openMobileSidebar(triggerEl?: HTMLElement | null) {
  saveTrigger(triggerEl || mobileMenuBtnRef.value)
  inspector.mobileInspectorOpen.value = false
  mobileSidebarOpen.value = true
  await nextTick()
  focusInitialElement(sidebarRef.value)
}

function closeMobileSidebar() {
  mobileSidebarOpen.value = false
  void restoreTriggerFocus(mobileMenuBtnRef.value)
}

function toggleMobileSidebar(event: MouseEvent) {
  if (mobileSidebarOpen.value) {
    closeMobileSidebar()
  } else {
    void openMobileSidebar(event.currentTarget as HTMLElement)
  }
}

async function openMemoryModal(event: MouseEvent) {
  saveTrigger(event.currentTarget as HTMLElement)
  mobileSidebarOpen.value = false
  inspector.mobileInspectorOpen.value = false
  memoryModalOpen.value = true
  await nextTick()
  focusInitialElement(memoryModalRef.value, '.drawer-close-btn')
}

function closeMemoryModal() {
  memoryModalOpen.value = false
  void restoreTriggerFocus()
}

function closeActiveBackdrop() {
  if (isRightDrawerModal.value) {
    closeRightPanel()
  } else if (isLeftDrawerModal.value) {
    closeMobileSidebar()
  }
}

function handleSelectClaim(
  seg: MappedAnswerClaim,
  turnOrRunId: string,
  triggerEl: HTMLElement | null,
) {
  void selectBackendRun(turnOrRunId)
  inspector.handleSelectClaim(
    seg,
    triggerEl,
    isRightPanelVisible.value,
    isNarrowViewport.value,
  )
}

function handleOpenFullInspectorFromPopover(claim: MappedAnswerClaim) {
  inspector.handleOpenFullInspectorFromPopover(claim, isNarrowViewport.value)
}

function handleInspectSource(
  source: SourceItem,
  turnOrRunId: string,
  triggerEl: HTMLElement | null,
) {
  void selectBackendRun(turnOrRunId)
  inspector.handleInspectSource(source, triggerEl, isNarrowViewport.value)
}

function handleInspectOmittedClaims(
  turnOrRunId: string,
  triggerEl: HTMLElement | null,
) {
  void selectBackendRun(turnOrRunId)
  inspector.handleInspectOmittedClaims(triggerEl, isNarrowViewport.value)
}

function handleOpenTraceView(
  section: 'overview' | 'omitted' | 'dag',
  turnOrRunId: string,
  triggerEl: HTMLElement | null,
) {
  void selectBackendRun(turnOrRunId)
  inspector.handleOpenTraceView(section, triggerEl, isNarrowViewport.value)
}

function getActiveModalContainer(): HTMLElement | null {
  if (catalogModalOpen.value) return document.querySelector<HTMLElement>('.catalog-modal-panel')
  if (exportModalOpen.value) return document.querySelector<HTMLElement>('.dossier-modal-panel')
  if (memoryModalOpen.value) return memoryModalRef.value
  if (isRightDrawerModal.value) return inspectorColRef.value
  if (isLeftDrawerModal.value) return sidebarRef.value
  return null
}

function handleGlobalKeydown(event: KeyboardEvent) {
  if (event.key === 'Tab') {
    const modalContainer = getActiveModalContainer()
    if (modalContainer) {
      trapFocusOnTab(event, modalContainer)
    }
    return
  }

  if (event.key !== 'Escape') return

  if (catalogModalOpen.value) {
    event.preventDefault()
    event.stopPropagation()
    closeCatalogModal()
    return
  }
  if (exportModalOpen.value) {
    event.preventDefault()
    event.stopPropagation()
    closeExportModal()
    return
  }
  if (memoryModalOpen.value) {
    event.preventDefault()
    event.stopPropagation()
    closeMemoryModal()
    return
  }
  if (isRightDrawerModal.value) {
    event.preventDefault()
    event.stopPropagation()
    closeRightPanel()
    return
  }
  if (isLeftDrawerModal.value) {
    event.preventDefault()
    event.stopPropagation()
    closeMobileSidebar()
    return
  }
  if (selectedClaim.value) {
    event.preventDefault()
    selectedClaim.value = null
    void restoreTriggerFocus()
  }
}

function handleGlobalFocusIn(event: FocusEvent) {
  const modalContainer = getActiveModalContainer()
  if (
    modalContainer &&
    event.target instanceof HTMLElement &&
    !modalContainer.contains(event.target)
  ) {
    focusInitialElement(modalContainer)
  }
}

let healthCheckTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  updateViewportFlag()
  window.addEventListener('resize', updateViewportFlag)
  window.addEventListener('keydown', handleGlobalKeydown, true)
  document.addEventListener('focusin', handleGlobalFocusIn)
  void checkBackendHealth()
  healthCheckTimer = setInterval(() => {
    void checkBackendHealth()
  }, 3000)
})

onUnmounted(() => {
  if (healthCheckTimer) {
    clearInterval(healthCheckTimer)
    healthCheckTimer = null
  }
  window.removeEventListener('resize', updateViewportFlag)
  window.removeEventListener('keydown', handleGlobalKeydown, true)
  document.removeEventListener('focusin', handleGlobalFocusIn)
  if (typeof document !== 'undefined') {
    document.body.style.overflow = ''
  }
  clearTimeout(toastTimer)
})
</script>

<template>
  <div class="med-app-root">
    <!-- ======================================================================
         TOP GLOBAL BAR: Enterprise Brand, Status Cluster, Secondary Actions
         ====================================================================== -->
    <header
      class="med-topbar"
      :inert="anyModalOpen ? true : undefined"
      :aria-hidden="anyModalOpen ? 'true' : undefined"
    >
      <div class="topbar-left">
        <button
          ref="mobileMenuBtnRef"
          type="button"
          class="mobile-menu-btn"
          :aria-expanded="mobileSidebarOpen"
          aria-label="打开会话导航"
          @click="toggleMobileSidebar"
        >
          <Menu :size="18" />
        </button>

        <div class="brand-lockup">
          <span class="brand-square"><Activity :size="16" :stroke-width="2.2" /></span>
          <div class="brand-titles">
            <strong>Medical-Agent · 可溯源医学问答系统</strong>
            <small>基于 LangGraph 的多专家协同与声明级溯源研究原型</small>
          </div>
        </div>
      </div>

      <!-- Live Infrastructure Status Cluster (Decoupled from Hardcoded Labels) -->
      <div class="system-status-cluster" role="status" aria-label="服务架构与运行环境状态">
        <span
          class="status-badge"
          :class="backendHealth ? 'online' : 'offline'"
          :title="backendHealth ? 'FastAPI 本地 8010 服务在线' : '8010 服务离线'"
        >
          <span class="pulse-dot"></span>
          <span>{{ backendHealth ? '8010 在线' : '服务离线' }}</span>
        </span>
        <span class="status-chip mono" title="多智能体工作流编排引擎">
          <GitBranch :size="12" />
          <span>LangGraph v{{ backendHealth?.graph_version || 3 }}</span>
        </span>
        <span class="status-chip mono" title="本地向量检索与知识库">
          <Database :size="12" />
          <span>{{ backendHealth ? (backendHealth.providers.knowledge === 'milvus_bge' ? 'Milvus+BGE' : (backendHealth.providers.knowledge === 'fake' ? '离线合成库' : backendHealth.providers.knowledge)) : '知识库未就绪' }}</span>
        </span>
        <span class="status-chip mono" title="推理驱动模型">
          <Sparkles :size="12" />
          <span>{{ backendHealth ? (backendHealth.providers.model === 'deepseek' ? 'DeepSeek API' : '离线 FakeModel') : '模型未就绪' }}</span>
        </span>
      </div>

      <!-- Topbar Actions -->
      <div class="topbar-right">
        <button
          v-if="currentBackendRun"
          type="button"
          class="secondary-nav-btn export-btn"
          title="生成并导出当前轮次《医疗循证科研专报》"
          @click="openExportModal"
        >
          <FileText :size="14" />
          <span class="btn-label-text">导出专报</span>
        </button>

        <button
          v-if="token"
          type="button"
          class="secondary-nav-btn"
          title="查看患者长期病历事实库 (Mem0)"
          @click="openMemoryModal"
        >
          <Database :size="14" />
          <span class="btn-label-text">记忆 ({{ facts.length }})</span>
        </button>

        <button
          type="button"
          class="secondary-nav-btn"
          title="查看已入库的国内外权威临床指南与教材规范大纲"
          aria-label="打开知识库大纲目录"
          @click="openCatalogModal"
        >
          <BookOpen :size="14" />
          <span class="btn-label-text">知识库大纲</span>
        </button>

        <button
          v-if="activeInspectorRun"
          type="button"
          class="inspector-toggle-btn"
          :class="{ active: isRightPanelVisible }"
          :aria-expanded="isRightPanelVisible"
          aria-label="切换证据与审核面板"
          @click="toggleRightPanel"
        >
          <PanelRightOpen :size="15" />
          <span>{{ isRightPanelVisible ? '收起证据栏' : '证据与审核' }}</span>
        </button>
      </div>
    </header>

    <!-- ======================================================================
         MAIN WORKSPACE: Sidebar | Conversation Reading Center | Collapsible Inspector
         ====================================================================== -->
    <div
      class="med-workspace"
      :class="{ 'inspector-collapsed': !isRightPanelVisible }"
    >
      <!-- Backdrop for mobile drawers -->
      <div
        v-if="isLeftDrawerModal || isRightDrawerModal"
        class="mobile-backdrop"
        @click="closeActiveBackdrop"
      ></div>

      <!-- --------------------------------------------------------------------
           LEFT COLUMN: SESSION NAVIGATION
           -------------------------------------------------------------------- -->
      <aside
        ref="sidebarRef"
        v-show="!isMobileViewport || mobileSidebarOpen"
        class="med-sidebar"
        :class="{ 'mobile-open': mobileSidebarOpen }"
        :role="isMobileViewport ? 'dialog' : undefined"
        :aria-modal="isLeftDrawerModal ? 'true' : undefined"
        aria-label="会话列表导航"
        :inert="
          (isMobileViewport && !mobileSidebarOpen) ||
          catalogModalOpen ||
          memoryModalOpen ||
          exportModalOpen ||
          isRightDrawerModal
            ? true
            : undefined
        "
        :aria-hidden="
          (isMobileViewport && !mobileSidebarOpen) ||
          catalogModalOpen ||
          memoryModalOpen ||
          exportModalOpen ||
          isRightDrawerModal
            ? 'true'
            : undefined
        "
      >
        <div v-if="isMobileViewport" class="mobile-drawer-bar">
          <strong>会话导航</strong>
          <button
            type="button"
            class="mobile-drawer-close-btn"
            aria-label="关闭会话导航"
            @click="closeMobileSidebar"
          >
            <X :size="17" />
          </button>
        </div>

        <!-- REAL PRODUCTION WORKSPACE SIDEBAR -->
        <div class="sidebar-section-head">
          <div>
            <span class="eyebrow-tag real">科研工作区</span>
            <h2>历史咨询会话</h2>
          </div>
          <button
            type="button"
            class="icon-action-btn"
            title="刷新系统状态与会话"
            aria-label="刷新系统状态与会话"
            @click="checkBackendHealth(); token && runBackendAction(loadBackendSessionData)"
          >
            <RefreshCw :size="15" />
          </button>
        </div>

        <div class="backend-health-card">
          <div class="health-row">
            <span>后端服务状态</span>
            <strong :class="backendHealth ? 'ok' : 'err'">
              {{ backendHealth ? '在线 (8010 正常)' : '未连接 (需启动)' }}
            </strong>
          </div>
          <template v-if="backendHealth">
            <div class="health-row">
              <span>运行模式</span>
              <span class="mono">{{ backendHealth.mode }}</span>
            </div>
            <div class="health-row">
              <span>知识库画像</span>
              <span class="mono">{{ backendHealth.knowledge_profile || 'medical_guideline' }}</span>
            </div>
          </template>
          <p v-else class="health-err-note">
            请确认后端已通过 <code>启动系统.bat</code> 运行在 8010 端口。
          </p>
        </div>

        <template v-if="token">
          <div class="signed-user-bar">
            <div class="user-info">
              <UserCheck :size="15" />
              <strong>{{ signedIn }}</strong>
            </div>
            <button
              type="button"
              class="logout-btn"
              :disabled="backendBusy"
              @click="logoutBackend"
            >
              <LogOut :size="14" />
              <span>退出</span>
            </button>
          </div>

          <button
            type="button"
            class="new-session-btn"
            :disabled="backendBusy"
            @click="createBackendSession"
          >
            <MessageSquarePlus :size="15" />
            <span>新建咨询会话</span>
          </button>

          <nav class="session-list" aria-label="科研咨询会话列表">
            <p v-if="!sessions.length" class="empty-sessions-hint">
              暂无历史会话，点击上方“新建咨询会话”开始循证咨询。
            </p>
            <button
              v-for="s in sessions"
              :key="s.id"
              type="button"
              class="session-item"
              :class="{ active: s.id === sessionId }"
              @click="chooseBackendSession(s.id)"
            >
              <strong class="session-item-title">{{ s.title }}</strong>
              <div class="session-item-meta">
                <span class="scen-status-dot completed"></span>
                <span class="mono">ID: {{ s.id.slice(0, 8) }}</span>
              </div>
            </button>
          </nav>
        </template>

        <div v-else class="sidebar-login-hint">
          <KeyRound :size="18" />
          <p>请在右侧验证研究员身份以访问个人专属会话与长期病历档案。</p>
        </div>

        <div class="sidebar-footer-box">
          <span>NLM / PubMed 成人高血压与糖尿病循证指南 · 严谨留痕</span>
        </div>
      </aside>

      <!-- --------------------------------------------------------------------
           CENTER COLUMN: CONVERSATION READING CENTER & COMPOSER
           -------------------------------------------------------------------- -->
      <main
        class="med-center"
        aria-label="医学问答对话主区"
        :inert="anyModalOpen ? true : undefined"
        :aria-hidden="anyModalOpen ? 'true' : undefined"
      >
        <div v-if="backendError" class="global-error-alert" role="alert">
          <AlertTriangle :size="17" />
          <span>{{ backendError }}</span>
          <button
            type="button"
            class="alert-close"
            aria-label="关闭错误提示"
            @click="backendError = ''"
          >
            <X :size="15" />
          </button>
        </div>

        <!-- Login / Register Gate when unauthenticated -->
        <div v-if="!token" class="backend-auth-container">
          <div class="auth-card">
            <div class="auth-card-head">
              <span class="eyebrow-tag real">临床科研安全认证中心</span>
              <h2>研究员身份凭证验证</h2>
              <p>
                系统采用安全 Argon2 单向散列与短期 HS256 JWT 凭证授权，严格遵循按用户会话与病历事实隔离规范。
              </p>
            </div>

            <!-- Quick Connect Helper for Reviewers & Interview Demonstrations -->
            <div class="quick-connect-banner">
              <div class="quick-connect-info">
                <Sparkles :size="16" />
                <div>
                  <strong>评审与快速体验通道</strong>
                  <p>一键以默认研究员身份登录进入工作台（若账号不存在将自动创建）</p>
                </div>
              </div>
              <button
                type="button"
                class="btn primary quick-btn"
                :disabled="backendBusy"
                @click="quickLoginResearcher"
              >
                一键登录工作台 →
              </button>
            </div>

            <div class="auth-divider">
              <span>或使用已有凭证登录</span>
            </div>

            <form class="auth-form" @submit.prevent="authenticateBackend(false)">
              <div class="form-field">
                <label for="backend-username">用户名 (3–40 位字符)</label>
                <input
                  id="backend-username"
                  v-model="username"
                  type="text"
                  autocomplete="username"
                  minlength="3"
                  maxlength="40"
                  required
                  placeholder="例如：demo_researcher"
                />
              </div>
              <div class="form-field">
                <label for="backend-password">登录密码 (至少 8 位)</label>
                <input
                  id="backend-password"
                  v-model="password"
                  type="password"
                  autocomplete="current-password"
                  minlength="8"
                  required
                  placeholder="请输入密码"
                />
              </div>

              <div class="auth-buttons">
                <button
                  type="submit"
                  class="btn primary"
                  :disabled="backendBusy || username.trim().length < 3 || password.length < 8"
                >
                  {{ backendBusy ? '处理中…' : '登录系统' }}
                </button>
                <button
                  type="button"
                  class="btn secondary"
                  :disabled="backendBusy || username.trim().length < 3 || password.length < 8"
                  @click="authenticateBackend(true)"
                >
                  注册新研究员
                </button>
              </div>
            </form>
          </div>
        </div>

        <!-- Authenticated Backend Conversation Workspace -->
        <template v-else>
          <header class="session-header">
            <div class="session-header-main">
              <h1>
                {{
                  sessions.find(s => s.id === sessionId)?.title ||
                  '请选择左侧会话或新建咨询会话'
                }}
              </h1>
              <span class="session-mode-badge real">
                8010 智能体服务 ({{ backendHealth ? formatLabel(backendHealth.mode) : '未连接' }})
              </span>
            </div>
            <div class="session-header-actions">
              <button
                type="button"
                class="btn secondary sm"
                :disabled="backendBusy || !sessionId"
                @click="runBackendAction(loadBackendSessionData)"
              >
                <RefreshCw :size="14" />
                <span>同步状态</span>
              </button>
            </div>
          </header>

          <div ref="chatScrollRef" class="conversation-stream" role="log" aria-live="polite">
            <div class="conversation-inner">
              <div v-if="!sessionId" class="empty-conversation">
                <MessageSquarePlus :size="30" :stroke-width="1.4" />
                <h2>尚未选择咨询会话</h2>
                <p>请点击左侧“新建咨询会话”或选择已有历史会话开始循证咨询。</p>
                <button type="button" class="btn primary" @click="createBackendSession">
                  新建咨询会话
                </button>
              </div>

              <div v-else-if="!backendTurns.length && !backendChatPending" class="empty-conversation">
                <BookOpen :size="30" :stroke-width="1.4" />
                <h2>科研咨询会话已就绪，等待提交问题</h2>
                <p>
                  点击下方临床指南典型用例填充输入框，确认后点击“发送”由多 Agent 执行检索与事实核验：
                </p>
                <div class="empty-example-grid">
                  <button
                    v-for="(ex, idx) in BACKEND_QUESTION_EXAMPLES"
                    :key="idx"
                    type="button"
                    class="empty-example-card"
                    :disabled="backendBusy"
                    @click="backendQuestion = ex.text; composerRef?.focus()"
                  >
                    <Sparkles :size="14" />
                    <div>
                      <strong>{{ ex.label }}</strong>
                      <span>{{ ex.text }}</span>
                    </div>
                  </button>
                </div>
              </div>

              <template v-else>
                <ConversationTurnCard
                  v-for="t in backendTurns"
                  :key="t.id"
                  :question="t.question"
                  :answer-text="t.answer"
                  :created-at="t.createdAt"
                  :run="t.run"
                  :selected="selectedBackendRunId === t.runId"
                  :busy="backendBusy"
                  :is-simulation="false"
                  :progress-events="pendingBackendRun?.run_id === t.runId ? backendEvents : []"
                  :progress-sync-delayed="pendingBackendRun?.run_id === t.runId && backendProgressStale"
                  :selected-claim-index="
                    selectedBackendRunId === t.runId
                      ? (selectedClaim?.claim.index ?? null)
                      : null
                  "
                  @select-turn="selectBackendRun(t.runId)"
                  @select-claim="(seg, el) => handleSelectClaim(seg, t.runId, el)"
                  @inspect-source="(src, el) => handleInspectSource(src, t.runId, el)"
                  @inspect-omitted-claims="el => handleInspectOmittedClaims(t.runId, el)"
                  @open-trace-view="(sec, el) => handleOpenTraceView(sec, t.runId, el)"
                  @retry-question="q => sendBackendQuestion(q)"
                  @cancel-run="cancelBackendRun"
                />

                <button
                  v-if="moreHistory"
                  type="button"
                  class="btn secondary load-more-btn"
                  :disabled="backendBusy"
                  @click="runBackendAction(() => loadBackendHistory(true))"
                >
                  加载更早的会话消息
                </button>
              </template>
              <template v-if="backendChatPending && pendingRequest">
                <div v-if="!pendingBackendRun && pendingRequest" class="pending-question">{{ pendingRequest.question }}</div>
                <RunProgress
                  v-if="!pendingBackendRun"
                  :run="null"
                  :sync-delayed="backendProgressStale"
                />
              </template>
            </div>
          </div>

          <!-- Clarification / Resume Bar when run is paused or awaiting_input -->
          <form
            v-if="
              currentBackendRun &&
              ['awaiting_input', 'paused'].includes(currentBackendRun.run_status)
            "
            class="clarification-resume-bar"
            @submit.prevent="resumeBackendRun"
          >
            <div class="clarify-head">
              <AlertTriangle :size="16" />
              <strong>
                当前运行处于“{{ formatLabel(currentBackendRun.run_status) }}”状态 (checkpoint:
                {{ currentBackendRun.checkpoint_id?.slice(0, 10) }})
              </strong>
            </div>
            <div class="clarify-controls">
              <input
                v-model="clarificationInput"
                type="text"
                :required="currentBackendRun.run_status === 'awaiting_input'"
                placeholder="填写补充说明以从当前检查点恢复运行…"
              />
              <button type="submit" class="btn primary" :disabled="backendBusy">
                恢复运行
              </button>
              <button
                type="button"
                class="btn secondary"
                :disabled="backendBusy"
                @click="cancelBackendRun"
              >
                取消运行
              </button>
            </div>
          </form>

          <!-- Compact Composer for Backend Mode -->
          <section class="composer-section" aria-label="循证科研提问区">
            <div class="composer-inner">
              <div v-if="backendTurns.length > 0" class="suggestion-chips">
                <button
                  v-for="(ex, idx) in BACKEND_QUESTION_EXAMPLES"
                  :key="idx"
                  type="button"
                  class="suggestion-chip"
                  :disabled="backendBusy || !sessionId"
                  @click="backendQuestion = ex.text; composerRef?.focus()"
                >
                  <span>{{ ex.label }}</span>
                </button>
              </div>

              <form class="composer-row" @submit.prevent="sendBackendQuestion()">
                <textarea
                  ref="composerRef"
                  v-model="backendQuestion"
                  rows="3"
                  maxlength="8000"
                  :disabled="backendBusy || !sessionId"
                  placeholder="输入医学健康咨询或临床科研问题（支持高血压、糖尿病、呼吸、消化、急症、妇产、儿科等中国临床标准）…"
                  aria-label="循证健康知识问题输入"
                  @keydown.enter.exact="
                    !$event.isComposing && ($event.preventDefault(), sendBackendQuestion())
                  "
                ></textarea>
                <button
                  type="submit"
                  class="send-btn"
                  :disabled="backendBusy || !backendQuestion.trim() || !sessionId"
                  aria-label="发送提问"
                  title="发送提问 (Enter)"
                >
                  <ArrowUp :size="17" />
                  <span class="send-btn-text">{{ backendBusy ? '执行中' : '发送' }}</span>
                </button>
              </form>
            </div>
          </section>
        </template>
      </main>

      <!-- --------------------------------------------------------------------
           RIGHT COLUMN / DRAWER: COLLAPSIBLE EVIDENCE & TRACE INSPECTOR
           -------------------------------------------------------------------- -->
      <div
        ref="inspectorColRef"
        v-show="isRightPanelVisible"
        class="med-inspector-col"
        :class="{ 'mobile-open': mobileInspectorOpen }"
        :role="isNarrowViewport ? 'dialog' : undefined"
        :aria-modal="isRightDrawerModal ? 'true' : undefined"
        :aria-label="isNarrowViewport ? '引用证据与执行审核抽屉' : undefined"
        :inert="
          !isRightPanelVisible ||
          catalogModalOpen ||
          memoryModalOpen ||
          exportModalOpen ||
          isLeftDrawerModal
            ? true
            : undefined
        "
        :aria-hidden="
          !isRightPanelVisible ||
          catalogModalOpen ||
          memoryModalOpen ||
          exportModalOpen ||
          isLeftDrawerModal
            ? 'true'
            : undefined
        "
      >
        <EvidenceAndTracePanel
          ref="evidencePanelRef"
          :run="activeInspectorRun"
          :events="activeInspectorEvents"
          :provider-calls="activeInspectorCalls"
          :session-summary="activeInspectorSummary"
          :active-tab="rightInspectorTab"
          :highlighted-source-id="highlightedSourceId"
          :selected-claim="selectedClaim"
          :claim-filter="claimFilter"
          :is-simulation="false"
          :is-drawer="isNarrowViewport"
          @update:active-tab="val => (rightInspectorTab = val)"
          @update:claim-filter="val => (claimFilter = val)"
          @clear-selected-claim="selectedClaim = null"
          @focus-source-id="handleFocusSourceCard"
          @close="closeRightPanel"
        />
      </div>
    </div>

    <!-- ======================================================================
         SECONDARY MODAL 2: LONG-TERM MEMORIES & MAINTENANCE JOBS (Mem0)
         ====================================================================== -->
    <div
      v-if="memoryModalOpen"
      class="reg-modal-backdrop"
      @click.self="closeMemoryModal"
    >
      <section
        ref="memoryModalRef"
        class="memory-modal-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="mem-title"
      >
        <header class="reg-drawer-header">
          <div>
            <div class="reg-eyebrow">
              <Database :size="14" />
              <span>患者长期记忆与增量摘要后台维护</span>
            </div>
            <h2 id="mem-title">患者病历事实库与维护队列</h2>
          </div>
          <button
            type="button"
            class="drawer-close-btn"
            aria-label="关闭窗口"
            @click="closeMemoryModal"
          >
            <X :size="18" />
          </button>
        </header>

        <div class="reg-drawer-body">
          <p class="mem-intro">
            仅保存明确的偏好、过敏史、既往病史与用药目标。纠正或撤回记忆会使旧会话摘要失效并触发后台同步，原始记录保留在 SQL 审计账本。
          </p>

          <div v-if="!facts.length" class="empty-reg-records">
            <p>当前账号尚无筛选后的长期记忆事实。</p>
          </div>

          <div v-else class="mem-list">
            <article v-for="fact in facts" :key="fact.id" class="mem-card">
              <div class="mem-card-head">
                <strong class="mono">{{ fact.key }}</strong>
                <span class="reg-badge">{{ formatLabel(fact.status) }}</span>
                <span class="mono">本地 v{{ fact.version }} · 同步 v{{ fact.synced_version }}</span>
              </div>
              <div class="nl-input-row">
                <input
                  v-model="factDrafts[fact.id]"
                  type="text"
                  maxlength="300"
                  :disabled="backendBusy"
                />
                <button
                  type="button"
                  class="btn primary"
                  :disabled="backendBusy || !factDrafts[fact.id]?.trim()"
                  @click="editMemoryFact(fact, 'update')"
                >
                  {{ fact.status === 'deleted' ? '恢复此记忆' : '保存纠正' }}
                </button>
                <button
                  v-if="fact.status !== 'deleted'"
                  type="button"
                  class="btn secondary"
                  :disabled="backendBusy"
                  @click="editMemoryFact(fact, 'delete')"
                >
                  撤回
                </button>
              </div>
            </article>
          </div>

          <div v-if="maintenanceJobs.length" class="audit-log-box">
            <div class="records-head">
              <h4>后台维护任务队列 ({{ maintenanceJobs.length }})</h4>
              <button
                v-if="
                  maintenanceJobs.some(j =>
                    ['failed', 'uncertain', 'awaiting_remote'].includes(j.status),
                  )
                "
                type="button"
                class="btn secondary"
                :disabled="backendBusy"
                @click="retryMaintenanceJobs"
              >
                核对并重试失败任务
              </button>
            </div>
            <ul>
              <li v-for="job in maintenanceJobs.slice(0, 12)" :key="job.id">
                <strong class="mono">{{ job.action }}</strong>
                <span>{{ formatLabel(job.status) }} · 尝试 {{ job.attempts }} 次</span>
                <span v-if="job.safe_error_code" class="err-msg mono">{{ job.safe_error_code }}</span>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </div>

    <!-- Inline Citation Evidence Popover -->
    <CitationPopover
      :claim="popoverClaim"
      :anchor-el="popoverAnchorEl"
      :run="activeInspectorRun"
      :open="popoverOpen"
      @close="closePopover"
      @open-full-inspector="handleOpenFullInspectorFromPopover"
      @inspect-source="src => handleInspectSource(src, sessionId, popoverAnchorEl)"
    />

    <!-- Dossier Export Modal (Clinical Evidence Dossier) -->
    <ExportDossierModal
      :open="exportModalOpen"
      :session-title="sessions.find(s => s.id === sessionId)?.title"
      :question="activeTurnForExport?.question || backendQuestion || ''"
      :answer="activeTurnForExport?.answer || currentBackendRun?.answer || null"
      :run="activeTurnForExport?.run || currentBackendRun"
      :events="activeEventsForExport"
      :provider-calls="activeCallsForExport"
      @close="closeExportModal"
      @show-toast="showToast"
    />

    <!-- Knowledge Catalog Modal -->
    <KnowledgeCatalogModal
      :open="catalogModalOpen"
      @close="closeCatalogModal"
    />

    <!-- Global Toast -->
    <Transition name="toast">
      <div v-if="toastText" class="med-toast" role="status">
        <CheckCircle2 :size="15" />
        <span>{{ toastText }}</span>
      </div>
    </Transition>
  </div>
</template>
