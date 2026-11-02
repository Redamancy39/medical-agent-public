<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Filter,
  Layers,
  RefreshCw,
  Search,
  Sparkles,
  X,
} from 'lucide-vue-next'
import type { KnowledgeCatalogItem, KnowledgeCatalogOverview } from './types'
import { focusInitialElement, trapFocusOnTab } from './focusTrap'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const modalRef = ref<HTMLElement | null>(null)
const searchInputRef = ref<HTMLInputElement | null>(null)

const loading = ref(false)
const error = ref('')
const catalog = ref<KnowledgeCatalogOverview>({
  total_documents: 0,
  total_sections: 0,
  items: [],
})

const searchQuery = ref('')
const jurisdictionFilter = ref<'all' | 'CN' | 'INT'>('all')
const topicFilter = ref<string>('all')
const expandedItems = ref<Record<string, boolean>>({})

async function fetchCatalog() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('/api/knowledge/catalog')
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    }
    const data = (await res.json()) as KnowledgeCatalogOverview
    catalog.value = data
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载知识库目录失败'
  } finally {
    loading.value = false
  }
}

watch(
  () => props.open,
  async isOpen => {
    if (isOpen) {
      if (!catalog.value.items.length) {
        await fetchCatalog()
      }
      await nextTick()
      focusInitialElement(modalRef.value, '.catalog-search-input')
    }
  },
  { immediate: true },
)

function toggleExpand(id: string) {
  expandedItems.value[id] = !expandedItems.value[id]
}

function expandAll() {
  const map: Record<string, boolean> = {}
  filteredItems.value.forEach(item => {
    map[item.id] = true
  })
  expandedItems.value = map
}

function collapseAll() {
  expandedItems.value = {}
}

const allTopics = computed(() => {
  const map = new Map<string, string>()
  catalog.value.items.forEach(item => {
    if (item.topic && item.topic_zh) {
      map.set(item.topic, item.topic_zh)
    }
  })
  return Array.from(map.entries()).map(([topic, topic_zh]) => ({ topic, topic_zh }))
})

const cnCount = computed(
  () => catalog.value.items.filter(item => item.jurisdiction === 'CN').length,
)
const intCount = computed(
  () => catalog.value.items.filter(item => item.jurisdiction !== 'CN').length,
)

const filteredItems = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return catalog.value.items.filter(item => {
    if (jurisdictionFilter.value === 'CN' && item.jurisdiction !== 'CN') return false
    if (jurisdictionFilter.value === 'INT' && item.jurisdiction === 'CN') return false
    if (topicFilter.value !== 'all' && item.topic !== topicFilter.value) return false

    if (!q) return true

    const titleMatch = (item.title || '').toLowerCase().includes(q)
    const publisherMatch = (item.publisher || '').toLowerCase().includes(q)
    const topicMatch = (item.topic_zh || '').toLowerCase().includes(q)
    const secMatch = item.sections.some(
      s =>
        s.heading.toLowerCase().includes(q) ||
        s.text.toLowerCase().includes(q) ||
        s.quotes.some(quote => quote.toLowerCase().includes(q)),
    )
    return titleMatch || publisherMatch || topicMatch || secMatch
  })
})

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

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown, true)
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="catalog-modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="catalog-modal-title"
      @click="emit('close')"
    >
      <div
        ref="modalRef"
        class="catalog-modal-panel"
        tabindex="-1"
        @click.stop
      >
        <!-- Modal Header -->
        <header class="catalog-modal-header">
          <div class="header-left">
            <span class="catalog-icon-box"><BookOpen :size="18" /></span>
            <div>
              <h3 id="catalog-modal-title">临床知识库全景目录</h3>
              <p>国内外权威临床指南与国家规划教材规范 · 逐事实原文锚定与矢量分块</p>
            </div>
          </div>
          <div class="header-actions">
            <button
              type="button"
              class="refresh-btn"
              title="重新加载知识库目录"
              :disabled="loading"
              @click="fetchCatalog"
            >
              <RefreshCw :size="14" :class="{ 'spin-anim': loading }" />
              <span>刷新</span>
            </button>
            <button
              type="button"
              class="close-btn"
              aria-label="关闭知识库目录"
              @click="emit('close')"
            >
              <X :size="18" />
            </button>
          </div>
        </header>

        <!-- Stats Bar -->
        <div class="catalog-stats-bar">
          <div class="stat-pill">
            <Layers :size="14" />
            <span>收录文献总量：<strong>{{ catalog.total_documents }}</strong> 篇</span>
          </div>
          <div class="stat-pill">
            <Sparkles :size="14" />
            <span>索引分块（Chunks）：<strong>{{ catalog.total_sections }}</strong> 个切片</span>
          </div>
          <div class="stat-pill cn">
            <span>🇨🇳 中国国家临床标准：<strong>{{ cnCount }}</strong> 部</span>
          </div>
          <div class="stat-pill int">
            <span>🌐 国际权威循证文献：<strong>{{ intCount }}</strong> 篇</span>
          </div>
        </div>

        <!-- Controls: Search & Filters -->
        <div class="catalog-controls">
          <div class="search-box">
            <Search :size="15" class="search-icon" />
            <input
              ref="searchInputRef"
              v-model="searchQuery"
              type="search"
              class="catalog-search-input"
              placeholder="搜索指南名称、章节标题、出处机构或关键词（如：奥司他韦、发热、幽门螺杆菌、BE FAST）..."
            />
            <button
              v-if="searchQuery"
              type="button"
              class="clear-search-btn"
              aria-label="清空搜索"
              @click="searchQuery = ''"
            >
              <X :size="13" />
            </button>
          </div>

          <!-- Filter Pills -->
          <div class="filter-row">
            <div class="pill-group">
              <span class="group-label">来源范畴:</span>
              <button
                type="button"
                class="filter-pill"
                :class="{ active: jurisdictionFilter === 'all' }"
                @click="jurisdictionFilter = 'all'"
              >
                全部 ({{ catalog.total_documents }})
              </button>
              <button
                type="button"
                class="filter-pill cn"
                :class="{ active: jurisdictionFilter === 'CN' }"
                @click="jurisdictionFilter = 'CN'"
              >
                🇨🇳 中国标准 ({{ cnCount }})
              </button>
              <button
                type="button"
                class="filter-pill int"
                :class="{ active: jurisdictionFilter === 'INT' }"
                @click="jurisdictionFilter = 'INT'"
              >
                🌐 国际文献 ({{ intCount }})
              </button>
            </div>

            <div class="expand-toggles">
              <button type="button" class="text-toggle-btn" @click="expandAll">全部展开</button>
              <span class="sep">/</span>
              <button type="button" class="text-toggle-btn" @click="collapseAll">全部收起</button>
            </div>
          </div>

          <!-- Topic Pills -->
          <div class="topic-row">
            <span class="group-label">专科领域:</span>
            <button
              type="button"
              class="topic-pill"
              :class="{ active: topicFilter === 'all' }"
              @click="topicFilter = 'all'"
            >
              全部专科
            </button>
            <button
              v-for="t in allTopics"
              :key="t.topic"
              type="button"
              class="topic-pill"
              :class="{ active: topicFilter === t.topic }"
              @click="topicFilter = t.topic"
            >
              {{ t.topic_zh }}
            </button>
          </div>
        </div>

        <!-- Body / Document Cards List -->
        <div class="catalog-modal-body">
          <div v-if="loading && !catalog.items.length" class="empty-loading-state">
            <RefreshCw :size="24" class="spin-anim" />
            <p>正在读取知识库目录与索引切片...</p>
          </div>

          <div v-else-if="error" class="error-banner">
            <p>加载失败：{{ error }}</p>
            <button type="button" class="btn-retry" @click="fetchCatalog">重试</button>
          </div>

          <div v-else-if="!filteredItems.length" class="empty-state">
            <BookOpen :size="32" class="empty-icon" />
            <p>没有找到符合条件的医学指南</p>
            <small>尝试更改搜索词或重置筛选条件</small>
          </div>

          <div v-else class="catalog-list">
            <article
              v-for="item in filteredItems"
              :key="item.id"
              class="catalog-item-card"
              :class="{ 'is-cn': item.jurisdiction === 'CN' }"
            >
              <div class="card-head" @click="toggleExpand(item.id)">
                <div class="title-and-badges">
                  <div class="badge-cluster">
                    <span v-if="item.jurisdiction === 'CN'" class="badge badge-cn">
                      🇨🇳 中国临床标准
                    </span>
                    <span v-else class="badge badge-int">
                      🌐 国际权威循证
                    </span>
                    <span class="badge badge-topic">{{ item.topic_zh }}</span>
                    <span class="badge badge-sections">{{ item.section_count }} 个索引切片</span>
                  </div>
                  <h4 class="doc-title">{{ item.title }}</h4>
                </div>
                <div class="card-actions" @click.stop>
                  <a
                    v-if="item.url"
                    :href="item.url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="ext-link-btn"
                    title="访问官方发布来源"
                  >
                    <span>官方出处</span>
                    <ExternalLink :size="12" />
                  </a>
                  <button
                    type="button"
                    class="expand-icon-btn"
                    :aria-expanded="expandedItems[item.id]"
                    :title="expandedItems[item.id] ? '收起详情' : '展开详情'"
                    @click="toggleExpand(item.id)"
                  >
                    <ChevronUp v-if="expandedItems[item.id]" :size="16" />
                    <ChevronDown v-else :size="16" />
                  </button>
                </div>
              </div>

              <!-- Metadata Summary Line -->
              <div class="card-meta">
                <span class="meta-item">
                  <strong>发布机构：</strong>{{ item.publisher || '未指定' }}
                </span>
                <span v-if="item.publication_date" class="meta-item">
                  <strong>发布时间：</strong>{{ item.publication_date }}
                </span>
                <span v-if="item.attribution" class="meta-item attr">
                  {{ item.attribution }}
                </span>
              </div>

              <!-- Sections View (Expanded) -->
              <div v-if="expandedItems[item.id]" class="card-sections-container">
                <div class="sections-divider">
                  <span>已入库的矢量切片与逐字引文锚点 ({{ item.sections.length }})</span>
                </div>
                <div class="sections-grid">
                  <div
                    v-for="(sec, sIdx) in item.sections"
                    :key="sIdx"
                    class="section-block"
                  >
                    <div class="section-head">
                      <span class="sec-badge mono">切片 {{ sIdx + 1 }}</span>
                      <strong class="sec-heading">{{ sec.heading }}</strong>
                    </div>
                    <p class="sec-text">{{ sec.text }}</p>
                    <div v-if="sec.quotes && sec.quotes.length" class="sec-quotes-box">
                      <span class="quotes-label">绑定原文证据字句（Reviewer 校验锚点）：</span>
                      <ul class="quotes-list">
                        <li v-for="(quote, qIdx) in sec.quotes" :key="qIdx" class="quote-item">
                          <q>{{ quote }}</q>
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            </article>
          </div>
        </div>

        <!-- Footer -->
        <footer class="catalog-modal-footer">
          <span class="footer-note">
            当前显示 <strong>{{ filteredItems.length }}</strong> / {{ catalog.total_documents }} 部医学文献 · 所有切片均经本地 BGE 稠密向量化与 GPU 交叉重排索引
          </span>
          <button type="button" class="btn-primary-close" @click="emit('close')">
            完成查看
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.catalog-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background-color: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  animation: fadeIn 0.18s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.catalog-modal-panel {
  background-color: #ffffff;
  width: 100%;
  max-width: 1060px;
  max-height: 90vh;
  border-radius: 14px;
  box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.25);
  display: flex;
  flex-direction: column;
  outline: none;
  overflow: hidden;
  border: 1px solid #e2e8f0;
}

.catalog-modal-header {
  padding: 18px 24px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: #f8fafc;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.catalog-icon-box {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background-color: #0284c7;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.catalog-modal-header h3 {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 700;
  color: #0f172a;
}

.catalog-modal-header p {
  margin: 2px 0 0;
  font-size: 0.8rem;
  color: #64748b;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 0.82rem;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #ffffff;
  color: #475569;
  cursor: pointer;
  transition: all 0.15s;
}

.refresh-btn:hover:not(:disabled) {
  background-color: #f1f5f9;
  color: #0f172a;
}

.close-btn {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s;
}

.close-btn:hover {
  background-color: #fee2e2;
  color: #ef4444;
}

/* Stats Bar */
.catalog-stats-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 12px 24px;
  background-color: #f1f5f9;
  border-bottom: 1px solid #e2e8f0;
}

.stat-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 20px;
  font-size: 0.8rem;
  color: #334155;
}

.stat-pill strong {
  color: #0f172a;
}

.stat-pill.cn {
  border-color: #a7f3d0;
  background-color: #ecfdf5;
  color: #065f46;
}

.stat-pill.int {
  border-color: #bae6fd;
  background-color: #f0f9ff;
  color: #0369a1;
}

/* Controls */
.catalog-controls {
  padding: 14px 24px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background-color: #ffffff;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  color: #94a3b8;
  pointer-events: none;
}

.catalog-search-input {
  width: 100%;
  padding: 8px 36px 8px 36px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 0.88rem;
  outline: none;
  transition: all 0.15s;
}

.catalog-search-input:focus {
  border-color: #0284c7;
  box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.15);
}

.clear-search-btn {
  position: absolute;
  right: 10px;
  border: none;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  padding: 4px;
}

.filter-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

.pill-group,
.topic-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.group-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: #64748b;
  margin-right: 4px;
}

.filter-pill,
.topic-pill {
  font-size: 0.78rem;
  padding: 3px 10px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  background-color: #f8fafc;
  color: #475569;
  cursor: pointer;
  transition: all 0.12s;
}

.filter-pill:hover,
.topic-pill:hover {
  background-color: #e2e8f0;
}

.filter-pill.active,
.topic-pill.active {
  background-color: #0284c7;
  border-color: #0284c7;
  color: #ffffff;
  font-weight: 600;
}

.filter-pill.cn.active {
  background-color: #059669;
  border-color: #059669;
}

.expand-toggles {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.78rem;
}

.text-toggle-btn {
  border: none;
  background: transparent;
  color: #0284c7;
  cursor: pointer;
  padding: 2px 4px;
  font-size: 0.78rem;
}

.text-toggle-btn:hover {
  text-decoration: underline;
}

.sep {
  color: #cbd5e1;
}

/* Body / List */
.catalog-modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px;
  background-color: #f8fafc;
}

.catalog-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.catalog-item-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px 18px;
  transition: all 0.15s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.catalog-item-card:hover {
  border-color: #cbd5e1;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
}

.catalog-item-card.is-cn {
  border-left: 4px solid #10b981;
}

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  cursor: pointer;
}

.title-and-badges {
  flex: 1;
}

.badge-cluster {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 6px;
}

.badge {
  font-size: 0.72rem;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.badge-cn {
  background-color: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}

.badge-int {
  background-color: #eff6ff;
  color: #1e40af;
  border: 1px solid #bfdbfe;
}

.badge-topic {
  background-color: #f1f5f9;
  color: #334155;
  border: 1px solid #e2e8f0;
}

.badge-sections {
  background-color: #faf5ff;
  color: #6b21a8;
  border: 1px solid #e9d5ff;
}

.doc-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.4;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ext-link-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.75rem;
  color: #0284c7;
  text-decoration: none;
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid #e0f2fe;
  background-color: #f0f9ff;
  transition: all 0.12s;
}

.ext-link-btn:hover {
  background-color: #bae6fd;
  color: #0369a1;
}

.expand-icon-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  color: #64748b;
  cursor: pointer;
}

.expand-icon-btn:hover {
  background-color: #f1f5f9;
  color: #0f172a;
}

.card-meta {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  font-size: 0.8rem;
  color: #475569;
}

.meta-item strong {
  color: #64748b;
  font-weight: 500;
}

.meta-item.attr {
  color: #64748b;
  font-style: italic;
}

/* Sections view */
.card-sections-container {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed #e2e8f0;
  animation: fadeIn 0.15s ease-out;
}

.sections-divider {
  font-size: 0.78rem;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 10px;
}

.sections-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-block {
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 14px;
}

.section-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.sec-badge {
  font-size: 0.7rem;
  padding: 1px 6px;
  background-color: #e2e8f0;
  color: #334155;
  border-radius: 4px;
  font-weight: 600;
}

.sec-heading {
  font-size: 0.88rem;
  color: #0f172a;
}

.sec-text {
  margin: 0 0 8px 0;
  font-size: 0.84rem;
  color: #334155;
  line-height: 1.5;
}

.sec-quotes-box {
  background-color: #ffffff;
  border-left: 3px solid #10b981;
  padding: 8px 12px;
  border-radius: 0 6px 6px 0;
  margin-top: 6px;
}

.quotes-label {
  display: block;
  font-size: 0.74rem;
  font-weight: 600;
  color: #059669;
  margin-bottom: 4px;
}

.quotes-list {
  margin: 0;
  padding-left: 16px;
  font-size: 0.8rem;
  color: #1e293b;
  line-height: 1.45;
}

.quote-item {
  margin-bottom: 3px;
}

.quote-item q {
  font-style: italic;
}

/* Empty & Error */
.empty-loading-state,
.empty-state {
  text-align: center;
  padding: 48px 16px;
  color: #64748b;
}

.empty-icon {
  margin-bottom: 8px;
  color: #94a3b8;
}

.spin-anim {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.error-banner {
  background-color: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  padding: 16px;
  border-radius: 8px;
  text-align: center;
}

.btn-retry {
  margin-top: 8px;
  padding: 6px 16px;
  background-color: #ef4444;
  color: #ffffff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

/* Footer */
.catalog-modal-footer {
  padding: 14px 24px;
  border-top: 1px solid #e2e8f0;
  background-color: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.footer-note {
  font-size: 0.8rem;
  color: #64748b;
}

.btn-primary-close {
  padding: 8px 18px;
  background-color: #0284c7;
  color: #ffffff;
  border: none;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-primary-close:hover {
  background-color: #0369a1;
}

@media (max-width: 640px) {
  .catalog-modal-panel {
    max-height: 96vh;
    border-radius: 8px;
  }
  .catalog-modal-header,
  .catalog-controls,
  .catalog-modal-body,
  .catalog-modal-footer {
    padding-left: 14px;
    padding-right: 14px;
  }
}
</style>
