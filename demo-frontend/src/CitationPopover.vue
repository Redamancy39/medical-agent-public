<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  ExternalLink,
  GitBranch,
  Quote,
  ShieldCheck,
  X,
} from 'lucide-vue-next'
import type { MappedAnswerClaim } from './medicalLabels'
import type { EvidenceAnchor, RunOut, SourceItem } from './types'
import { formatLabel } from './medicalLabels'

const props = defineProps<{
  claim: MappedAnswerClaim | null
  anchorEl: HTMLElement | null
  run: RunOut | null
  open: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'openFullInspector', claim: MappedAnswerClaim): void
  (e: 'inspectSource', source: SourceItem): void
}>()

const popoverRef = ref<HTMLElement | null>(null)
const popoverStyle = ref<Record<string, string>>({})

const supportStatus = computed(() => props.claim?.claim.support_status || 'unverified')
const supportStatusLabel = computed(() => {
  const st = supportStatus.value
  if (st === 'supported') return '权威文献充分支持'
  if (st === 'partially_supported') return '部分文献支持'
  if (st === 'contradicted') return '与文献结论冲突'
  if (st === 'unsupported') return '未获充分支持'
  return formatLabel(st)
})

const matchedSources = computed<SourceItem[]>(() => {
  if (!props.claim || !props.run?.sources) return []
  return props.claim.sourceNumbers
    .map(num => props.run!.sources[num - 1])
    .filter((s): s is SourceItem => Boolean(s))
})

function findSourceForAnchor(anchor: EvidenceAnchor): SourceItem | undefined {
  if (!props.run?.sources) return undefined
  return props.run.sources.find(
    s => s.id === anchor.source_id || s.document_id === anchor.document_id,
  )
}

function updatePosition() {
  if (!props.open || !props.anchorEl) return

  const rect = props.anchorEl.getBoundingClientRect()
  const vw = window.innerWidth
  const vh = window.innerHeight

  if (vw <= 640) {
    popoverStyle.value = {
      position: 'fixed',
      bottom: '16px',
      left: '12px',
      right: '12px',
      maxWidth: 'calc(100vw - 24px)',
      maxHeight: '75vh',
      zIndex: '1050',
    }
    return
  }

  const width = Math.min(460, vw - 32)
  let left = rect.left - 16
  if (left + width > vw - 16) {
    left = vw - width - 16
  }
  if (left < 16) {
    left = 16
  }

  const spaceBelow = vh - rect.bottom
  const spaceAbove = rect.top
  const preferAbove = spaceBelow < 320 && spaceAbove > spaceBelow

  const top = preferAbove ? Math.max(16, rect.top - 8) : rect.bottom + 8
  const transform = preferAbove ? 'translateY(-100%)' : 'none'

  popoverStyle.value = {
    position: 'fixed',
    top: `${Math.round(top)}px`,
    left: `${Math.round(left)}px`,
    width: `${width}px`,
    maxHeight: 'min(500px, 80vh)',
    transform,
    zIndex: '1050',
  }
}

function onDocumentClick(e: MouseEvent) {
  if (!props.open) return
  const target = e.target as Node | null
  if (!target) return
  if (popoverRef.value && popoverRef.value.contains(target)) return
  if (props.anchorEl && props.anchorEl.contains(target)) return
  emit('close')
}

function onKeyDown(e: KeyboardEvent) {
  if (!props.open) return
  if (e.key === 'Escape') {
    e.stopPropagation()
    emit('close')
    props.anchorEl?.focus()
  }
}

watch(
  () => props.open,
  val => {
    if (val) {
      nextTick(() => {
        updatePosition()
        if (typeof window !== 'undefined') {
          window.addEventListener('scroll', updatePosition, true)
          window.addEventListener('resize', updatePosition)
          window.addEventListener('click', onDocumentClick, true)
          window.addEventListener('keydown', onKeyDown, true)
        }
      })
    } else {
      if (typeof window !== 'undefined') {
        window.removeEventListener('scroll', updatePosition, true)
        window.removeEventListener('resize', updatePosition)
        window.removeEventListener('click', onDocumentClick, true)
        window.removeEventListener('keydown', onKeyDown, true)
      }
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('scroll', updatePosition, true)
    window.removeEventListener('resize', updatePosition)
    window.removeEventListener('click', onDocumentClick, true)
    window.removeEventListener('keydown', onKeyDown, true)
  }
})

function handleOpenFull() {
  if (!props.claim) return
  emit('openFullInspector', props.claim)
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <transition name="popover-fade">
      <div
        v-if="open && claim"
        ref="popoverRef"
        class="citation-popover-card"
        :style="popoverStyle"
        role="dialog"
        aria-modal="false"
        aria-label="文献引用与依据快速预览"
      >
        <!-- Popover Header -->
        <header class="popover-header">
          <div class="popover-title-row">
            <span class="popover-badge">第 {{ (claim.claim.index ?? 0) + 1 }} 句医学事实</span>
            <span
              v-if="supportStatus === 'supported'"
              class="popover-status-pill ok"
            >
              <CheckCircle2 :size="13" />
              <span>权威文献支持</span>
            </span>
            <span
              v-else-if="supportStatus === 'partially_supported'"
              class="popover-status-pill partial"
            >
              <AlertTriangle :size="13" />
              <span>部分支持</span>
            </span>
            <span v-else class="popover-status-pill warning">
              <AlertTriangle :size="13" />
              <span>{{ supportStatusLabel }}</span>
            </span>
          </div>
          <button
            type="button"
            class="popover-close-btn"
            aria-label="关闭依据预览"
            @click="emit('close')"
          >
            <X :size="15" />
          </button>
        </header>

        <!-- Popover Body -->
        <div class="popover-body">
          <!-- Statement Box -->
          <div class="popover-fact-section">
            <div class="popover-section-label">回答断言语句</div>
            <p class="popover-fact-text">{{ claim.claim.text || claim.text }}</p>
          </div>

          <!-- Matched Evidence Anchors -->
          <div class="popover-anchors-section">
            <div class="popover-section-label">
              <span>对应 NLM / MedlinePlus 权威原文依据</span>
              <span class="anchor-count-tag">{{ claim.evidenceAnchors.length }} 处</span>
            </div>

            <div v-if="claim.evidenceAnchors.length > 0" class="popover-anchor-list">
              <article
                v-for="(anchor, aIdx) in claim.evidenceAnchors"
                :key="anchor.id || aIdx"
                class="popover-anchor-item"
              >
                <div class="anchor-source-meta">
                  <div class="anchor-source-left">
                    <BookOpen :size="13" class="source-icon" />
                    <strong class="source-title">
                      {{ findSourceForAnchor(anchor)?.title || anchor.document_id }}
                    </strong>
                    <span
                      v-if="findSourceForAnchor(anchor)?.section"
                      class="source-section-pill"
                    >
                      {{ findSourceForAnchor(anchor)?.section }}
                    </span>
                  </div>
                  <a
                    v-if="anchor.url || findSourceForAnchor(anchor)?.url"
                    :href="anchor.url || findSourceForAnchor(anchor)?.url || '#'"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="source-ext-link"
                    title="在浏览器中打开 NLM 官方页面"
                  >
                    <span>NLM 原文</span>
                    <ExternalLink :size="11" />
                  </a>
                </div>

                <blockquote class="anchor-quote-box">
                  <span class="quote-mark">“</span>
                  <span class="quote-text">{{ anchor.quote }}</span>
                  <span class="quote-mark">”</span>
                </blockquote>

                <div
                  v-if="findSourceForAnchor(anchor)?.score"
                  class="anchor-score-bar"
                >
                  <span class="score-label">知识库语义匹配度</span>
                  <span class="score-val">
                    {{ Math.round((findSourceForAnchor(anchor)?.score || 0) * 100) }}%
                  </span>
                </div>
              </article>
            </div>

            <div v-else-if="matchedSources.length > 0" class="popover-anchor-list">
              <article
                v-for="src in matchedSources"
                :key="src.id"
                class="popover-anchor-item"
              >
                <div class="anchor-source-meta">
                  <div class="anchor-source-left">
                    <BookOpen :size="13" class="source-icon" />
                    <strong class="source-title">{{ src.title || src.document_id }}</strong>
                  </div>
                  <a
                    v-if="src.url"
                    :href="src.url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="source-ext-link"
                  >
                    <span>NLM 原文</span>
                    <ExternalLink :size="11" />
                  </a>
                </div>
                <div class="anchor-quote-box">
                  <span class="quote-text">{{ src.content.slice(0, 180) }}...</span>
                </div>
              </article>
            </div>

            <div v-else class="popover-no-anchor">
              本句尚未匹配到直接的 NLM 原文锚点切片。
            </div>
          </div>
        </div>

        <!-- Popover Footer -->
        <footer class="popover-footer">
          <span class="popover-disclaimer">美国 NLM/MedlinePlus 摘述 · 科研辅助参考</span>
          <button
            type="button"
            class="popover-expand-btn"
            @click="handleOpenFull"
          >
            <GitBranch :size="13" />
            <span>在右侧深入查看完整诊断 →</span>
          </button>
        </footer>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.citation-popover-card {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  box-shadow: 0 16px 36px -4px rgba(15, 23, 42, 0.18), 0 6px 14px -2px rgba(15, 23, 42, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: inherit;
  color: #1e293b;
}

.popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.popover-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.popover-badge {
  font-size: 12px;
  font-weight: 700;
  color: #0f172a;
}

.popover-status-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 999px;
}

.popover-status-pill.ok {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
}

.popover-status-pill.partial {
  background: #fffbeb;
  color: #b45309;
  border: 1px solid #fde68a;
}

.popover-status-pill.warning {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.popover-close-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  color: #64748b;
  padding: 4px;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.popover-close-btn:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.popover-body {
  padding: 12px 14px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.popover-section-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #64748b;
  margin-bottom: 5px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.anchor-count-tag {
  font-size: 10px;
  background: #e0f2fe;
  color: #0284c7;
  padding: 1px 6px;
  border-radius: 999px;
  font-weight: 700;
}

.popover-fact-section {
  background: #f8fafc;
  border-left: 3px solid #0284c7;
  padding: 8px 10px;
  border-radius: 0 6px 6px 0;
}

.popover-fact-text {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.5;
  color: #0f172a;
  font-weight: 500;
}

.popover-anchors-section {
  display: flex;
  flex-direction: column;
}

.popover-anchor-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.popover-anchor-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 9px 11px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.anchor-source-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.anchor-source-left {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  overflow: hidden;
}

.source-icon {
  color: #0284c7;
  flex-shrink: 0;
}

.source-title {
  font-size: 12.5px;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.source-section-pill {
  font-size: 10.5px;
  background: #f1f5f9;
  color: #475569;
  padding: 1px 5px;
  border-radius: 4px;
  flex-shrink: 0;
  white-space: nowrap;
}

.source-ext-link {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  color: #0284c7;
  text-decoration: none;
  flex-shrink: 0;
  font-weight: 500;
}

.source-ext-link:hover {
  text-decoration: underline;
}

.anchor-quote-box {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.5;
  color: #334155;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 7px 9px;
  font-style: italic;
  display: flex;
  gap: 2px;
}

.quote-mark {
  color: #94a3b8;
  font-size: 14px;
  font-weight: 700;
  line-height: 1;
}

.quote-text {
  flex: 1;
}

.anchor-score-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 10.5px;
  color: #64748b;
  padding-top: 2px;
}

.score-val {
  font-weight: 700;
  color: #0284c7;
}

.popover-no-anchor {
  font-size: 12px;
  color: #64748b;
  padding: 10px;
  background: #f8fafc;
  border-radius: 6px;
  text-align: center;
}

.popover-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 14px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  gap: 8px;
}

.popover-disclaimer {
  font-size: 10.5px;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.popover-expand-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 600;
  background: #0f172a;
  color: #ffffff;
  border: none;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.15s ease;
}

.popover-expand-btn:hover {
  background: #1e293b;
  transform: translateY(-1px);
}

/* Transitions */
.popover-fade-enter-active,
.popover-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.popover-fade-enter-from,
.popover-fade-leave-to {
  opacity: 0;
  transform: scale(0.96);
}
</style>
