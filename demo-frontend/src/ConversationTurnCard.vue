<script setup lang="ts">
import { computed } from 'vue'
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  GitBranch,
  LoaderCircle,
  RotateCcw,
  ShieldAlert,
  XCircle,
} from 'lucide-vue-next'
import type { ExecutionEventItem, RunOut, SourceItem } from './types'
import RunProgress from './RunProgress.vue'
import {
  describeUserFacingFailure,
  isSimulatedRun,
  resolveAnswerClaimSegments,
  type MappedAnswerClaim,
} from './medicalLabels'

const props = defineProps<{
  question: string
  answerText: string | null
  createdAt?: string
  run: RunOut | null
  selected?: boolean
  busy?: boolean
  isSimulation: boolean
  selectedClaimIndex?: number | null
  progressEvents?: ExecutionEventItem[]
  progressSyncDelayed?: boolean
}>()

const emit = defineEmits<{
  (e: 'selectTurn'): void
  (e: 'selectClaim', payload: MappedAnswerClaim, triggerEl: HTMLElement | null): void
  (e: 'inspectSource', source: SourceItem, triggerEl: HTMLElement | null): void
  (e: 'inspectOmittedClaims', triggerEl: HTMLElement | null): void
  (e: 'openTraceView', section: 'overview' | 'omitted' | 'dag', triggerEl: HTMLElement | null): void
  (e: 'retryQuestion', question: string): void
  (e: 'cancelRun'): void
}>()

const simulated = computed(() => isSimulatedRun(props.run, props.isSimulation))
const claimMapping = computed(() =>
  resolveAnswerClaimSegments(props.run, props.answerText ?? props.run?.answer),
)
const failureSummary = computed(() => describeUserFacingFailure(props.run))

const omittedCount = computed(
  () => props.run?.omitted_claim_count || claimMapping.value.omittedClaims.length || 0,
)

const questionPreserved = computed(() => Boolean(props.question && props.question.trim().length > 0))

const effectiveStatus = computed(() => {
  if (!props.run) return 'completed'
  if (['running', 'awaiting_input', 'paused'].includes(props.run.run_status)) {
    return props.run.run_status
  }
  if (props.run.reviewer_status === 'failed') return 'reviewer_failed'
  return props.run.result_status || props.run.run_status
})

const statusBadgeText = computed(() => {
  const r = props.run
  if (!r) return '已回复'
  if (r.run_status === 'running') return '执行中…'
  if (r.run_status === 'awaiting_input') return '等待补充说明'
  if (r.run_status === 'paused') return '已暂停'
  if (r.response_origin === 'urgent_policy') return '紧急医疗规则直出'
  if (r.reviewer_status === 'failed') return '审核拦截（未输出初稿）'
  if (r.result_status === 'partial') {
    return omittedCount.value ? `部分完成（省略 ${omittedCount.value} 条）` : '部分完成'
  }
  if (r.result_status === 'failed' || r.run_status === 'failed') {
    return '服务暂不可用 / 未完成'
  }
  if (r.result_status === 'cancelled' || r.run_status === 'cancelled') return '已取消'
  if (r.result_status === 'timed_out' || r.run_status === 'timed_out') return '执行超时'
  return '已完成'
})

const memoryBadgeText = computed(() => {
  const r = props.run
  if (!r) return null
  const prefs = r.memory_fixed_preferences
  const hasPrefs = prefs && Object.keys(prefs).length > 0
  const hasLearning = Boolean(r.learning_state?.last_topic)
  if (hasLearning && hasPrefs) return '记忆已接续'
  if (hasLearning) return '学习跟进中'
  if (hasPrefs) return '已载入偏好'
  if (r.context_details?.memory_status === 'ready' || (r.context_details?.memory_count && r.context_details.memory_count > 0)) {
    return '背景记忆已引用'
  }
  return null
})

function sectionHeadingForParagraph(index: number, total: number): string | null {
  if (total <= 1) return null
  if (index === 0) return '核心结论'
  if (index === 1) return '机制与适用范围'
  if (index === 2) return '检查准备与注意事项'
  return `补充说明 ${index}`
}

const MEDICAL_METRIC_REGEX =
  /(\b\d{2,3}\/\d{2,3}(?:\s*mmHg)?\b|\b(?:HbA1c|eGFR|UACR|FPG|OGTT|BMI)\b|\b\d+(?:\.\d+)?\s*(?:mmHg|mmol\/L|mg\/dL|mg\/g|mL\/min(?:\/1\.73m²)?|%))/gi

interface TextPart {
  type: 'text' | 'metric'
  content: string
}

function parseMedicalText(text: string): TextPart[] {
  if (!text) return []
  const parts: TextPart[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null
  MEDICAL_METRIC_REGEX.lastIndex = 0

  while ((match = MEDICAL_METRIC_REGEX.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', content: text.slice(lastIndex, match.index) })
    }
    parts.push({ type: 'metric', content: match[0] })
    lastIndex = match.index + match[0].length
  }
  if (lastIndex < text.length) {
    parts.push({ type: 'text', content: text.slice(lastIndex) })
  }
  return parts
}
</script>

<template>
  <article
    class="turn-card"
    :class="{ 'is-selected': selected }"
    @click="emit('selectTurn')"
  >
    <!-- User Question Row -->
    <div class="user-prompt-row">
      <div class="user-prompt-meta">
        <span class="role-tag user">提问</span>
        <time v-if="createdAt" class="mono">{{ createdAt }}</time>
      </div>
      <div class="user-prompt-bubble">{{ question }}</div>
    </div>

    <!-- Assistant Response Sheet -->
    <div class="assistant-response-box" :class="`status-${effectiveStatus}`">
      <!-- Calm Single-Line Status & Verification Metadata Header -->
      <header class="response-status-bar">
        <div class="status-left">
          <span class="status-indicator" :class="effectiveStatus">
            <LoaderCircle v-if="effectiveStatus === 'running'" :size="14" class="spin" />
            <CheckCircle2 v-else-if="effectiveStatus === 'completed'" :size="14" />
            <AlertTriangle
              v-else-if="
                ['partial', 'reviewer_failed', 'awaiting_input', 'paused'].includes(effectiveStatus)
              "
              :size="14"
            />
            <XCircle v-else :size="14" />
            <strong>{{ statusBadgeText }}</strong>
          </span>

          <template v-if="effectiveStatus !== 'running'">
          <span class="meta-dot" aria-hidden="true">·</span>

          <span
            v-if="run?.citation_support_status === 'model_reviewed'"
            class="verify-meta-text model-ok"
          >
            {{ simulated ? '模拟引用核对完成' : '模型引用核对完成' }}
          </span>
          <span
            v-else-if="run?.reviewer_status === 'skipped_policy'"
            class="verify-meta-text policy-skip"
          >
            安全规则快速出口
          </span>
          <span
            v-else-if="run && run.citation_support_status === 'unverified'"
            class="verify-meta-text unverified"
          >
            引用未完成核对
          </span>

          <span class="meta-dot" aria-hidden="true">·</span>

          <span class="verify-meta-text clinical-not-run">
            医学专业审核：未执行
          </span>

          <template v-if="memoryBadgeText">
            <span class="meta-dot" aria-hidden="true">·</span>
            <span class="verify-meta-text memory-badge" :title="run?.learning_state?.learning_goal || '已启用连续记忆'">
              {{ memoryBadgeText }}
            </span>
          </template>
          </template>
        </div>

        <div class="status-right">
          <span v-if="claimMapping.hasReliableMapping" class="cite-guide-hint">
            点击句末上标查看原文
          </span>
          <button
            v-if="run && ['running', 'awaiting_input', 'paused'].includes(run.run_status)"
            type="button"
            class="action-chip danger"
            @click.stop="emit('cancelRun')"
          >
            取消运行
          </button>
          <button
            v-if="
              run &&
              (run.run_status === 'failed' ||
                run.result_status === 'failed' ||
                run.safe_error_code === 'UPSTREAM_ERROR')
            "
            type="button"
            class="action-chip retry"
            :disabled="busy"
            @click.stop="emit('retryQuestion', question)"
          >
            <RotateCcw :size="13" />
            <span>重试本轮提问</span>
          </button>
        </div>
      </header>

      <!-- Concise User-Facing Failure / Interception Explanation (When Failed or Reviewer Blocked) -->
      <RunProgress
        v-if="effectiveStatus === 'running'"
        :run="run"
        :events="progressEvents"
        :sync-delayed="progressSyncDelayed"
      />
      <div
        v-else-if="failureSummary && !claimMapping.paragraphs.length"
        class="user-failure-card"
        :class="effectiveStatus"
        role="status"
      >
        <div class="failure-card-head">
          <ShieldAlert :size="18" />
          <strong>本轮未能返回医学回答</strong>
          <span v-if="questionPreserved" class="preserved-pill">问题已保留</span>
        </div>
        <dl class="failure-explain-list">
          <div>
            <dt>发生了什么</dt>
            <dd>{{ failureSummary.whatHappened }}</dd>
          </div>
          <div>
            <dt>未完成内容</dt>
            <dd>{{ failureSummary.whatIsIncomplete }}</dd>
          </div>
          <div>
            <dt>下一步建议</dt>
            <dd>{{ failureSummary.nextStep }}</dd>
          </div>
        </dl>
        <div class="failure-card-actions">
          <button
            v-if="
              run &&
              (run.run_status === 'failed' ||
                run.result_status === 'failed' ||
                run.safe_error_code === 'UPSTREAM_ERROR')
            "
            type="button"
            class="btn primary sm"
            :disabled="busy"
            @click.stop="emit('retryQuestion', question)"
          >
            <RotateCcw :size="13" />
            <span>重试本轮提问</span>
          </button>
          <button
            type="button"
            class="btn secondary sm"
            @click.stop="
              emit('openTraceView', 'overview', ($event.currentTarget as HTMLElement) || null)
            "
          >
            <GitBranch :size="13" />
            <span>查看错误码与节点诊断详情 →</span>
          </button>
        </div>
      </div>

      <!-- Main Answer Prose: Unified Full-Text Segment Rendering (Never Drops Unmapped Text) -->
      <div v-else class="answer-prose">
        <div
          v-if="claimMapping.mappingStatus === 'fallback_plain' && run?.sources?.length"
          class="unmapped-notice-bar"
        >
          <span>当前回答暂无可用的逐事实引用定位，已完整展示正文并在下方列出本轮引用资料。</span>
        </div>
        <div
          v-else-if="claimMapping.mappingStatus === 'partial'"
          class="unmapped-notice-bar"
        >
          <span>部分句子的引用偏移未对齐，已仅在可精确对齐的句子旁显示引用入口，正文完整保留。</span>
        </div>

        <template v-if="claimMapping.paragraphs.length">
          <section
            v-for="(paraSegments, pIdx) in claimMapping.paragraphs"
            :key="pIdx"
            class="structured-para-block"
          >
            <h3
              v-if="sectionHeadingForParagraph(pIdx, claimMapping.paragraphs.length)"
              class="para-section-label"
            >
              {{ sectionHeadingForParagraph(pIdx, claimMapping.paragraphs.length) }}
            </h3>
            <p class="prose-paragraph">
              <template
                v-for="(seg, sIdx) in paraSegments"
                :key="`${pIdx}-${sIdx}-${seg.start}`"
              >
                <span
                  v-if="seg.kind === 'claim' && seg.isMedicalFactWithEvidence"
                  class="claim-sentence has-evidence"
                  :class="{
                    'is-active': selectedClaimIndex === seg.claim.index,
                  }"
                  @click.stop="
                    emit(
                      'selectClaim',
                      seg,
                      (($event.currentTarget as HTMLElement)?.querySelector(
                        '.claim-cite-btn',
                      ) as HTMLElement) || ($event.currentTarget as HTMLElement) || null,
                    )
                  "
                >
                  <span><template v-for="(part, pIdx) in parseMedicalText(seg.text)" :key="pIdx"><mark v-if="part.type === 'metric'" class="med-metric-chip">{{ part.content }}</mark><template v-else>{{ part.content }}</template></template></span>
                  <button
                    type="button"
                    class="claim-cite-btn"
                    :class="{ active: selectedClaimIndex === seg.claim.index }"
                    :aria-label="`查看第 ${seg.claim.index + 1} 句的原文依据`"
                    :title="`来源 ${seg.sourceNumbers.join('、')} · ${seg.evidenceAnchors.length} 处原文依据`"
                    @click.stop="
                      emit('selectClaim', seg, ($event.currentTarget as HTMLElement) || null)
                    "
                  >
                    <span>[{{ seg.sourceNumbers.length ? seg.sourceNumbers.join(',') : '原文' }}]</span>
                  </button>
                </span>
                <span
                  v-else-if="seg.kind === 'claim' && seg.isPolicyOrScope"
                  class="claim-sentence"
                >
                  <span><template v-for="(part, pIdx) in parseMedicalText(seg.text)" :key="pIdx"><mark v-if="part.type === 'metric'" class="med-metric-chip">{{ part.content }}</mark><template v-else>{{ part.content }}</template></template></span>
                  <span class="claim-policy-tag" title="这是项目的使用限制，不是原文医学事实。">使用提示</span>
                </span>
                <span v-else class="plain-text-segment"><template v-for="(part, pIdx) in parseMedicalText(seg.text)" :key="pIdx"><mark v-if="part.type === 'metric'" class="med-metric-chip">{{ part.content }}</mark><template v-else>{{ part.content }}</template></template></span>
              </template>
            </p>
          </section>
        </template>
      </div>

      <!-- Bottom Unified Footer: Sources + Scope + Single Technical Details Entry -->
      <footer v-if="run && effectiveStatus !== 'running'" class="turn-unified-footer">
        <div v-if="run.sources && run.sources.length" class="inline-sources-row">
          <span class="sources-row-label">
            <BookOpen :size="13" />
            <span>引用资料 ({{ run.sources.length }})：</span>
          </span>
          <div class="source-pills">
            <button
              v-for="(src, sIdx) in run.sources"
              :key="src.id"
              type="button"
              class="source-pill-btn"
              @click.stop="
                emit('inspectSource', src, ($event.currentTarget as HTMLElement) || null)
              "
            >
              <span class="pill-idx mono">[{{ sIdx + 1 }}]</span>
              <span class="pill-title">
                {{ src.title || src.document_id }}{{ src.section ? ` · ${src.section}` : '' }}
              </span>
            </button>
          </div>
        </div>

        <div class="footer-meta-bar">
          <span class="scope-note-inline">
            资料范围：权威临床诊疗指南与人卫版教材标准，不替代临床医师面诊或处方。
          </span>
          <button
            type="button"
            class="open-tech-btn"
            @click.stop="
              emit('openTraceView', 'overview', ($event.currentTarget as HTMLElement) || null)
            "
          >
            <GitBranch :size="13" />
            <span>本轮回答说明 →</span>
          </button>
        </div>
      </footer>
    </div>
  </article>
</template>
