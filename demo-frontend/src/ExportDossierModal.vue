<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import {
  AlertTriangle,
  BookOpen,
  Check,
  CheckCircle2,
  Copy,
  FileText,
  Printer,
  ShieldAlert,
  ShieldCheck,
  X,
} from 'lucide-vue-next'
import type { ExecutionEventItem, ProviderCallItem, RunOut, SourceItem } from './types'
import { resolveAnswerClaimSegments, summarizeClaims, formatLabel } from './medicalLabels'
import { focusInitialElement, trapFocusOnTab } from './focusTrap'

const props = defineProps<{
  open: boolean
  sessionTitle?: string
  question: string
  answer: string | null
  run: RunOut | null
  events?: ExecutionEventItem[]
  providerCalls?: ProviderCallItem[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'showToast', message: string): void
}>()

const modalRef = ref<HTMLElement | null>(null)
const copied = ref(false)
let copyTimer: ReturnType<typeof setTimeout> | undefined

const claimMapping = computed(() =>
  resolveAnswerClaimSegments(props.run, props.answer ?? props.run?.answer ?? ''),
)

const claimStats = computed(() => summarizeClaims(props.run?.claim_reviews))

const generatedDate = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
    d.getDate(),
  ).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(
    d.getMinutes(),
  ).padStart(2, '0')}`
})

// Unified Dossier Report Model: single source of truth for both Markdown and HTML view
const reportModel = computed(() => {
  const r = props.run

  // Run status and review analysis
  const runStatus = r?.run_status || 'unknown'
  const resultStatus = r?.result_status || 'unknown'
  const reviewerStatus = r?.reviewer_status || 'not_run'
  const safeErrorCode = r?.safe_error_code || r?.reviewer_error_code || null
  const graphVersion = r?.graph_version ?? 3
  const runMode = r?.mode || 'offline_fake'

  let reviewVerdictText = '审核未执行 / 未记录'
  let reviewPassed = false

  if (reviewerStatus === 'failed' || safeErrorCode === 'REVIEW_FAILED') {
    reviewVerdictText = '审核拦截：本轮初稿未通过文献引用/项目规则核验，已被系统拦截，未进入最终回答'
    reviewPassed = false
  } else if (reviewerStatus === 'completed' || reviewerStatus === 'passed') {
    if (resultStatus === 'partial') {
      reviewVerdictText = '部分核验：部分初稿内容因缺乏充分文献依据被省略'
      reviewPassed = true
    } else {
      reviewVerdictText = '模型核验完成：已完成声明级原子事实与文献比对'
      reviewPassed = true
    }
  } else if (reviewerStatus === 'skipped_policy') {
    reviewVerdictText = '安全规则出口：触发预设医疗安全门禁，直接输出就医提示'
    reviewPassed = true
  } else if (runStatus === 'failed') {
    reviewVerdictText = '执行失败 / 未能完成'
    reviewPassed = false
  }

  // Structured Claims
  const claims = (r?.claim_reviews || []).map((c, idx) => {
    const isPolicy = c.kind === 'policy_or_scope'
    const isMedicalFact = c.kind === 'medical_fact'
    const enteredFinalAnswer = c.support_status === 'supported'

    let verdictLabel = '未知状态'
    if (isPolicy) {
      verdictLabel = '项目规则声明 · 已保留'
    } else if (c.support_status === 'supported') {
      verdictLabel = '文献支持 · 已保留'
    } else if (c.support_status === 'partially_supported') {
      verdictLabel = '仅部分支持 · 未纳入回答'
    } else if (c.support_status === 'contradicted') {
      verdictLabel = '与文献冲突 · 未纳入回答'
    } else {
      verdictLabel = '缺乏充分支持 · 未纳入回答'
    }

    const quotes = (c.evidence || []).map(e => e.quote).filter(Boolean)

    return {
      index: idx + 1,
      text: c.text,
      kind: c.kind,
      kindLabel: isPolicy ? '项目规则与范围' : (isMedicalFact ? '医学事实' : c.kind),
      supportStatus: c.support_status,
      verdictLabel,
      enteredFinalAnswer,
      evidenceQuotes: quotes,
      note: c.note || '',
      reviewRound: c.review_round || 1,
    }
  })

  // Grounding Sources
  const sources = (r?.sources || []).map((src, idx) => {
    const isPubMed = src.source === 'pubmed'
    const docIdDisplay = isPubMed
      ? `PMID: ${src.document_id || src.id}`
      : `文档标识: ${src.document_id || src.id}`

    const offsetsStr =
      typeof src.start === 'number' && typeof src.end === 'number'
        ? `[${src.start}..${src.end}] (${src.end - src.start} 字符)`
        : null

    const spans = (src.source_spans || []).map((sp, sIdx) => ({
      index: sIdx + 1,
      quote: sp.quote,
      offsets:
        typeof sp.start === 'number' && typeof sp.end === 'number'
          ? `[${sp.start}..${sp.end}] (${sp.quote.length} 字符)`
          : null,
    }))

    return {
      index: idx + 1,
      id: src.id,
      title: src.title || src.document_id || src.id,
      publisher: src.publisher || (isPubMed ? 'U.S. National Library of Medicine (PubMed)' : 'NLM / MedlinePlus 快照'),
      isPubMed,
      documentId: src.document_id || src.id,
      docIdDisplay,
      section: src.section || null,
      sha256: src.source_sha256 || null,
      version: src.version || null,
      editorialContent: src.content || null,
      editorialOffsets: offsetsStr,
      spans,
    }
  })

  // Observability & Auditing
  const modelCallsDisplay = typeof r?.model_calls === 'number' ? `${r.model_calls} 次` : '未知 / 未记录'
  const toolCallsDisplay = typeof r?.tool_calls === 'number' ? `${r.tool_calls} 次` : '未知 / 未记录'
  const rewriteCountDisplay = typeof r?.review_rewrite_count === 'number' ? `${r.review_rewrite_count} 轮` : '未知 / 未记录'

  const providerCalls = (props.providerCalls || []).map(p => {
    const httpDisplay = p.http_status != null ? `HTTP ${p.http_status}` : 'HTTP 未知'
    const elapsedDisplay = typeof p.elapsed_seconds === 'number' ? `${p.elapsed_seconds.toFixed(2)}s` : '未知'
    const tokensDisplay = typeof p.usage?.total_tokens === 'number' ? `${p.usage.total_tokens} tokens` : '未知'
    return {
      provider: p.provider,
      operation: p.operation,
      httpDisplay,
      elapsedDisplay,
      tokensDisplay,
      status: p.status,
      safeErrorCode: p.safe_error_code || null,
    }
  })

  return {
    title: '医疗科研与临床决策循证专报 (Clinical Evidence Dossier)',
    generatedAt: generatedDate.value,
    sessionTitle: props.sessionTitle || '循证医学咨询会话',
    runId: r?.run_id || 'N/A',
    graphVersion,
    runMode,
    runStatus,
    resultStatus,
    reviewerStatus,
    clinicalReview: '未执行 (Not Run)',
    safeErrorCode,
    reviewVerdictText,
    reviewPassed,
    question: props.question || '（无问题记录）',
    answer: props.answer || null,
    claims,
    sources,
    modelCallsDisplay,
    toolCallsDisplay,
    rewriteCountDisplay,
    planReason: r?.plan_reason || (r?.response_origin === 'urgent_policy' ? '命中紧急安全规则门禁' : '单任务路由 / 动态任务规划'),
    providerCalls,
    disclaimer:
      '【科研与临床使用免责声明】：本专报由 Medical-Agent 研究原型系统自动编排生成，旨在为医学健康研究与文献事实溯源提供实验参考。系统基于分块 RAG 检索与声明级原子事实核验，医学专业复核当前标记为未执行。本报告绝不构成确诊、治疗方案或处方建议，不具备临床生产效力。任何临床决策必须由具备资质的执业医师面诊指导。',
  }
})

// Markdown Export generated strictly from reportModel
const markdownReport = computed(() => {
  const m = reportModel.value
  const lines: string[] = []

  lines.push(`# ${m.title}`)
  lines.push(`- **生成时间**：${m.generatedAt}`)
  lines.push(`- **所属会话**：${m.sessionTitle}`)
  lines.push(`- **运行标识 (Run ID)**：\`${m.runId}\``)
  lines.push(`- **工作流版本**：LangGraph DAG v${m.graphVersion} (运行模式: \`${m.runMode}\`)`)
  lines.push(`- **运行状态**：\`${m.runStatus}\` / \`${m.resultStatus}\``)
  lines.push(`- **模型引用核对**：\`${m.reviewerStatus}\` (${m.reviewVerdictText})`)
  lines.push(`- **医学专业复核**：${m.clinicalReview}`)
  if (m.safeErrorCode) {
    lines.push(`- **诊断拦截码**：\`${m.safeErrorCode}\``)
  }
  lines.push('\n---\n')

  lines.push('## 一、咨询临床问题')
  lines.push(`> ${m.question}`)
  lines.push('')

  lines.push('## 二、智能体综合结论与机制解析')
  if (m.answer) {
    lines.push(m.answer)
  } else {
    lines.push('*（本轮未产生有效回答正文或已被审核拦截）*')
  }
  lines.push('')

  lines.push('## 三、细粒度声明级事实核查矩阵 (Claim-Level Grounding)')
  if (m.claims.length) {
    lines.push('| 序号 | 声明原句 | 分类 | 核验判定 | 纳入最终回答 | 原文依据锚点 | 核对说明 |')
    lines.push('| :--- | :--- | :--- | :--- | :--- | :--- | :--- |')
    m.claims.forEach(c => {
      const cleanText = c.text.replace(/\|/g, '\\|').replace(/\n/g, ' ')
      const cleanNote = c.note.replace(/\|/g, '\\|').replace(/\n/g, ' ') || '—'
      const enteredStr = c.enteredFinalAnswer ? '是' : '否（已拦截）'
      const evStr = c.evidenceQuotes.length ? `${c.evidenceQuotes.length} 处` : '无'
      lines.push(`| #${c.index} | ${cleanText} | ${c.kindLabel} | ${c.verdictLabel} | ${enteredStr} | ${evStr} | ${cleanNote} |`)
    })
  } else {
    lines.push('*本轮未产生独立的逐事实审核记录。*')
  }
  lines.push('')

  lines.push('## 四、参考文献与权威数据源溯源 (Grounding Sources)')
  if (m.sources.length) {
    m.sources.forEach(src => {
      lines.push(`### [文献 ${src.index}] ${src.title}`)
      lines.push(`- **发布机构**：${src.publisher}`)
      lines.push(`- **${src.isPubMed ? 'PubMed 索引 (PMID)' : '文献编号 (Document ID)'}**：\`${src.documentId}\``)
      if (src.section) lines.push(`- **所属章节**：${src.section}`)
      if (src.version) lines.push(`- **资料版本**：${src.version}`)
      if (src.sha256) lines.push(`- **SHA256 校验和**：\`${src.sha256}\``)
      if (src.editorialOffsets) lines.push(`- **摘述字符区间**：\`${src.editorialOffsets}\``)
      if (src.editorialContent) lines.push(`- **核心中文摘述**：${src.editorialContent}`)
      if (src.spans.length) {
        lines.push('- **英文权威证据锚点**：')
        src.spans.forEach(sp => {
          lines.push(`  > [${sp.index}] "${sp.quote}" ${sp.offsets ? `(区间: ${sp.offsets})` : ''}`)
        })
      }
      lines.push('')
    })
  } else {
    lines.push('*本轮未检索或未绑定外部文献快照。*')
  }

  lines.push('## 五、多智能体协同与可观测性审计 (Observability Audit)')
  lines.push(`- **任务规划逻辑**：${m.planReason}`)
  lines.push(`- **模型调用总计**：${m.modelCallsDisplay}`)
  lines.push(`- **工具检索调用**：${m.toolCallsDisplay}`)
  lines.push(`- **审查改写轮次**：${m.rewriteCountDisplay}`)
  if (m.providerCalls.length) {
    lines.push('- **服务调用与耗时记录**：')
    m.providerCalls.forEach(p => {
      lines.push(`  - \`${p.provider}\` (${p.operation}) -> ${p.httpDisplay} | 耗时: ${p.elapsedDisplay} | 消耗: ${p.tokensDisplay} ${p.safeErrorCode ? `[错误: ${p.safeErrorCode}]` : ''}`)
    })
  }
  lines.push('')

  lines.push('## 六、严谨科研与临床使用免责声明')
  lines.push(`> ${m.disclaimer}`)

  return lines.join('\n')
})

async function copyMarkdown() {
  try {
    await navigator.clipboard.writeText(markdownReport.value)
    copied.value = true
    emit('showToast', '循证专报 Markdown 已成功复制到剪贴板！')
    clearTimeout(copyTimer)
    copyTimer = setTimeout(() => {
      copied.value = false
    }, 2500)
  } catch {
    emit('showToast', '复制失败，请手动全选复制。')
  }
}

function printReport() {
  window.print()
}

watch(
  () => props.open,
  async isOpen => {
    if (isOpen) {
      await nextTick()
      focusInitialElement(modalRef.value, '.close-btn')
    }
  },
)

function onKeydown(e: KeyboardEvent) {
  if (!props.open) return
  if (e.key === 'Escape') {
    e.stopPropagation()
    emit('close')
  } else if (e.key === 'Tab' && modalRef.value) {
    trapFocusOnTab(e, modalRef.value)
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown, true)
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="dossier-modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label="医疗循证科研专报导出预览"
      @click="emit('close')"
    >
      <div
        ref="modalRef"
        class="dossier-modal-panel"
        tabindex="-1"
        @click.stop
      >
        <!-- Modal Top Bar (Mobile Responsive with safe viewport sizing) -->
        <header class="dossier-modal-header">
          <div class="header-branding">
            <span class="dossier-badge"><FileText :size="16" /></span>
            <div class="header-text">
              <h3>医疗循证科研专报</h3>
              <p>研究原型导出 · 声明级溯源 · 文献锚点 · 调用链审计</p>
            </div>
          </div>
          <div class="header-actions">
            <button
              type="button"
              class="dossier-action-btn primary"
              title="复制 Markdown 文本"
              aria-label="复制 Markdown"
              @click="copyMarkdown"
            >
              <Check v-if="copied" :size="14" />
              <Copy v-else :size="14" />
              <span class="btn-text">{{ copied ? '已复制' : '复制 Markdown' }}</span>
            </button>
            <button
              type="button"
              class="dossier-action-btn secondary"
              title="调起打印或保存为 PDF"
              aria-label="打印 / 导出 PDF"
              @click="printReport"
            >
              <Printer :size="14" />
              <span class="btn-text">打印 / 导出 PDF</span>
            </button>
            <button
              type="button"
              class="close-btn"
              aria-label="关闭专报窗口"
              @click="emit('close')"
            >
              <X :size="18" />
            </button>
          </div>
        </header>

        <!-- Printable Document Body -->
        <div class="dossier-printable-area">
          <article class="dossier-document">
            <!-- Header Block -->
            <div class="dossier-doc-header">
              <div class="doc-title-row">
                <h2>{{ reportModel.title }}</h2>
                <span
                  class="verdict-banner-tag"
                  :class="reportModel.reviewPassed ? 'passed' : 'failed'"
                >
                  {{ reportModel.reviewPassed ? '核验通过' : '未通过 / 拦截' }}
                </span>
              </div>
              <div class="doc-meta-grid">
                <div><span>生成时间：</span><strong>{{ reportModel.generatedAt }}</strong></div>
                <div><span>所属会话：</span><strong>{{ reportModel.sessionTitle }}</strong></div>
                <div><span>运行标识：</span><code class="mono">{{ reportModel.runId }}</code></div>
                <div><span>工作流版本：</span><strong>LangGraph DAG v{{ reportModel.graphVersion }} ({{ reportModel.runMode }})</strong></div>
                <div><span>运行状态：</span><span class="mono">{{ reportModel.runStatus }} / {{ reportModel.resultStatus }}</span></div>
                <div><span>专业医学复核：</span><strong class="warn-text">{{ reportModel.clinicalReview }}</strong></div>
              </div>

              <div
                class="audit-status-strip"
                :class="reportModel.reviewPassed ? 'ok' : 'err'"
              >
                <ShieldCheck v-if="reportModel.reviewPassed" :size="15" />
                <ShieldAlert v-else :size="15" />
                <span>{{ reportModel.reviewVerdictText }}</span>
                <span v-if="reportModel.safeErrorCode" class="mono safe-code-badge">
                  [{{ reportModel.safeErrorCode }}]
                </span>
              </div>
            </div>

            <!-- Question Block -->
            <section class="doc-section">
              <h4 class="doc-section-title">一、咨询临床问题</h4>
              <div class="doc-question-card">
                <strong>临床提问：</strong>
                <p>{{ reportModel.question }}</p>
              </div>
            </section>

            <!-- Synthesis & Answer -->
            <section class="doc-section">
              <h4 class="doc-section-title">二、智能体综合结论与机制解析</h4>
              <div v-if="reportModel.answer" class="doc-answer-body">
                <p v-for="(p, pIdx) in reportModel.answer.split('\n\n')" :key="pIdx">{{ p }}</p>
              </div>
              <div v-else class="doc-empty-answer">
                <AlertTriangle :size="16" />
                <span>本轮未产生有效回答正文或初稿因未通过核验被完全拦截。</span>
              </div>
            </section>

            <!-- Verification Table -->
            <section v-if="reportModel.claims.length" class="doc-section">
              <h4 class="doc-section-title">
                三、细粒度声明级事实核查矩阵
                <small>(共 {{ reportModel.claims.length }} 条原子声明，支持率: {{ claimStats.total ? Math.round((claimStats.supported / claimStats.total) * 100) : 100 }}%)</small>
              </h4>
              <div class="doc-table-wrapper">
                <table class="dossier-table">
                  <thead>
                    <tr>
                      <th style="width: 44px">序号</th>
                      <th>声明原句</th>
                      <th style="width: 100px">分类</th>
                      <th style="width: 130px">核验判定</th>
                      <th style="width: 80px">进入回答</th>
                      <th style="width: 80px">证据锚点</th>
                      <th>审查说明</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="claim in reportModel.claims"
                      :key="claim.index"
                      :class="claim.supportStatus"
                    >
                      <td class="mono">#{{ claim.index }}</td>
                      <td class="claim-text-cell">{{ claim.text }}</td>
                      <td class="mono">{{ claim.kindLabel }}</td>
                      <td>
                        <span class="doc-verdict-pill" :class="claim.supportStatus">
                          {{ claim.verdictLabel }}
                        </span>
                      </td>
                      <td>
                        <span class="entered-badge" :class="claim.enteredFinalAnswer ? 'yes' : 'no'">
                          {{ claim.enteredFinalAnswer ? '是' : '否' }}
                        </span>
                      </td>
                      <td class="mono">{{ claim.evidenceQuotes.length ? `${claim.evidenceQuotes.length} 处` : '—' }}</td>
                      <td class="note-cell">{{ claim.note || '—' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            <!-- Sources List with Provenance -->
            <section v-if="reportModel.sources.length" class="doc-section">
              <h4 class="doc-section-title">四、权威参考文献与引文锚点溯源 (共 {{ reportModel.sources.length }} 份资料)</h4>
              <div class="doc-sources-list">
                <div
                  v-for="src in reportModel.sources"
                  :key="src.index"
                  class="doc-source-item"
                >
                  <div class="source-item-head">
                    <span class="source-idx">[{{ src.index }}]</span>
                    <strong>{{ src.title }}</strong>
                    <span class="source-pub">{{ src.publisher }}</span>
                  </div>
                  <div class="source-tech-meta mono">
                    <span>{{ src.docIdDisplay }}</span>
                    <span v-if="src.version">版本: {{ src.version }}</span>
                    <span v-if="src.sha256" class="hash-tag">SHA256: {{ src.sha256.slice(0, 16) }}...</span>
                    <span v-if="src.editorialOffsets">摘述区间: {{ src.editorialOffsets }}</span>
                  </div>
                  <p v-if="src.editorialContent" class="source-editorial"><strong>中文摘述：</strong>{{ src.editorialContent }}</p>
                  <div v-if="src.spans.length" class="source-quotes">
                    <span class="quote-label">绑定的英文证据锚点片段：</span>
                    <ul>
                      <li v-for="sp in src.spans" :key="sp.index">
                        <q>{{ sp.quote }}</q>
                        <span v-if="sp.offsets" class="mono span-offset-pill">{{ sp.offsets }}</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </section>

            <!-- Observability & Governance -->
            <section class="doc-section">
              <h4 class="doc-section-title">五、系统审计与多智能体执行指标</h4>
              <div class="doc-audit-grid">
                <div class="audit-card">
                  <span>模型总调用</span>
                  <strong>{{ reportModel.modelCallsDisplay }}</strong>
                </div>
                <div class="audit-card">
                  <span>工具/检索调用</span>
                  <strong>{{ reportModel.toolCallsDisplay }}</strong>
                </div>
                <div class="audit-card">
                  <span>审查改写轮次</span>
                  <strong>{{ reportModel.rewriteCountDisplay }}</strong>
                </div>
                <div class="audit-card">
                  <span>规划与路由</span>
                  <strong>{{ reportModel.planReason }}</strong>
                </div>
              </div>

              <div v-if="reportModel.providerCalls.length" class="provider-audit-box">
                <h5>模型与服务接口调用明细</h5>
                <div class="provider-audit-list">
                  <div
                    v-for="(p, pIdx) in reportModel.providerCalls"
                    :key="pIdx"
                    class="provider-audit-row mono"
                  >
                    <span class="p-name">{{ p.provider }} ({{ p.operation }})</span>
                    <span class="p-status">{{ p.httpDisplay }}</span>
                    <span class="p-sec">耗时: {{ p.elapsedDisplay }}</span>
                    <span class="p-tok">消耗: {{ p.tokensDisplay }}</span>
                    <span v-if="p.safeErrorCode" class="p-err">错误: {{ p.safeErrorCode }}</span>
                  </div>
                </div>
              </div>
            </section>

            <!-- Legal Disclaimer Footer -->
            <footer class="doc-footer">
              <ShieldCheck :size="16" />
              <p>{{ reportModel.disclaimer }}</p>
            </footer>
          </article>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.dossier-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal, 100);
  background: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  overflow-y: auto;
  box-sizing: border-box;
}

.dossier-modal-panel {
  background: var(--surface-card, #ffffff);
  border: 1px solid var(--border-soft, #e2e8f0);
  border-radius: var(--radius-xl, 16px);
  width: 100%;
  max-width: min(920px, calc(100vw - 2rem));
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  overflow: hidden;
  outline: none;
  box-sizing: border-box;
}

.dossier-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1.25rem;
  border-bottom: 1px solid var(--border-soft, #e2e8f0);
  background: var(--surface-page, #f8fafc);
  flex-wrap: wrap;
  gap: 0.6rem;
  box-sizing: border-box;
  width: 100%;
}

.header-branding {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  min-width: 0;
  flex: 1 1 auto;
}

.dossier-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: #eff6ff;
  color: var(--brand-primary, #002fa7);
  flex-shrink: 0;
}

.header-text {
  min-width: 0;
}

.header-text h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-heading, #0f172a);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-text p {
  margin: 0.1rem 0 0 0;
  font-size: 0.72rem;
  color: var(--text-muted, #64748b);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-shrink: 0;
}

.dossier-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.4rem 0.75rem;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid transparent;
  white-space: nowrap;
}

.dossier-action-btn.primary {
  background: var(--brand-primary, #002fa7);
  color: #ffffff;
}
.dossier-action-btn.primary:hover {
  background: #002482;
}

.dossier-action-btn.secondary {
  background: #ffffff;
  border-color: var(--border-soft, #cbd5e1);
  color: var(--text-body, #334155);
}
.dossier-action-btn.secondary:hover {
  background: #f1f5f9;
}

.close-btn {
  background: transparent;
  border: none;
  color: var(--text-muted, #64748b);
  padding: 0.35rem;
  border-radius: 6px;
  cursor: pointer;
  flex-shrink: 0;
}
.close-btn:hover {
  background: #e2e8f0;
  color: var(--text-heading, #0f172a);
}

.dossier-printable-area {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  background: #fdfdfd;
  box-sizing: border-box;
}

.dossier-document {
  max-width: 820px;
  margin: 0 auto;
  background: #ffffff;
  padding: 1.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  box-sizing: border-box;
}

.dossier-doc-header {
  border-bottom: 2px solid var(--brand-primary, #002fa7);
  padding-bottom: 1.25rem;
  margin-bottom: 1.5rem;
}

.doc-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.doc-title-row h2 {
  margin: 0;
  font-size: 1.35rem;
  color: #0f172a;
}

.verdict-banner-tag {
  padding: 0.25rem 0.65rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 700;
}
.verdict-banner-tag.passed {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
}
.verdict-banner-tag.failed {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.doc-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem 1.5rem;
  font-size: 0.8rem;
  color: #475569;
}

.audit-status-strip {
  margin-top: 0.85rem;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  font-size: 0.82rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
}
.audit-status-strip.ok {
  background: #f0fdf4;
  color: #166534;
  border: 1px solid #bbf7d0;
}
.audit-status-strip.err {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}
.safe-code-badge {
  font-size: 0.75rem;
  background: rgba(0, 0, 0, 0.06);
  padding: 1px 4px;
  border-radius: 3px;
}

.warn-text {
  color: #b45309;
}

.doc-section {
  margin-bottom: 1.75rem;
}

.doc-section-title {
  margin: 0 0 0.75rem 0;
  font-size: 1rem;
  color: #1e293b;
  border-left: 3px solid var(--brand-primary, #002fa7);
  padding-left: 0.6rem;
}
.doc-section-title small {
  font-size: 0.78rem;
  color: #64748b;
  font-weight: normal;
  margin-left: 0.4rem;
}

.doc-question-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.85rem 1rem;
  font-size: 0.9rem;
}
.doc-question-card strong {
  color: var(--brand-primary, #002fa7);
  margin-right: 0.4rem;
}
.doc-question-card p {
  display: inline;
  margin: 0;
  color: #1e293b;
}

.doc-answer-body {
  font-size: 0.9rem;
  line-height: 1.7;
  color: #1e293b;
}
.doc-answer-body p {
  margin: 0 0 0.75rem 0;
}

.doc-empty-answer {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  padding: 0.85rem 1rem;
  color: #991b1b;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.doc-table-wrapper {
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}

.dossier-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.78rem;
}
.dossier-table th,
.dossier-table td {
  padding: 0.55rem 0.65rem;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
}
.dossier-table th {
  background: #f8fafc;
  font-weight: 600;
  color: #475569;
}
.claim-text-cell {
  font-weight: 500;
  color: #0f172a;
}
.doc-verdict-pill {
  display: inline-block;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
}
.doc-verdict-pill.supported {
  background: #ecfdf5;
  color: #047857;
}
.doc-verdict-pill.partially_supported {
  background: #fffbeb;
  color: #b45309;
}
.doc-verdict-pill.contradicted,
.doc-verdict-pill.omitted {
  background: #fef2f2;
  color: #b91c1c;
}

.entered-badge {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 3px;
}
.entered-badge.yes {
  background: #ecfdf5;
  color: #047857;
}
.entered-badge.no {
  background: #f1f5f9;
  color: #64748b;
}

.note-cell {
  color: #64748b;
}

.doc-sources-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.doc-source-item {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.85rem 1rem;
  background: #fafafa;
}
.source-item-head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  margin-bottom: 0.3rem;
  flex-wrap: wrap;
}
.source-idx {
  font-weight: 700;
  color: var(--brand-primary, #002fa7);
}
.source-pub {
  color: #64748b;
  font-size: 0.75rem;
  margin-left: auto;
}
.source-tech-meta {
  font-size: 0.74rem;
  color: #64748b;
  display: flex;
  gap: 0.75rem;
  margin-bottom: 0.4rem;
  flex-wrap: wrap;
}
.hash-tag {
  background: #f1f5f9;
  padding: 1px 4px;
  border-radius: 3px;
}
.source-editorial {
  margin: 0.25rem 0;
  font-size: 0.82rem;
  color: #334155;
}
.source-quotes {
  margin-top: 0.4rem;
  font-size: 0.78rem;
}
.quote-label {
  color: #64748b;
  font-weight: 600;
}
.source-quotes ul {
  margin: 0.2rem 0 0 1rem;
  padding: 0;
  color: #475569;
}
.source-quotes li {
  margin-bottom: 0.3rem;
}
.span-offset-pill {
  font-size: 0.7rem;
  color: #64748b;
  margin-left: 0.4rem;
}

.doc-audit-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.65rem;
}
.audit-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.65rem;
  text-align: center;
}
.audit-card span {
  display: block;
  font-size: 0.72rem;
  color: #64748b;
  margin-bottom: 0.2rem;
}
.audit-card strong {
  font-size: 0.88rem;
  color: #0f172a;
}

.provider-audit-box {
  margin-top: 1rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.75rem;
  background: #f8fafc;
}
.provider-audit-box h5 {
  margin: 0 0 0.5rem 0;
  font-size: 0.8rem;
  color: #475569;
}
.provider-audit-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.provider-audit-row {
  display: flex;
  font-size: 0.74rem;
  gap: 0.75rem;
  color: #334155;
  flex-wrap: wrap;
}
.p-name {
  font-weight: 600;
}
.p-status {
  color: #059669;
}
.p-err {
  color: #dc2626;
}

.doc-footer {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px dashed #cbd5e1;
  display: flex;
  gap: 0.6rem;
  color: #64748b;
  font-size: 0.74rem;
  line-height: 1.5;
}
.doc-footer p {
  margin: 0;
}

/* Mobile Safe Layout Fix */
@media (max-width: 640px) {
  .dossier-modal-backdrop {
    padding: 0;
  }
  .dossier-modal-panel {
    max-height: 100vh;
    height: 100vh;
    border-radius: 0;
    max-width: 100vw;
  }
  .dossier-action-btn .btn-text {
    display: none;
  }
  .doc-meta-grid {
    grid-template-columns: 1fr;
  }
  .doc-audit-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>

<!-- Global Un-scoped Print Stylesheet to hide app backdrop and print ONLY the dossier -->
<style>
@media print {
  /* Hide the main app root and any overlay backdrop */
  #app,
  .med-app-root,
  .mobile-backdrop {
    display: none !important;
  }
  .dossier-modal-backdrop {
    position: static !important;
    background: none !important;
    padding: 0 !important;
    display: block !important;
    overflow: visible !important;
  }
  .dossier-modal-header {
    display: none !important;
  }
  .dossier-modal-panel {
    border: none !important;
    box-shadow: none !important;
    max-height: none !important;
    width: 100% !important;
    max-width: 100% !important;
    overflow: visible !important;
  }
  .dossier-printable-area {
    overflow: visible !important;
    padding: 0 !important;
    background: white !important;
  }
  .dossier-document {
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    max-width: 100% !important;
  }
}
</style>
