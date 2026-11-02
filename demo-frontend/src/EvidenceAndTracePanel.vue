<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import {
  AlertTriangle,
  ArrowDown,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ExternalLink,
  Filter,
  GitBranch,
  PanelRightClose,
  X,
  XCircle,
} from 'lucide-vue-next'
import type {
  ClaimReviewItem,
  EvidenceAnchor,
  ExecutionEventItem,
  ProviderCallItem,
  RunOut,
  SessionSummaryItem,
  SourceItem,
  SourceSpan,
} from './types'
import {
  CLAIM_KIND_LABELS,
  buildTaskWaves,
  describeSafeError,
  formatAgentRole,
  formatCallCount,
  formatLabel,
  formatStage,
  isSimulatedRun,
  resolveActualTasks,
  summarizeClaims,
  type MappedAnswerClaim,
} from './medicalLabels'

const props = defineProps<{
  run: RunOut | null
  events: ExecutionEventItem[]
  providerCalls: ProviderCallItem[]
  sessionSummary?: SessionSummaryItem | null
  activeTab: 'evidence' | 'trace'
  highlightedSourceId?: string | null
  selectedClaim?: MappedAnswerClaim | null
  claimFilter: 'all' | 'omitted'
  isSimulation: boolean
  isDrawer?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:activeTab', value: 'evidence' | 'trace'): void
  (e: 'update:claimFilter', value: 'all' | 'omitted'): void
  (e: 'clearSelectedClaim'): void
  (e: 'focusSourceId', sourceId: string): void
  (e: 'close'): void
}>()

const inspectorBodyRef = ref<HTMLElement | null>(null)
const omittedSectionRef = ref<HTMLElement | null>(null)
const selectedClaimBoxRef = ref<HTMLElement | null>(null)
const claimDetailsOpen = ref(false)

const simulated = computed(() => isSimulatedRun(props.run, props.isSimulation))
const actualTasks = computed(() => resolveActualTasks(props.run))
const taskWaves = computed(() => buildTaskWaves(actualTasks.value))
const claimStats = computed(() => summarizeClaims(props.run?.claim_reviews))
const safeErrorInfo = computed(() =>
  describeSafeError(props.run?.safe_error_code || props.run?.reviewer_error_code),
)
const answerSummary = computed(() => {
  const r = props.run
  if (!r) return '尚无回答记录'
  if (r.run_status === 'running') return '正在处理'
  if (r.run_status === 'awaiting_input') return '需要你补充说明'
  if (r.reviewer_status === 'failed') return '引用核对未完成'
  if (r.result_status === 'partial') return '部分完成，请留意未采用内容或运行限制'
  if (r.result_status === 'completed') return '本轮已完成'
  return formatLabel(r.result_status || r.run_status)
})

const filteredClaims = computed<ClaimReviewItem[]>(() => {
  const all = props.run?.claim_reviews || []
  if (props.claimFilter === 'omitted') {
    return all.filter(c => c.support_status !== 'supported')
  }
  return all
})

const omittedClaimsCount = computed(() => {
  const all = props.run?.claim_reviews || []
  return all.filter(c => c.support_status !== 'supported').length
})

const highlightedAnchorKeys = computed(() => {
  const keys = new Set<string>()
  if (!props.selectedClaim) return keys
  for (const a of props.selectedClaim.evidenceAnchors) {
    keys.add(`${a.document_id}:${a.start}:${a.end}`)
  }
  return keys
})

function isAnchorHighlighted(source: SourceItem, span: SourceSpan): boolean {
  if (!props.selectedClaim || !source.document_id) return false
  return highlightedAnchorKeys.value.has(`${source.document_id}:${span.start}:${span.end}`)
}

function isSourceSupportingSelectedClaim(source: SourceItem, index: number): boolean {
  if (!props.selectedClaim) return false
  if (props.selectedClaim.sourceNumbers.includes(index + 1)) return true
  return props.selectedClaim.evidenceAnchors.some(a => a.source_id === source.id)
}

function formatEditorialBody(content: string): string {
  // Strip redundant trailing '英文依据：...' from Chinese editorial display since quotes are shown right below
  const markerIdx = content.indexOf('\n英文依据：')
  const body = markerIdx >= 0 ? content.slice(0, markerIdx) : content
  const lines = body.split('\n').map(l => l.trim()).filter(Boolean)
  if (lines.length > 1 && lines[0]!.length <= 24) {
    return lines.slice(1).join('\n')
  }
  return body
}

const emptySourceExplanation = computed(() => {
  const r = props.run
  if (!r) return '选择一轮对话后，此处展示该回答绑定的 NLM/MedlinePlus 资料章节与英文原文片段。'
  if (r.response_origin === 'urgent_policy') {
    return '本轮触发紧急医疗风险规则出口（urgent_policy），系统跳过常规资料检索并直接给出就医提示，因此不附带知识库引用。'
  }
  if (r.run_status === 'failed' || r.result_status === 'failed') {
    return `本轮运行未完成（${r.safe_error_code || '运行失败'}），未产出有效回答与引用来源。`
  }
  if (r.reviewer_status === 'failed') {
    return `本轮回答在逐项引用审核阶段未通过契约校验（${r.reviewer_error_code || r.safe_error_code || 'REVIEW_FAILED'}），系统已拦截未审核原稿并清空未核实来源。可切换到“执行与审核”查看拦截溯源。`
  }
  if (r.safe_error_code === 'EVIDENCE_MISSING') {
    return '当前 20 份 NLM/MedlinePlus 成人高血压与 2 型糖尿病正式库中未检索到直接支持该问题的原文片段，系统不编造库外引用。'
  }
  return '本轮回答未引用本地医学知识库条目。'
})

async function focusOmittedSection() {
  claimDetailsOpen.value = true
  await nextTick()
  if (omittedSectionRef.value) {
    omittedSectionRef.value.scrollIntoView({ behavior: 'smooth', block: 'start' })
    const btn = omittedSectionRef.value.querySelector<HTMLElement>(
      '.back-all-claims-btn, .filter-pill-btn:not(:disabled), button:not(:disabled)',
    )
    if (btn) {
      btn.focus()
    } else {
      omittedSectionRef.value.focus()
    }
  }
}

watch(() => props.run?.run_id, () => { claimDetailsOpen.value = props.claimFilter === 'omitted' })

async function focusSelectedClaimBox() {
  await nextTick()
  if (selectedClaimBoxRef.value) {
    selectedClaimBoxRef.value.scrollIntoView({ behavior: 'smooth', block: 'start' })
    const btn = selectedClaimBoxRef.value.querySelector<HTMLElement>(
      '.clear-locator-btn, .jump-source-btn, button:not(:disabled)',
    )
    if (btn) {
      btn.focus()
    } else {
      selectedClaimBoxRef.value.focus()
    }
  }
}

watch(
  () => [props.activeTab, props.claimFilter],
  ([tab, filter]) => {
    if (tab === 'trace' && filter === 'omitted') {
      void focusOmittedSection()
    }
  },
)

watch(
  () => props.selectedClaim,
  val => {
    if (val && props.activeTab === 'evidence') {
      void focusSelectedClaimBox()
    }
  },
)

defineExpose({
  focusOmittedSection,
  focusSelectedClaimBox,
})
</script>

<template>
  <aside
    class="inspector-shell"
    :class="{ 'is-drawer': isDrawer }"
    aria-label="引用证据与执行审核面板"
  >
    <header class="inspector-header">
      <div class="inspector-tabs" role="tablist" aria-label="右侧详情标签切换">
        <button
          role="tab"
          type="button"
          :aria-selected="activeTab === 'evidence'"
          :class="{ active: activeTab === 'evidence' }"
          @click="emit('update:activeTab', 'evidence')"
        >
          <BookOpen :size="15" />
          <span>引用证据与原文</span>
          <span class="tab-count">{{ run?.sources?.length ?? 0 }}</span>
        </button>
        <button
          role="tab"
          type="button"
          :aria-selected="activeTab === 'trace'"
          :class="{ active: activeTab === 'trace' }"
          @click="emit('update:activeTab', 'trace')"
        >
          <GitBranch :size="15" />
          <span>回答说明</span>
          <span v-if="omittedClaimsCount > 0" class="tab-count warn">
            省略 {{ omittedClaimsCount }}
          </span>
          <span v-else-if="actualTasks.length" class="tab-count">{{ actualTasks.length }}</span>
        </button>
      </div>
      <button
        type="button"
        class="panel-collapse-btn"
        :aria-label="isDrawer ? '关闭详情抽屉' : '收起右侧详情栏'"
        :title="isDrawer ? '关闭详情抽屉 (Esc)' : '收起右侧详情栏'"
        @click="emit('close')"
      >
        <X v-if="isDrawer" :size="17" />
        <PanelRightClose v-else :size="16" />
      </button>
    </header>

    <!-- Honest Verification Status Strip -->
    <div class="truth-strip">
      <div class="truth-item">
        <span class="truth-label">引用核对</span>
        <strong
          class="truth-val"
          :class="{
            ok: run?.citation_support_status === 'model_reviewed',
            warn: run?.citation_support_status === 'unverified',
          }"
        >
          {{
            run?.citation_support_status === 'model_reviewed'
              ? simulated
                ? '模拟引用核对完成'
                : '模型引用核对完成'
              : formatLabel(run?.citation_support_status || 'not_run')
          }}
        </strong>
      </div>
      <div class="truth-divider"></div>
      <div class="truth-item">
        <span class="truth-label">医学专业审核</span>
        <strong class="truth-val clinical-pending">
          未执行
        </strong>
      </div>
    </div>

    <div ref="inspectorBodyRef" class="inspector-body">
      <!-- ====================================================================
           TAB 1: SOURCES & PER-FACT EVIDENCE ANCHORS
           ==================================================================== -->
      <template v-if="activeTab === 'evidence'">
        <!-- Selected Per-Fact Evidence Locator Card -->
        <section
          v-if="selectedClaim"
          ref="selectedClaimBoxRef"
          tabindex="-1"
          class="selected-claim-locator"
          aria-label="当前选中事实的原文依据"
        >
          <div class="locator-head">
            <span class="locator-badge">
              正在查看句子 #{{ selectedClaim.claim.index + 1 }} 的逐事实依据
            </span>
            <button
              type="button"
              class="clear-locator-btn"
              @click="emit('clearSelectedClaim')"
            >
              显示全部来源 ({{ run?.sources?.length || 0 }})
            </button>
          </div>

          <p class="locator-claim-text">“{{ selectedClaim.claim.text }}”</p>

          <div class="locator-status-row">
            <span class="claim-verdict-pill supported">
              {{ simulated ? '模拟核对：原文支持' : '模型核对：原文支持' }}
            </span>
            <span class="mono">
              第 {{ selectedClaim.claim.review_round || 1 }} 轮核定
            </span>
            <span class="mono">
              共 {{ selectedClaim.evidenceAnchors.length }} 处原文段落支持
            </span>
          </div>

          <p class="locator-note">{{ selectedClaim.claim.note }}</p>

          <div class="locator-anchors-list">
            <div
              v-for="(anc, aIdx) in selectedClaim.evidenceAnchors"
              :key="`${anc.id}-${aIdx}`"
              class="locator-anchor-item"
            >
              <div class="locator-anchor-top">
                <strong>对应英文原文 #{{ aIdx + 1 }}</strong>
                <button
                  type="button"
                  class="jump-source-btn"
                  @click="emit('focusSourceId', anc.source_id)"
                >
                  定位至来源卡片 ↓
                </button>
              </div>
              <blockquote class="locator-quote">“{{ anc.quote }}”</blockquote>
            </div>
          </div>
        </section>

        <!-- Empty State -->
        <div v-if="!run || !run.sources || run.sources.length === 0" class="empty-inspector">
          <BookOpen :size="28" :stroke-width="1.4" />
          <h3>当前轮次无引用来源</h3>
          <p>{{ emptySourceExplanation }}</p>
          <button
            v-if="run && (run.reviewer_status === 'failed' || run.safe_error_code)"
            type="button"
            class="link-btn"
            @click="emit('update:activeTab', 'trace')"
          >
            查看执行与审核拦截详情 →
          </button>
        </div>

        <!-- Source Cards -->
        <div v-else class="source-list">
          <article
            v-for="(source, idx) in run.sources"
            :key="source.id"
            :id="`source-card-${source.id}`"
            class="source-card"
            :class="{
              highlighted:
                highlightedSourceId === source.id || isSourceSupportingSelectedClaim(source, idx),
            }"
          >
            <div class="source-card-top">
              <span class="source-index">[来源 {{ idx + 1 }}]</span>
              <span class="source-origin-tag">
                {{ source.source === 'pubmed' ? 'PubMed 索引元数据' : 'NLM/MedlinePlus 公开资料快照' }}
              </span>
              <span
                v-if="isSourceSupportingSelectedClaim(source, idx)"
                class="supporting-current-tag"
              >
                支持当前选中句子
              </span>
            </div>

            <h3 class="source-title">
              {{ source.title || source.document_id || source.id }}
              <span v-if="source.section" class="source-section-sub">· {{ source.section }}</span>
            </h3>

            <p class="source-scope-line">
              {{ source.publisher || 'U.S. National Library of Medicine' }} · 适用范围：美国成人健康教育（非官方中译，未经临床复核）
            </p>

            <div class="source-editorial-block">
              <div class="block-label">
                <span>中文编辑摘述</span>
              </div>
              <p class="editorial-text">{{ formatEditorialBody(source.content) }}</p>
            </div>

            <div v-if="source.source_spans && source.source_spans.length" class="source-anchors-block">
              <div class="block-label">
                <span>绑定的英文原文片段 ({{ source.source_spans.length }} 处)</span>
              </div>
              <ul class="anchor-list">
                <li
                  v-for="(span, sIdx) in source.source_spans"
                  :key="sIdx"
                  class="anchor-item"
                  :class="{ 'anchor-matched': isAnchorHighlighted(source, span) }"
                >
                  <span v-if="isAnchorHighlighted(source, span)" class="matched-anchor-tag">
                    当前选中事实依据
                  </span>
                  <blockquote class="anchor-quote">“{{ span.quote }}”</blockquote>
                </li>
              </ul>
            </div>

            <!-- Collapsible Technical Provenance Details (Hash, Offsets, Version, Scores) -->
            <details class="source-tech-details">
              <summary>展开技术校验信息（SHA256 / 字符位置 / 版本）</summary>
              <dl class="tech-meta-dl mono">
                <div v-if="source.document_id">
                  <dt>document_id</dt>
                  <dd>{{ source.document_id }}</dd>
                </div>
                <div v-if="source.version">
                  <dt>version</dt>
                  <dd>{{ source.version }}</dd>
                </div>
                <div v-if="source.source_sha256">
                  <dt>source_sha256</dt>
                  <dd class="hash-break">{{ source.source_sha256 }}</dd>
                </div>
                <div v-if="typeof source.start === 'number' && typeof source.end === 'number'">
                  <dt>中文摘述字符区间</dt>
                  <dd>[{{ source.start }}..{{ source.end }}] ({{ source.end - source.start }} chars)</dd>
                </div>
                <div v-if="source.source_spans && source.source_spans.length">
                  <dt>英文锚点字符区间</dt>
                  <dd>
                    <span
                      v-for="(sp, i) in source.source_spans"
                      :key="i"
                      class="span-offset-item"
                    >
                      #{{ i + 1 }}: [{{ sp.start }}..{{ sp.end }}] (len={{ sp.quote.length }})
                    </span>
                  </dd>
                </div>
                <div>
                  <dt>检索分值</dt>
                  <dd>
                    <template v-if="typeof source.score === 'number'">
                      BGE {{ source.score.toFixed(3) }}
                      <template v-if="typeof source.rerank_score === 'number'">
                        · Rerank {{ source.rerank_score.toFixed(3) }}
                      </template>
                    </template>
                    <template v-else>
                      {{ simulated ? '本地模拟固定快照绑定（非实时向量分数）' : '未记录' }}
                    </template>
                  </dd>
                </div>
              </dl>
            </details>

            <div class="source-card-footer">
              <span class="license-note">{{ source.attribution || 'Source: MedlinePlus, NLM.' }}</span>
              <a
                v-if="source.url && source.url.startsWith('https://')"
                :href="source.url"
                target="_blank"
                rel="noopener noreferrer"
                class="source-link"
              >
                <span>打开 NLM 原始页面</span>
                <ExternalLink :size="13" />
              </a>
            </div>
          </article>
        </div>
      </template>

      <!-- ====================================================================
           TAB 2: AGENT EXECUTION FLOW (DAG) & CLAIM REVIEW / OMISSION INSPECTOR
           ==================================================================== -->
      <template v-else>
        <div v-if="!run" class="empty-inspector">
          <GitBranch :size="28" :stroke-width="1.4" />
          <h3>尚无运行记录</h3>
          <p>发起提问后，可在此查看任务依赖图、原子事实审核及省略原因。</p>
        </div>

        <div v-else class="trace-sections">
          <section class="answer-process-summary" aria-label="本轮回答概况">
            <h3>{{ answerSummary }}</h3>
            <dl>
              <div><dt>处理方式</dt><dd>{{ simulated ? '本地模拟 · ' : '' }}{{ run.response_origin === 'urgent_policy' ? '安全规则直接响应' : actualTasks.length ? `${actualTasks.length} 项任务${actualTasks.length > 1 ? '分工协作' : ''}` : '未记录任务分工' }}</dd></div>
              <div><dt>引用片段</dt><dd>{{ run.sources.length }} 条</dd></div>
              <div><dt>原文核对</dt><dd>{{ run.citation_support_status === 'model_reviewed' ? (simulated ? '模拟核对完成' : '模型核对完成') : formatLabel(run.reviewer_status || 'not_run') }}</dd></div>
            </dl>
            <p>点击正文引用角标可追溯对应指南文献。系统严格执行声明级核验，未获循证支持的内容不进入最终答复。</p>
            <p v-if="safeErrorInfo && run.safe_error_code !== 'REVIEW_SUPPORT_INCOMPLETE'" class="summary-limitation">{{ safeErrorInfo.title }}：{{ safeErrorInfo.detail }}</p>
          </section>
          <!-- SECTION A: Atomic Fact Review & Verification Trace -->
          <details
            ref="omittedSectionRef"
            tabindex="-1"
            class="trace-block trace-disclosure"
            :open="claimDetailsOpen"
            @toggle="claimDetailsOpen = ($event.target as HTMLDetailsElement).open"
            aria-label="原子事实审核与引用记录"
          >
            <summary><span>逐句事实审核与引文绑定记录</span><small>{{ run.sources?.length ? `${run.sources.length} 条依据` : '查看记录' }}</small><ChevronDown :size="14" class="disclosure-chevron" /></summary>
            <div class="disclosure-body">
            <div class="trace-block-header">
              <h4>
                {{
                  claimFilter === 'omitted'
                    ? `被省略的原稿断言（共 ${omittedClaimsCount} 条未进入最终回答）`
                    : '原子事实拆分与引用审核记录'
                }}
              </h4>
              <span class="task-summary-pill">
                {{ simulated ? '模拟审核' : formatLabel(run.reviewer_status || 'not_run') }}
              </span>
            </div>

            <!-- Filter Bar -->
            <div
              v-if="run.claim_reviews && run.claim_reviews.length"
              class="claim-filter-bar"
            >
              <button
                type="button"
                class="filter-pill-btn"
                :class="{ active: claimFilter === 'all' }"
                @click="emit('update:claimFilter', 'all')"
              >
                <span>全部审核记录 ({{ run.claim_reviews.length }})</span>
              </button>
              <button
                type="button"
                class="filter-pill-btn warn"
                :class="{ active: claimFilter === 'omitted' }"
                :disabled="omittedClaimsCount === 0"
                @click="emit('update:claimFilter', 'omitted')"
              >
                <Filter :size="12" />
                <span>仅看未进入回答的省略项 ({{ omittedClaimsCount }})</span>
              </button>
            </div>

            <div
              v-if="claimFilter === 'omitted' && omittedClaimsCount > 0"
              class="omitted-filter-banner"
            >
              <span>
                以下 {{ omittedClaimsCount }} 条原稿内容未通过引用或规则核对，<strong>未进入最终回答</strong>。这可能是证据不足，也可能是模型核对误判，不等于确定的医学纠错。
              </span>
              <button
                type="button"
                class="back-all-claims-btn"
                @click="emit('update:claimFilter', 'all')"
              >
                返回全部 {{ run.claim_reviews?.length || 0 }} 条审核记录
              </button>
            </div>

            <!-- Claim Review Cards -->
            <div
              v-if="filteredClaims.length"
              class="claim-list"
            >
              <article
                v-for="claim in filteredClaims"
                :key="claim.index"
                class="claim-card"
                :class="[
                  claim.support_status,
                  { 'excluded-claim-card': claim.support_status !== 'supported' },
                ]"
              >
                <div class="claim-head">
                  <span class="claim-idx mono">#{{ claim.index + 1 }}</span>
                  <span class="claim-kind">
                    {{ CLAIM_KIND_LABELS[claim.kind] || claim.kind }}
                  </span>
                  <span v-if="claim.review_round" class="claim-round mono">
                    第 {{ claim.review_round }} 轮判定
                  </span>
                  <span
                    class="claim-verdict"
                    :class="claim.support_status"
                  >
                    {{
                      claim.support_status === 'supported'
                        ? claim.kind === 'medical_fact'
                          ? '原文支持 · 已保留'
                          : '项目规则声明 · 已保留'
                        : `未进入最终回答 · ${
                            claim.support_status === 'partially_supported'
                              ? '仅部分支持'
                              : claim.support_status === 'contradicted' ? '与原文冲突' : '缺乏充分支持'
                          }`
                    }}
                  </span>
                </div>

                <!-- Excluded Draft Sentence Box -->
                <div
                  v-if="claim.support_status !== 'supported'"
                  class="excluded-sentence-box"
                >
                  <span class="excluded-tag">未进入最终回答的原稿句子</span>
                  <p class="excluded-text">“{{ claim.text }}”</p>
                </div>
                <p v-else class="claim-text">
                  {{ claim.text }}
                </p>

                <p class="claim-note">
                  <strong>{{ claim.support_status === 'supported' ? '核对说明：' : '未采用原因（模型判断）：' }}</strong>{{ claim.note }}
                </p>

                <div
                  v-if="claim.original_draft_spans && claim.original_draft_spans.length"
                  class="draft-origin-box"
                >
                  <span>第 1 轮首稿原句：</span>
                  <q>{{ claim.original_draft_spans[0]?.text }}</q>
                </div>

                <!-- Candidate / Bound Evidence Quotes -->
                <div
                  v-if="claim.evidence && claim.evidence.length"
                  class="claim-evidence-quotes"
                >
                  <span class="claim-ev-label">
                    {{
                      claim.support_status === 'supported'
                        ? `支持该句的 NLM 原文锚点 (${claim.evidence.length} 处)：`
                        : `核对时参考的原文 (${claim.evidence.length} 处；该原句未通过)：`
                    }}
                  </span>
                  <ul>
                    <li v-for="(ev, eIdx) in claim.evidence" :key="eIdx">
                      <q>{{ ev.quote }}</q>
                    </li>
                  </ul>
                </div>
              </article>
            </div>

            <!-- When Reviewer Blocked Output (review_trace) -->
            <div
              v-else-if="run.review_trace && run.review_trace.length"
              class="trace-packet-list"
            >
              <div v-for="trace in run.review_trace" :key="trace.round" class="round-box">
                <div class="round-box-header">
                  <strong>第 {{ trace.round }} 轮拦截快照（未发布初稿）</strong>
                  <span class="mono">{{ formatLabel(trace.status) }}</span>
                </div>
                <div class="trace-claims-preview">
                  <div v-for="c in trace.claims" :key="c.index" class="trace-claim-row">
                    <span class="mono">
                      [初稿句 #{{ c.index + 1 }} · 期望分类: {{ c.required_kind || '自适应' }}]
                    </span>
                    <span>{{ c.text }}</span>
                  </div>
                </div>
                <div v-if="trace.attempts && trace.attempts.length" class="trace-attempts">
                  <div v-for="(att, aIdx) in trace.attempts" :key="aIdx" class="attempt-item">
                    <div class="attempt-head mono">
                      <span>批次 #{{ att.batch }} ({{ att.claim_count }} 条)</span>
                      <span v-if="att.format_repair" class="repair-tag">格式修复重试</span>
                      <span>{{ formatLabel(att.status) }}</span>
                    </div>
                    <p v-if="att.diagnostic" class="task-error mono">
                      拦截诊断码: {{ att.diagnostic.code }}
                      <template v-if="att.diagnostic.global_claim_index !== undefined">
                        （触发位置：初稿句 #{{ att.diagnostic.global_claim_index + 1 }}）
                      </template>
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <p v-else class="muted-note">
              本轮未产生逐句引用审核记录（{{ formatLabel(run.reviewer_status || 'not_run') }}）。
            </p>
            </div>
          </details>

          <!-- SECTION B: Visual Execution Flow & Dynamic Task Dependency Graph (DAG) -->
          <details :key="`tasks-${run.run_id}`" class="trace-block trace-disclosure" aria-label="任务依赖与执行流程">
            <summary><span>专家分工与处理流程</span><small>{{ actualTasks.length }} 项任务</small><ChevronDown :size="14" class="disclosure-chevron" /></summary>
            <div class="disclosure-body">
            <p class="muted-note">查看谁负责查资料、解释问题，以及任务之间的先后依赖。</p>
            <div class="trace-block-header">
              <h4>执行流程与任务依赖图</h4>
              <span class="task-summary-pill">
                {{
                  run.response_origin === 'urgent_policy'
                    ? '安全规则直出 (0 任务)'
                    : `${actualTasks.length} 个实际任务 · ${
                        run.distinct_agent_count ?? actualTasks.length
                      } 个角色`
                }}
              </span>
            </div>

            <p class="plan-reason-box">
              <strong>规划说明：</strong>
              {{
                run.plan_reason ||
                (run.response_origin === 'urgent_policy'
                  ? '触发紧急医疗风险规则门禁，跳过任务规划与模型调用。'
                  : '由 LeadAgent 根据问题复杂度自动生成任务计划（不固定拆分为三个专家）。')
              }}
            </p>

            <!-- Visual Stage & Task Dependency Diagram -->
            <div class="dag-flow-diagram" role="list" aria-label="执行阶段与任务依赖">
              <!-- Node 1: Entry & Gate -->
              <div class="dag-stage-node completed" role="listitem">
                <span class="dag-node-badge">阶段 1</span>
                <div class="dag-node-main">
                  <strong>安全规则门禁与路由</strong>
                  <small>
                    {{
                      run.response_origin === 'urgent_policy'
                        ? '命中紧急风险规则 → 直接输出就医提示'
                        : `plan_status: ${run.plan_status}`
                    }}
                  </small>
                </div>
              </div>

              <!-- Wave Nodes: Actual Tasks (1 or Multi-task DAG) -->
              <template v-if="taskWaves.length">
                <div
                  v-for="wave in taskWaves"
                  :key="wave.waveIndex"
                  class="dag-wave-group"
                  role="listitem"
                >
                  <div class="dag-connector">
                    <ArrowDown :size="14" />
                    <span>{{ wave.title }}</span>
                  </div>
                  <div
                    class="dag-wave-cards"
                    :class="{ 'multi-cols': wave.tasks.length > 1 }"
                  >
                    <article
                      v-for="task in wave.tasks"
                      :key="task.task_id"
                      class="dag-task-card"
                      :class="task.status"
                    >
                      <div class="dag-task-top">
                        <strong class="mono">{{ task.task_id }}</strong>
                        <span class="task-status-tag" :class="task.status">
                          {{ formatLabel(task.status) }}
                        </span>
                      </div>
                      <div class="dag-task-role">
                        {{ formatAgentRole(task.agent_id).name }}
                      </div>
                      <p v-if="task.description" class="dag-task-desc">
                        {{ task.description }}
                      </p>
                      <div class="dag-task-meta mono">
                        <span>
                          模型: {{ formatCallCount(task.model_calls, '次', simulated) }} · 工具:
                          {{ formatCallCount(task.tool_calls, '次', simulated) }}
                        </span>
                        <span v-if="task.depends_on && task.depends_on.length" class="dep-pill">
                          依赖前置: {{ task.depends_on.join(', ') }}
                        </span>
                        <span v-else class="dep-pill">无前置依赖</span>
                      </div>
                      <p v-if="task.safe_error_code" class="task-error mono">
                        诊断码: {{ task.safe_error_code }}
                      </p>
                    </article>
                  </div>
                </div>
              </template>

              <!-- Final Node: Review & Persist -->
              <div class="dag-connector">
                <ArrowDown :size="14" />
                <span>审核与结果持久化</span>
              </div>
              <div
                class="dag-stage-node"
                :class="run.result_status || run.run_status"
                role="listitem"
              >
                <span class="dag-node-badge">终态</span>
                <div class="dag-node-main">
                  <strong>
                    {{
                      run.response_origin === 'urgent_policy'
                        ? '规则直出完成（跳过模型审核）'
                        : `引用审核: ${formatLabel(run.reviewer_status || 'not_run')} · 最终状态: ${formatLabel(
                            run.result_status || run.run_status,
                          )}`
                    }}
                  </strong>
                  <small class="mono">
                    总模型调用: {{ formatCallCount(run.model_calls, '次', simulated) }} · 总工具调用:
                    {{ formatCallCount(run.tool_calls, '次', simulated) }} · 改写次数:
                    {{ run.review_rewrite_count ?? 0 }}
                  </small>
                </div>
              </div>
            </div>
            </div>
          </details>

          <!-- SECTION C: Technical Diagnostics, Node Events & Provider Log (Secondary Collapsible) -->
          <section class="trace-block">
            <details :key="`dev-${run.run_id}`" class="secondary-trace-details trace-disclosure">
              <summary>
                <span>开发者诊断</span><small>节点、调用与上下文</small><ChevronDown :size="14" class="disclosure-chevron" />
              </summary>

              <div class="secondary-trace-body">
                <div
                  v-if="safeErrorInfo"
                  class="diagnostic-callout"
                  :class="run.result_status || run.run_status"
                >
                  <AlertTriangle :size="16" />
                  <div>
                    <strong>{{ safeErrorInfo.title }}</strong>
                    <p>{{ safeErrorInfo.detail }}</p>
                  </div>
                </div>

                <dl class="kv-grid mono">
                  <div>
                    <dt>run_id</dt>
                    <dd>{{ run.run_id }}</dd>
                  </div>
                  <div>
                    <dt>request_id</dt>
                    <dd>{{ run.request_id }}</dd>
                  </div>
                  <div>
                    <dt>mode / profile</dt>
                    <dd>{{ run.mode }} / {{ run.knowledge_profile || 'default' }}</dd>
                  </div>
                  <div>
                    <dt>safe_error_code</dt>
                    <dd>{{ run.safe_error_code || run.reviewer_error_code || '无' }}</dd>
                  </div>
                </dl>

                <div v-if="providerCalls.length" class="provider-list">
                  <h5>Provider 调用记录</h5>
                  <div v-for="(call, cIdx) in providerCalls" :key="cIdx" class="provider-item">
                    <div class="provider-main">
                      <strong class="mono">{{ call.provider }}</strong>
                      <span>{{ call.operation }}</span>
                    </div>
                    <div class="provider-metrics mono">
                      <span
                        class="http-badge"
                        :class="{
                          ok: call.http_status === 200,
                          err: call.http_status && call.http_status >= 400,
                        }"
                      >
                        HTTP {{ call.http_status ?? '未记录' }}
                      </span>
                      <span>
                        耗时:
                        {{
                          typeof call.elapsed_seconds === 'number'
                            ? `${call.elapsed_seconds.toFixed(2)}s`
                            : '未知'
                        }}
                      </span>
                      <span>
                        Tokens:
                        {{
                          typeof call.usage?.total_tokens === 'number'
                            ? call.usage.total_tokens
                            : '未知'
                        }}
                      </span>
                      <span v-if="call.safe_error_code" class="err-code">
                        {{ call.safe_error_code }}
                      </span>
                    </div>
                  </div>
                </div>

                <div v-if="events.length" class="event-timeline">
                  <h5>LangGraph 节点事件序列 ({{ events.length }})</h5>
                  <ol>
                    <li v-for="(ev, eIdx) in events" :key="eIdx">
                      <span class="ev-dot" :class="ev.status"></span>
                      <span class="ev-name">
                        {{ formatStage(ev.stage) }}
                        <strong v-if="ev.task_id" class="mono"> · {{ ev.task_id }}</strong>
                      </span>
                      <span class="ev-status">{{ formatLabel(ev.status) }}</span>
                    </li>
                  </ol>
                </div>

                <div v-if="sessionSummary && sessionSummary.content" class="summary-preview-box">
                  <h5>
                    会话增量摘要 (覆盖至 seq #{{ sessionSummary.covered_until_seq }} · v{{
                      sessionSummary.version
                    }})
                  </h5>
                  <p>{{ sessionSummary.content }}</p>
                </div>
              </div>
            </details>
          </section>
        </div>
      </template>
    </div>
  </aside>
</template>
