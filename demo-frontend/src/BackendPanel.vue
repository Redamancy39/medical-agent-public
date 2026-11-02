<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import RegistrationPanel from './RegistrationPanel.vue'

type Session = { id: string; title: string }
type Message = { id: string; role: string; content: string; seq: number }
type Run = { run_id: string; request_id: string; run_status: string; result_status: string | null; answer: string | null; checkpoint_id: string | null; stage: string | null; model_calls: number | null; tool_calls: number | null; plan_status: string; safe_error_code: string | null; sources: { id: string; content: string; source: string; verified: boolean; url: string | null; title: string | null; content_kind: string | null; score: number | null; rerank_score: number | null }[]; task_count: number | null; distinct_agent_count: number | null; task_results: TaskResult[]; evidence_status: string; refinement_count: number; mode: string; memory_write_status: string; summary_write_status: string; schema_repair_count: number; maintenance_error_code: string | null; context_details: { memory_status?: string; summary_status?: string; memory_count?: number } }
type Fact = { id: string; key: string; content: string; status: string; version: number; synced_version: number }
type ProviderCall = { provider: string; operation: string; status: string; http_status: number | null; safe_error_code: string | null; usage: { total_tokens?: number } }
type Summary = { status: string; content: string | null; covered_until_seq: number; version: number }
type Job = { id: string; action: string; status: string; attempts: number; safe_error_code: string | null }
type Event = { stage: string; status: string; task_id: string | null }
type TaskResult = { task_id: string; agent_id: string; status: string; depends_on: string[]; safe_error_code: string | null; model_calls: number; tool_calls: number; refined: boolean }
const token = ref(''), username = ref(''), password = ref(''), signedIn = ref(''), error = ref('')
const sessions = ref<Session[]>([]), sessionId = ref(''), question = ref(''), clarification = ref('')
const messages = ref<Message[]>([]), run = ref<Run | null>(null), events = ref<Event[]>([])
const busy = ref(false), moreHistory = ref(false), pendingRequest = ref<{ question: string; request_id: string } | null>(null)
const health = ref<{ mode: string; external_calls_enabled: boolean; providers: Record<string, string> } | null>(null)
const facts = ref<Fact[]>([]), drafts = ref<Record<string, string>>({}), calls = ref<ProviderCall[]>([]), jobs = ref<Job[]>([]), summary = ref<Summary | null>(null)
let statusEpoch = 0
let polling: ReturnType<typeof setInterval> | undefined
const labels: Record<string, string> = { running: '执行中', finished: '已结束', completed: '完成', partial: '部分完成', failed: '失败', cancelled: '已取消', timed_out: '超时', awaiting_input: '等待补充', paused: '已暂停', blocked: '前置任务未完成', passed: '引用与任务检查通过', issues: '发现证据缺口', rechecking: '补查中', not_run: '未执行', ready: '已就绪', empty: '无记录或无命中', stale: '摘要待更新', invalidated: '已失效，等待重建', budget_omitted: '预算内未加载', done: '已完成', pending: '等待维护', processing: '维护中', uncertain: '结果待核对', awaiting_remote: '远端处理中', superseded: '已被新版本替代', skipped: '无需维护', deleted: '已撤回', active: '有效', offline_fake: '离线模拟', cloud_real: '真实云服务', hybrid: '混合模式' }
const stages: Record<string, string> = { load_context: '加载上下文', route: '任务路由', clarify: '补充问题', plan: 'Lead 规划', worker: 'Agent 判断', tools: '执行工具', validate_output: '检查输出', persist_result: '保存结果', cancel_requested: '申请取消', cancel: '取消运行', dispatch: '调度任务', task_worker: 'Worker 判断', task_tools: 'Worker 工具', task_validate: 'Worker 输出检查', task_result: '任务结果', check_evidence: '证据检查', synthesize: 'Lead 汇总' }

async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const requestToken = token.value
  let response: Response
  try { response = await fetch(`/api${path}`, { method, headers: { 'Content-Type': 'application/json', ...(token.value ? { Authorization: `Bearer ${token.value}` } : {}) }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) }) }
  catch { throw new Error('连接失败，请先启动本地8010后端。') }
  const data = await response.json()
  if (requestToken !== token.value) throw new Error('登录状态已变化，请重新操作。')
  if (!response.ok) {
    if (response.status === 401 && token.value) { token.value = ''; signedIn.value = ''; sessions.value = []; sessionId.value = ''; messages.value = []; run.value = null; events.value = []; facts.value = []; drafts.value = {}; calls.value = []; jobs.value = []; summary.value = null; error.value = '登录凭证已过期或无效，请重新登录后读取SQL会话和草稿。' }
    throw new Error(data.error?.message || '请求未成功，请稍后重试。')
  }
  return data as T
}

async function action(work: () => Promise<void>) {
  error.value = ''; busy.value = true
  try { await work() } catch (e) { error.value = (e as Error).message } finally { busy.value = false }
}
async function authenticate(register = false) {
  await action(async () => {
    const body = { username: username.value, password: password.value }
    if (register) await api('/auth/register', 'POST', body)
    const result = await api<{ access_token: string }>('/auth/login', 'POST', body)
    token.value = result.access_token; password.value = ''
    signedIn.value = (await api<{ username: string }>('/auth/me')).username
    sessions.value = (await api<{ items: Session[] }>('/sessions')).items
    await loadMaintenance()
  })
}
async function history(append = false) {
  const after = append ? messages.value.at(-1)?.seq || 0 : 0
  const data = await api<{ items: Message[]; has_more: boolean }>(`/sessions/${sessionId.value}/messages?limit=100&after_seq=${after}`)
  messages.value = append ? [...messages.value, ...data.items] : data.items; moreHistory.value = data.has_more
}
async function status() {
  if (!sessionId.value) { await loadMaintenance(); return }
  const epoch = ++statusEpoch
  const requestedSession = sessionId.value
  const runs = await api<NonNullable<typeof run.value>[]>(`/sessions/${requestedSession}/runs`)
  if (requestedSession !== sessionId.value) return
  const nextRun = runs.find(value => value.request_id === pendingRequest.value?.request_id) || runs[0] || null
  const [eventData, callData] = nextRun ? await Promise.all([api<{ items: Event[] }>(`/runs/${nextRun.run_id}/events`), api<{ items: ProviderCall[] }>(`/runs/${nextRun.run_id}/providers`)]) : [{ items: [] }, { items: [] }]
  if (epoch !== statusEpoch || requestedSession !== sessionId.value) return
  run.value = nextRun; events.value = eventData.items; calls.value = callData.items
  await loadMaintenance()
}
async function loadMaintenance() {
  health.value = await api('/health')
  facts.value = (await api<{ items: Fact[] }>('/memories')).items
  for (const fact of facts.value) if (!(fact.id in drafts.value)) drafts.value[fact.id] = fact.content
  jobs.value = (await api<{ items: Job[] }>('/maintenance/jobs')).items
  const requestedSession = sessionId.value
  const nextSummary = requestedSession ? await api<Summary>(`/sessions/${requestedSession}/summary`) : null
  if (requestedSession === sessionId.value) summary.value = nextSummary
}
async function editFact(fact: Fact, operation: 'update' | 'delete') {
  await action(async () => { await api(`/memories/${fact.id}`, 'POST', { operation, ...(operation === 'update' ? { content: drafts.value[fact.id] } : {}) }); await loadMaintenance() })
}
async function retryMaintenance() { await action(async () => { await api('/maintenance/retry', 'POST', {}); await status() }) }
async function choose() {
  statusEpoch++; pendingRequest.value = null; question.value = ''; clarification.value = ''
  if (!sessionId.value) { messages.value = []; run.value = null; events.value = []; calls.value = []; summary.value = null; return }
  await action(async () => { await history(); await status() })
}
async function createSession() {
  await action(async () => {
    const value = await api<Session>('/sessions', 'POST', { title: 'Agent联调会话' })
    sessions.value = (await api<{ items: Session[] }>('/sessions')).items
    statusEpoch++; sessionId.value = value.id; messages.value = []; run.value = null; events.value = []; calls.value = []; summary.value = null; pendingRequest.value = null
  })
}
async function send() {
  const text = question.value.trim()
  if (!text || !sessionId.value) return
  if (!pendingRequest.value || pendingRequest.value.question !== text) pendingRequest.value = { question: text, request_id: crypto.randomUUID() }
  await action(async () => {
    polling = setInterval(() => { void status().catch(() => { /* Foreground request reports errors. */ }) }, 400)
    try {
      run.value = await api<Run>(`/sessions/${sessionId.value}/chat`, 'POST', pendingRequest.value)
      question.value = ''; pendingRequest.value = null
      await history(); await status()
    } finally { clearInterval(polling) }
  })
}
async function resume() {
  if (!run.value?.checkpoint_id) return
  await action(async () => {
    run.value = await api<Run>(`/runs/${run.value!.run_id}/resume`, 'POST', { checkpoint_id: run.value!.checkpoint_id, ...(clarification.value.trim() ? { clarification: clarification.value.trim() } : {}) })
    clarification.value = ''; await history(); await status()
  })
}
async function cancel() {
  if (!run.value) return
  try { run.value = await api<Run>(`/runs/${run.value.run_id}/cancel`, 'POST'); if (!busy.value) { await history(); await status() } }
  catch (e) { error.value = (e as Error).message }
}
function logout() { statusEpoch++; clearInterval(polling); token.value = ''; signedIn.value = ''; sessionId.value = ''; sessions.value = []; messages.value = []; run.value = null; events.value = []; pendingRequest.value = null; facts.value = []; drafts.value = {}; calls.value = []; jobs.value = []; summary.value = null }
onMounted(() => { void api<NonNullable<typeof health.value>>('/health').then(value => { health.value = value }).catch(() => {}) })
onUnmounted(() => clearInterval(polling))
</script>

<template>
  <section class="backend-panel">
    <h1>Agent 流程联调</h1>
    <p class="backend-intro">对话与运行记录保存在本地 SQL。<template v-if="health?.mode === 'cloud_real'">当前使用真实 DeepSeek / Mem0、本地 Milvus + BGE 与本地 reranker；问题和筛选后的偏好会发送到相应云服务。网络工具只读取 PubMed 索引元数据。</template><template v-else>当前为{{ health ? labels[health.mode] || health.mode : '连接待确认' }}；普通离线演示使用合成数据。</template></p>
    <form v-if="!token" class="backend-login" @submit.prevent="authenticate()">
      <label>本地用户名<input v-model="username" autocomplete="username" minlength="3" required placeholder="自定义测试用户名" /></label>
      <label>密码<input v-model="password" type="password" autocomplete="current-password" minlength="8" required /></label>
      <button type="submit" :disabled="busy">登录</button><button type="button" :disabled="busy || !username || password.length < 8" @click="authenticate(true)">注册并登录</button>
      <small>登录凭证仅保存在页面内存，刷新后需要重新登录。</small>
    </form>
    <div v-else class="backend-account"><span>已登录：{{ signedIn }}</span><button @click="logout" :disabled="busy">退出登录</button></div>
    <p v-if="error" role="alert" class="backend-error">{{ error }}</p>
    <div v-if="token" class="backend-layout">
      <div class="backend-chat">
        <div class="backend-session"><label>会话<select v-model="sessionId" @change="choose" :disabled="busy"><option value="">请选择会话</option><option v-for="s in sessions" :key="s.id" :value="s.id">{{ s.title }} · {{ s.id.slice(0, 8) }}</option></select></label><button @click="createSession" :disabled="busy">新建会话</button><button @click="choose" :disabled="busy || !sessionId">刷新</button></div>
        <div class="backend-history" aria-live="polite"><p v-if="!messages.length">选择或新建会话后开始测试。</p><article v-for="m in messages" :key="m.id" :class="m.role"><strong>{{ m.role === 'user' ? '用户' : '助手' }}</strong><p>{{ m.content }}</p></article></div>
        <button v-if="moreHistory" @click="action(() => history(true))" :disabled="busy">加载后续历史</button>
        <form class="backend-composer" @submit.prevent="send"><label>本轮问题<textarea v-model="question" :disabled="busy || !sessionId" rows="3" maxlength="8000" placeholder="试试：你好 / 三个专家研究样本登记 / 请澄清我的请求" /></label><div class="backend-examples"><button type="button" :disabled="busy || !sessionId" @click="question = '请检索本地合成资料，介绍样本登记所需字段、编辑后重新确认和取消的规则，并引用资料。'">单Agent问题示例</button><button type="button" :disabled="busy || !sessionId" @click="question = '请安排三个专家：research_agent检索本地合成登记资料，consultation_agent解释登记流程，diagnostic_agent根据research结果检查确认与取消规则。请汇总并引用资料。'">多Agent问题示例</button><a href="#server-registration">打开服务端模拟登记</a></div><button :disabled="busy || !question.trim() || !sessionId">{{ busy ? '执行中…' : '发送问题' }}</button></form>
        <form v-if="run?.run_status === 'awaiting_input' || run?.run_status === 'paused'" class="backend-composer" @submit.prevent="resume"><label>补充问题<textarea v-model="clarification" rows="2" :required="run?.run_status === 'awaiting_input'" /></label><button :disabled="busy">恢复运行</button></form>
      </div>
      <aside class="backend-state">
        <h2>实际运行状态</h2>
        <template v-if="run"><dl><div><dt>运行</dt><dd>{{ labels[run.run_status] || run.run_status }}</dd></div><div><dt>结果</dt><dd>{{ run.result_status ? labels[run.result_status] || run.result_status : '尚未产出' }}</dd></div><div><dt>模型 / 工具请求</dt><dd>{{ run.model_calls ?? '未记录' }} / {{ run.tool_calls ?? '未记录' }}</dd></div><div><dt>规划</dt><dd>{{ run.plan_status === 'skipped' ? '简单请求，跳过规划' : labels[run.plan_status] || run.plan_status }}</dd></div></dl><p class="backend-runid">运行ID：{{ run.run_id }}</p><p v-if="run.safe_error_code" class="backend-error">{{ run.safe_error_code }}</p><p v-if="run.answer">{{ run.answer }}</p><button v-if="['running','awaiting_input','paused'].includes(run.run_status)" @click="cancel">取消运行</button><template v-if="run.task_results.length">
          <h3>任务与专家</h3><p>{{ run.task_count }} 个任务 · {{ run.distinct_agent_count }} 个实际参与角色</p>
          <article v-for="task in run.task_results" :key="task.task_id">
            <strong>{{ task.task_id }} · {{ task.agent_id }}</strong>
            <p>{{ labels[task.status] || task.status }} · 模型 {{ task.model_calls }} / 工具 {{ task.tool_calls }}</p>
            <p v-if="task.depends_on.length">依赖：{{ task.depends_on.join('、') }}</p>
            <p v-if="task.safe_error_code" class="backend-error">{{ task.safe_error_code }}</p>
          </article>
          <h3>证据检查</h3><p>{{ labels[run.evidence_status] || run.evidence_status }} · 补查 {{ run.refinement_count }} 次</p>
          <p>检查任务覆盖与引用一致性；医学正确性尚未核验。</p>
        </template><h3>上下文与后续维护</h3><p>本轮模式：{{ labels[run.mode] || run.mode }} · 格式修正 {{ run.schema_repair_count }} 次</p>
          <p>记忆读取：{{ labels[run.context_details.memory_status || ''] || run.context_details.memory_status || '未记录' }} · 命中 {{ run.context_details.memory_count ?? '未记录' }}</p>
          <p>记忆维护：{{ labels[run.memory_write_status] || run.memory_write_status }} · 摘要维护：{{ labels[run.summary_write_status] || run.summary_write_status }}</p>
          <p v-if="run.maintenance_error_code" class="backend-error">{{ run.maintenance_error_code }}</p>
          <template v-if="summary"><p>摘要：{{ labels[summary.status] || summary.status }} · 版本 {{ summary.version }} · 覆盖至消息 {{ summary.covered_until_seq }}</p><details v-if="summary.content"><summary>查看旧历史摘要</summary><p>{{ summary.content }}</p></details></template>
          <button :disabled="busy" @click="action(status)">刷新运行与维护状态</button>
          <h3 v-if="calls.length">实际 provider 请求</h3><ol><li v-for="(call, i) in calls" :key="i">{{ call.provider }} · {{ call.operation }}<small>{{ call.http_status ?? '等待响应' }}</small><p v-if="call.safe_error_code">{{ call.safe_error_code }}</p><p v-if="call.usage.total_tokens !== undefined">{{ call.usage.total_tokens }} token</p></li></ol>
          <h3>已记录的节点</h3><ol><li v-for="(e, i) in events" :key="i"><span>{{ stages[e.stage] || e.stage }}{{ e.task_id ? ` · ${e.task_id}` : '' }}</span><small>{{ labels[e.status] || e.status }}</small></li></ol><h3 v-if="run.sources.length">本轮资料</h3><article v-for="source in run.sources" :key="source.id"><strong>{{ source.source === 'pubmed' ? 'PubMed 索引 · 未读正文' : '本地资料 · 未核验' }}</strong><p>{{ source.title }}</p><p>{{ source.content }}</p><a v-if="source.url?.startsWith('https://')" :href="source.url" target="_blank" rel="noopener noreferrer">查看来源</a><p v-if="typeof source.score === 'number'">检索相似度 {{ source.score?.toFixed(3) }}<template v-if="typeof source.rerank_score === 'number'"> · 重排 {{ source.rerank_score?.toFixed(3) }}</template></p></article></template>
        <p v-else>运行后显示后端状态、调用次数和节点记录。</p>
      </aside>
    </div>
    <RegistrationPanel v-if="token && sessionId" :key="`${signedIn}:${sessionId}`" :session-id="sessionId" :api="api" />
    <section v-if="token" class="backend-memories"><h2>本人长期记忆</h2><p>仅保存明确的偏好、背景和持续目标。撤回后保留本地审计状态，云端删除由维护任务处理；原始聊天仍保留。</p>
      <p v-if="!facts.length">尚无筛选后的长期记忆。</p>
      <article v-for="fact in facts" :key="fact.id"><strong>{{ fact.key }} · {{ labels[fact.status] || fact.status }}</strong><p>本地版本 {{ fact.version }} · 已同步版本 {{ fact.synced_version }}</p><label>记忆内容<input v-model="drafts[fact.id]" maxlength="300" :disabled="busy" /></label><div><button :disabled="busy || !drafts[fact.id]?.trim()" @click="editFact(fact, 'update')">{{ fact.status === 'deleted' ? '恢复此偏好' : '保存纠正' }}</button><button v-if="fact.status !== 'deleted'" :disabled="busy" @click="editFact(fact, 'delete')">撤回记忆</button></div></article>
      <h3 v-if="jobs.length">已记录的维护任务</h3><ul><li v-for="job in jobs.slice(0, 10)" :key="job.id">{{ job.action }} · {{ labels[job.status] || job.status }} · 尝试 {{ job.attempts }} 次 <span v-if="job.safe_error_code">{{ job.safe_error_code }}</span></li></ul><button v-if="jobs.some(job => ['failed','uncertain','awaiting_remote'].includes(job.status))" :disabled="busy" @click="retryMaintenance">核对并重试维护</button>
    </section>
  </section>
</template>

<style scoped>
.backend-panel{font-family:Arial,"Microsoft YaHei",sans-serif;color:#202329}.backend-intro{color:#626773;margin:14px 0 24px;line-height:1.8}.backend-login,.backend-account,.backend-session{display:flex;flex-wrap:wrap;align-items:end;gap:12px;padding:20px;background:#fff;border:1px solid #d8dce3}.backend-account{justify-content:space-between;align-items:center}.backend-login small{width:100%;color:#626773}label{display:flex;flex-direction:column;gap:8px;font-size:12px}input,select,textarea{border:1px solid #bbc2ce;background:#fff;padding:10px;font:inherit;color:inherit;border-radius:0}input:focus,select:focus,textarea:focus{outline:2px solid #002FA7;outline-offset:2px}button{padding:10px 14px;border:1px solid #002FA7;background:#002FA7;color:#fff;font:inherit;font-size:12px;cursor:pointer}button:disabled{opacity:.45;cursor:not-allowed}.backend-error{color:#a32c32;background:#fff;padding:12px;border-left:3px solid #a32c32;overflow-wrap:anywhere}.backend-layout{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(250px,1fr);gap:20px;margin-top:20px}.backend-chat,.backend-state{background:#fff;border:1px solid #d8dce3;min-width:0}.backend-session{border:0;border-bottom:1px solid #d8dce3}.backend-session label{flex:1;min-width:150px}.backend-history{padding:20px;min-height:160px;max-height:440px;overflow:auto}.backend-history article{margin-bottom:16px;border-left:2px solid #d8dce3;padding:8px 14px}.backend-history article.user{border-color:#002FA7;background:#F7F7F8}.backend-history p,.backend-state p{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.8;font-size:12px}.backend-composer{display:flex;flex-direction:column;gap:12px;padding:20px;border-top:1px solid #d8dce3}.backend-composer button{align-self:end}.backend-state{padding:20px}.backend-state h2{font-size:17px;margin-bottom:18px}.backend-state h3{font-size:13px;margin:24px 0 12px}.backend-state dl div{display:flex;justify-content:space-between;gap:16px;border-bottom:1px solid #d8dce3;padding:12px 0;font-size:12px}.backend-state dt{color:#626773}.backend-state dd{margin:0;text-align:right}.backend-runid{color:#626773;font-size:10px!important}.backend-state ol{padding-left:20px}.backend-state li{font-size:12px;padding:8px 0}.backend-state li small{float:right;color:#626773}.backend-state article{border-top:1px solid #d8dce3;padding-top:12px;font-size:12px}@media(max-width:950px){.backend-layout{grid-template-columns:1fr}}@media(max-width:600px){.backend-login{align-items:stretch}.backend-login label{width:100%}.backend-layout{gap:16px}.backend-state,.backend-composer,.backend-history{padding:16px}}
.backend-memories{background:#fff;border:1px solid #d8dce3;padding:20px;margin-top:20px}.backend-memories h2{font-size:17px}.backend-memories p,.backend-memories li{font-size:12px;line-height:1.8}.backend-memories article{border-top:1px solid #d8dce3;padding:16px 0;font-size:12px}.backend-memories article div{display:flex;gap:12px;margin-top:12px}.backend-memories input{max-width:700px}.backend-state a{color:#002FA7;font-size:12px}.backend-state details{font-size:12px;margin:12px 0}
.backend-examples{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.backend-examples a{font-size:12px;color:#002FA7}.backend-examples button{background:#fff;color:#002FA7}
</style>
