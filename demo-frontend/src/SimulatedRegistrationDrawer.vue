<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  ArrowRight,
  Check,
  CheckCheck,
  ClipboardList,
  Database,
  FlaskConical,
  PencilLine,
  Plus,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-vue-next'
import {
  PROJECTS,
  SAMPLE_TYPES,
  STORAGES,
  STORAGE_KEY,
  addMessage,
  beginDraft,
  cancelDraft,
  commitDraft,
  dismissConfirmation,
  editDraft,
  fieldsOf,
  initialState,
  parseInput,
  requestConfirmation,
  restoreState,
  validate,
} from './workflow'
import type { Confirmation, DemoState, Fields } from './workflow'
import RegistrationPanel from './RegistrationPanel.vue'

const props = defineProps<{
  open: boolean
  backendToken: string
  backendSessionId: string
  backendSignedIn: string
  api: <T>(path: string, method?: string, body?: unknown) => Promise<T>
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'switchToBackendLogin'): void
}>()

const regTab = ref<'browser' | 'server' | 'records'>('browser')

let stored: string | null = null
try {
  stored = localStorage.getItem(STORAGE_KEY)
} catch {
  /* Browser storage can be disabled */
}
const state = ref<DemoState>(restoreState(stored) ?? initialState())
const nlInput = ref('')
const form = ref<Fields>(
  state.value.draft
    ? fieldsOf(state.value.draft)
    : { project: '', sampleType: '', quantity: null, receivedAt: '', storage: '', note: '' },
)
const confirmation = ref<Confirmation | null>(null)
const notice = ref('')

const draft = computed(() => state.value.draft)
const active = computed(() => draft.value && !['completed', 'cancelled'].includes(draft.value.status))
const errors = computed(() => validate(form.value))
const validCount = computed(
  () => 5 - ['project', 'sampleType', 'quantity', 'receivedAt', 'storage'].filter(k => errors.value[k]).length,
)
const statusLabel = computed(
  () =>
    ({
      incomplete: '待补全字段',
      ready: '草稿待核对',
      confirmation_pending: '等待明确确认',
      completed: '已确认登记',
      cancelled: '已取消',
    })[draft.value?.status ?? 'incomplete'],
)

function persist() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state.value))
  } catch {
    /* ignore */
  }
}
watch(state, persist, { deep: true })
persist()

function syncForm() {
  if (draft.value) form.value = fieldsOf(draft.value)
}

function updateForm() {
  if (!active.value) return
  confirmation.value = null
  editDraft(state.value, {
    ...form.value,
    quantity:
      form.value.quantity === null || String(form.value.quantity) === ''
        ? null
        : Number(form.value.quantity),
  })
  form.value = fieldsOf(draft.value!)
  notice.value = `已更新为第 ${draft.value!.revision} 版草稿，旧确认凭据已失效。`
}

function extractFromText(presetText?: string) {
  const text = (presetText ?? nlInput.value).trim()
  if (!text) return
  nlInput.value = ''
  const extracted = parseInput(text)
  if (!Object.keys(extracted).length) {
    notice.value = '未识别到有效演示字段，请包含数量、样本类型（组织/血液/唾液）、项目（DEMO-A/B）或区域（DEMO-B/C）。'
    return
  }
  if (active.value) {
    editDraft(state.value, { ...fieldsOf(draft.value!), ...extracted })
  } else {
    beginDraft(state.value, text)
  }
  syncForm()
  const missing = Object.keys(validate(draft.value!))
  notice.value = missing.length
    ? `草稿已生成（第 ${draft.value!.revision} 版），仍需补全 ${missing.length} 个必填项。`
    : `草稿字段已齐全（第 ${draft.value!.revision} 版），请核对后点击“核对当前版本”。`
}

function loadMissingExample() {
  if (active.value) {
    cancelDraft(state.value)
  }
  confirmation.value = null
  beginDraft(state.value, '帮我登记3份样本，属于A项目。')
  syncForm()
  notice.value = '已加载缺失字段示例（缺少样本类型、接收日期与存储区域），补齐前无法确认登记。'
}

function askConfirm() {
  updateForm()
  try {
    confirmation.value = requestConfirmation(state.value)
    notice.value = `正在核对第 ${draft.value?.revision} 版草稿，点击“明确确认并写入演示记录”才会生效。`
  } catch (err) {
    notice.value = (err as Error).message
  }
}

function cancelConfirmStep() {
  dismissConfirmation(state.value)
  confirmation.value = null
  notice.value = '已返回编辑状态，未新增任何记录。'
}

function finishCommit() {
  if (!confirmation.value) return
  try {
    const staged = JSON.parse(JSON.stringify(state.value)) as DemoState
    const record = commitDraft(staged, confirmation.value)
    addMessage(staged, 'assistant', `已确认登记 ${record.quantity} 份${record.sampleType}样本。`)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(staged))
    state.value = staged
    confirmation.value = null
    notice.value = `登记完成：已生成 1 批（${record.quantity} 个合成编号），可在“浏览器演示记录”查看。`
  } catch (err) {
    notice.value = `未登记：${(err as Error).message}`
  }
}

function cancelCurrentDraft() {
  if (!active.value) return
  cancelDraft(state.value)
  confirmation.value = null
  notice.value = '当前草稿已取消，未新增任何记录。'
}

function startNewDraft() {
  if (active.value) {
    cancelDraft(state.value)
  }
  confirmation.value = null
  beginDraft(state.value, '')
  syncForm()
  notice.value = '已创建新的空白模拟草稿。'
}

function resetBrowserDemo() {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* ignore */
  }
  state.value = initialState()
  syncForm()
  confirmation.value = null
  notice.value = '已重置浏览器模拟登记数据，恢复为初始 5 份组织样本草稿。'
}
</script>

<template>
  <div
    v-if="open"
    class="reg-modal-backdrop"
    @click.self="emit('close')"
  >
    <section
      class="reg-drawer-panel"
      role="dialog"
      aria-modal="true"
      aria-labelledby="sim-reg-title"
    >
      <header class="reg-drawer-header">
        <div>
          <div class="reg-eyebrow">
            <FlaskConical :size="14" />
            <span>次级功能演示 · 仅保留合成样本模拟登记</span>
          </div>
          <h2 id="sim-reg-title">科研样本模拟登记（草稿 · 版本校验 · 显式确认）</h2>
        </div>
        <button class="drawer-close-btn" @click="emit('close')" aria-label="关闭模拟登记窗口">
          <X :size="18" />
        </button>
      </header>

      <div class="reg-mode-tabs" role="tablist">
        <button
          role="tab"
          :aria-selected="regTab === 'browser'"
          :class="{ active: regTab === 'browser' }"
          @click="regTab = 'browser'"
        >
          <ClipboardList :size="15" />
          <span>浏览器本地模拟登记 (localStorage)</span>
        </button>
        <button
          role="tab"
          :aria-selected="regTab === 'records'"
          :class="{ active: regTab === 'records' }"
          @click="regTab = 'records'"
        >
          <Database :size="15" />
          <span>浏览器已确认记录 ({{ state.records.length }})</span>
        </button>
        <button
          role="tab"
          :aria-selected="regTab === 'server'"
          :class="{ active: regTab === 'server' }"
          @click="regTab = 'server'"
        >
          <ShieldCheck :size="15" />
          <span>服务端 SQL 模拟登记 (registration_graph_v1)</span>
        </button>
      </div>

      <div class="reg-drawer-body">
        <!-- TAB 1: BROWSER SIMULATION WORKFLOW -->
        <template v-if="regTab === 'browser'">
          <div class="reg-notice-banner">
            <span>
              <strong>模拟登记说明：</strong>此功能仅用于展示 Agent 工具链中的“结构化草稿提取 → 字段修改版本递增 → 显式二次确认门禁 → 幂等提交/取消”安全状态机，不扩展为真实医疗业务系统。
            </span>
            <button type="button" class="text-btn" @click="resetBrowserDemo">
              <RotateCcw :size="13" />
              <span>重置初始示例</span>
            </button>
          </div>

          <p v-if="notice" class="reg-status-toast" role="status">{{ notice }}</p>

          <!-- Natural Language Quick Extraction Bar -->
          <div class="nl-extract-box">
            <label for="nl-reg-input">自然语言提取草稿字段（有界规则提取，歧义留空）</label>
            <div class="nl-input-row">
              <input
                id="nl-reg-input"
                v-model="nlInput"
                type="text"
                placeholder="例如：今天收到5份组织样本，属于A项目，存储在B区域"
                @keydown.enter.prevent="extractFromText()"
              />
              <button type="button" class="btn secondary" @click="extractFromText()">
                提取至草稿
              </button>
            </div>
            <div class="nl-presets">
              <button
                type="button"
                @click="extractFromText('今天收到5份组织样本，属于A项目，存储在B区域。')"
              >
                <Sparkles :size="12" />
                <span>示例1：完整5份组织样本</span>
              </button>
              <button type="button" @click="loadMissingExample">
                <span>示例2：试试缺失字段草稿</span>
              </button>
              <button type="button" :disabled="!active" @click="cancelCurrentDraft">
                <span>取消当前草稿</span>
              </button>
            </div>
          </div>

          <!-- Draft Editor Form -->
          <div class="reg-draft-card">
            <div class="reg-draft-head">
              <div>
                <strong>
                  当前草稿
                  <span v-if="draft" class="mono">
                    · DRAFT-{{ draft.id.slice(0, 6).toUpperCase() }} · 第 {{ draft.revision }} 版
                  </span>
                </strong>
                <span class="field-progress mono">必填校验: {{ validCount }}/5</span>
              </div>
              <span class="reg-badge" :class="draft?.status">{{ statusLabel }}</span>
            </div>

            <div v-if="draft?.status === 'completed'" class="reg-outcome ok">
              <CheckCheck :size="20" />
              <div>
                <strong>本批合成样本已完成登记</strong>
                <p>已生成 {{ draft.quantity }} 个合成样本编号，草稿已锁定。可新建下一批草稿或查看记录。</p>
              </div>
              <button type="button" class="btn primary" @click="startNewDraft">
                <Plus :size="14" />
                <span>新建模拟草稿</span>
              </button>
            </div>

            <div v-else-if="draft?.status === 'cancelled'" class="reg-outcome cancelled">
              <X :size="20" />
              <div>
                <strong>当前草稿已取消</strong>
                <p>取消操作不会写入任何登记记录。</p>
              </div>
              <button type="button" class="btn primary" @click="startNewDraft">
                <Plus :size="14" />
                <span>新建模拟草稿</span>
              </button>
            </div>

            <form v-else class="reg-form-grid" @submit.prevent="askConfirm">
              <div class="form-field">
                <label for="sim-project">研究项目 (DEMO-A/B) *</label>
                <select id="sim-project" v-model="form.project" :disabled="!active" @change="updateForm">
                  <option value="">请选择演示项目</option>
                  <option v-for="p in PROJECTS" :key="p" :value="p">{{ p }}</option>
                </select>
                <small v-if="errors.project" class="err-msg">{{ errors.project }}</small>
              </div>

              <div class="form-field">
                <label for="sim-type">样本类型 *</label>
                <select id="sim-type" v-model="form.sampleType" :disabled="!active" @change="updateForm">
                  <option value="">请选择类型</option>
                  <option v-for="t in SAMPLE_TYPES" :key="t" :value="t">{{ t }}样本</option>
                </select>
                <small v-if="errors.sampleType" class="err-msg">{{ errors.sampleType }}</small>
              </div>

              <div class="form-field">
                <label for="sim-qty">样本数量 (1–20 份) *</label>
                <input
                  id="sim-qty"
                  v-model.number="form.quantity"
                  type="number"
                  min="1"
                  max="20"
                  step="1"
                  :disabled="!active"
                  @input="updateForm"
                />
                <small v-if="errors.quantity" class="err-msg">{{ errors.quantity }}</small>
              </div>

              <div class="form-field">
                <label for="sim-date">接收日期 (YYYY-MM-DD) *</label>
                <input
                  id="sim-date"
                  v-model="form.receivedAt"
                  type="date"
                  :disabled="!active"
                  @change="updateForm"
                />
                <small v-if="errors.receivedAt" class="err-msg">{{ errors.receivedAt }}</small>
              </div>

              <div class="form-field">
                <label for="sim-storage">存储区域 *</label>
                <select id="sim-storage" v-model="form.storage" :disabled="!active" @change="updateForm">
                  <option value="">请选择区域</option>
                  <option v-for="s in STORAGES" :key="s" :value="s">{{ s }}</option>
                </select>
                <small v-if="errors.storage" class="err-msg">{{ errors.storage }}</small>
              </div>

              <div class="form-field">
                <label for="sim-note">登记备注 (选填)</label>
                <input
                  id="sim-note"
                  v-model="form.note"
                  type="text"
                  maxlength="300"
                  placeholder="合成演示备注…"
                  :disabled="!active"
                  @input="updateForm"
                />
              </div>
            </form>

            <!-- Explicit Confirmation Box -->
            <div v-if="confirmation && active" class="explicit-confirm-box">
              <div class="confirm-box-head">
                <ShieldCheck :size="17" />
                <strong>核对确认对象：第 {{ confirmation.revision }} 版草稿</strong>
              </div>
              <p class="confirm-summary-line">
                项目 <strong>{{ form.project }}</strong> · <strong>{{ form.quantity }} 份{{ form.sampleType }}样本</strong> · 接收日期 <strong>{{ form.receivedAt }}</strong> · 存储于 <strong>{{ form.storage }}</strong>
              </p>
              <p class="confirm-rule-hint">
                如果在上方修改任何字段，草稿将自动升版且本确认框立即失效。
              </p>
              <div class="confirm-actions">
                <button type="button" class="btn secondary" @click="cancelConfirmStep">
                  返回修改
                </button>
                <button type="button" class="btn primary" @click="finishCommit">
                  <Check :size="15" />
                  <span>明确确认并写入演示记录</span>
                </button>
              </div>
            </div>

            <div v-else-if="active" class="reg-draft-footer">
              <button type="button" class="btn secondary" @click="cancelCurrentDraft">
                取消草稿
              </button>
              <button
                type="button"
                class="btn primary"
                :disabled="Object.keys(errors).length > 0"
                @click="askConfirm"
              >
                <span>核对当前版本 (第 {{ draft?.revision }} 版)</span>
                <ArrowRight :size="15" />
              </button>
            </div>
          </div>
        </template>

        <!-- TAB 2: BROWSER RECORDS & AUDIT -->
        <template v-else-if="regTab === 'records'">
          <div class="records-section">
            <div class="records-head">
              <h3>已确认的浏览器模拟批次 ({{ state.records.length }} 批)</h3>
              <button type="button" class="btn secondary" @click="regTab = 'browser'; startNewDraft()">
                <Plus :size="14" />
                <span>新建登记</span>
              </button>
            </div>

            <div v-if="!state.records.length" class="empty-reg-records">
              <p>尚无已确认的浏览器模拟记录。未确认或已取消的草稿不会进入此列表。</p>
            </div>

            <table v-else class="reg-table">
              <thead>
                <tr>
                  <th>批次号</th>
                  <th>项目</th>
                  <th>样本类型与数量</th>
                  <th>存储区域</th>
                  <th>接收日期</th>
                  <th>核定版本</th>
                  <th>合成样本编号</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="rec in state.records" :key="rec.id">
                  <td class="mono">SYN-{{ rec.draftId.slice(0, 6).toUpperCase() }}</td>
                  <td>{{ rec.project }}</td>
                  <td>{{ rec.quantity }} 份{{ rec.sampleType }}</td>
                  <td>{{ rec.storage }}</td>
                  <td class="mono">{{ rec.receivedAt }}</td>
                  <td class="mono">v{{ rec.revision }}</td>
                  <td class="mono sample-ids-cell">{{ rec.sampleIds.join(', ') }}</td>
                </tr>
              </tbody>
            </table>

            <div class="audit-log-box">
              <h4>草稿状态机操作记录 ({{ state.audit.length }})</h4>
              <ul>
                <li v-for="ev in state.audit.slice(0, 12)" :key="ev.id">
                  <strong>{{ ev.action }}</strong>
                  <span>{{ ev.detail }}</span>
                </li>
              </ul>
            </div>
          </div>
        </template>

        <!-- TAB 3: SERVER SQL REGISTRATION -->
        <template v-else>
          <div v-if="!backendToken || !backendSessionId" class="server-reg-gate">
            <ShieldCheck :size="26" />
            <h3>服务端 SQL 模拟登记需在“后端联调”模式登录并选择会话</h3>
            <p>
              服务端模拟登记（<code>/sessions/{id}/registration-drafts</code>）受 JWT 身份与会话所有权保护，数据保存在本地 SQLite (<code>backend/data/app.db</code>)。
            </p>
            <button type="button" class="btn primary" @click="emit('switchToBackendLogin')">
              切换到后端联调并登录 →
            </button>
          </div>
          <RegistrationPanel
            v-else
            :key="`${backendSignedIn}:${backendSessionId}`"
            :session-id="backendSessionId"
            :api="api"
          />
        </template>
      </div>
    </section>
  </div>
</template>
