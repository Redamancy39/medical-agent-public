<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

type Fields = { project: string; sample_type: string; quantity: number | null; received_at: string; storage: string; note: string }
type Draft = { id: string; revision: number; status: string; fields: Fields; issues: Record<string, string>; session_id: string }
type RecordRow = { id: string; draft_id: string; revision: number; fields: Fields; sample_ids: string[]; created_at: string }
type Result = { draft: Draft; record: RecordRow | null; confirmation_token?: string; replayed: boolean }
type Audit = { action: string; revision: number; created_at: string }
const props = defineProps<{ sessionId: string; api: <T>(path: string, method?: string, body?: unknown) => Promise<T> }>()
const text = ref('请登记3份血液样本，项目DEMO-A，2026-10-13接收，存储在DEMO-B区域')
const options = ref<{ projects: string[]; sample_types: string[]; storages: string[] } | null>(null)
const drafts = ref<Draft[]>([]), selected = ref(''), current = ref<Draft | null>(null), fields = ref<Fields | null>(null)
const rows = ref<RecordRow[]>([]), audit = ref<Audit[]>([]), reviewToken = ref(''), checked = ref(false)
const busy = ref(false), error = ref(''), notice = ref('')
const labels: Record<string, string> = { incomplete: '等待补充字段', ready: '草稿待核对', awaiting_confirmation: '等待明确确认', completed: '已登记', cancelled: '已取消', prepare: '生成草稿', edit: '保存编辑', review: '核对版本', confirm: '确认登记', cancel: '取消草稿' }
const dirty = computed(() => fields.value && current.value && JSON.stringify(fields.value) !== JSON.stringify(current.value.fields))
const closed = computed(() => current.value && ['completed', 'cancelled'].includes(current.value.status))
let pending: { signature: string; request_id: string } | null = null
watch(fields, () => { reviewToken.value = ''; checked.value = false }, { deep: true, flush: 'sync' })

async function action(work: () => Promise<void>) {
  busy.value = true; error.value = ''; notice.value = ''
  try { await work() } catch (e) { error.value = (e as Error).message } finally { busy.value = false }
}
async function refreshLists() {
  drafts.value = (await props.api<{ items: Draft[] }>(`/sessions/${props.sessionId}/registration-drafts`)).items
  rows.value = (await props.api<{ items: RecordRow[] }>('/registration-records')).items
}
async function show(value: Result) {
  current.value = value.draft; selected.value = value.draft.id
  fields.value = { ...value.draft.fields }; reviewToken.value = value.confirmation_token || ''; checked.value = false
  audit.value = (await props.api<{ items: Audit[] }>(`/registration-drafts/${value.draft.id}/audit`)).items
  await refreshLists()
}
async function load() {
  await action(async () => {
    await refreshLists()
    if (selected.value) await show(await props.api<Result>(`/registration-drafts/${selected.value}`))
    else { current.value = null; fields.value = null; reviewToken.value = ''; audit.value = [] }
  })
}
async function mutate(path: string, payload: object): Promise<Result> {
  const signature = JSON.stringify([path, payload])
  if (pending?.signature !== signature) pending = { signature, request_id: crypto.randomUUID() }
  const result = await props.api<Result>(path, 'POST', { ...payload, request_id: pending!.request_id })
  pending = null
  return result
}
async function prepare() {
  await action(async () => {
    const result = await mutate(`/sessions/${props.sessionId}/registration-drafts`, { text: text.value.trim() })
    await show(result); notice.value = '草稿已保存到本地SQL，尚未登记。请补充缺失字段或核对当前版本。'
  })
}
async function operate(operation: 'edit' | 'review' | 'confirm' | 'cancel') {
  if (!current.value || (operation === 'confirm' && (!checked.value || !reviewToken.value || dirty.value))) return
  await action(async () => {
    const result = await mutate(`/registration-drafts/${current.value!.id}/${operation}`, {
      revision: current.value!.revision,
      ...(operation === 'edit' ? { fields: fields.value } : {}),
      ...(operation === 'confirm' ? { explicit_confirm: true, confirmation_token: reviewToken.value } : {}),
    })
    await show(result)
    notice.value = operation === 'confirm' ? `已写入一批模拟记录${result.replayed ? '（幂等重放）' : ''}。` : operation === 'cancel' ? '草稿已取消，没有新增登记记录。' : operation === 'edit' ? '编辑已保存，旧确认失效，请核对新版本。' : '请核对下方当前版本，勾选后再明确确认。'
  })
}
onMounted(() => { void action(async () => { options.value = await props.api('/registration-options'); await refreshLists() }) })
</script>

<template>
  <section id="server-registration" class="registration-panel" aria-label="服务端模拟样本登记">
    <header><div><h2>服务端模拟样本登记</h2><p>登记数据保存在本地SQL，按登录用户隔离。此处仅使用DEMO项目和合成样本；咨询回答不会自动生成登记记录。</p></div><button :disabled="busy" @click="load">刷新登记状态</button></header>
    <p v-if="error" class="error" role="alert">{{ error }}</p><p v-if="notice" class="notice" role="status">{{ notice }}</p>
    <form @submit.prevent="prepare"><label>模拟登记输入<textarea v-model="text" rows="2" maxlength="2000" :disabled="busy" required /></label><button :disabled="busy || !text.trim()">生成服务端草稿</button></form>
    <label>已保存草稿<select v-model="selected" :disabled="busy" @change="load"><option value="">请选择草稿</option><option v-for="draft in drafts" :key="draft.id" :value="draft.id">{{ draft.id.slice(0, 8) }} · 第{{ draft.revision }}版 · {{ labels[draft.status] }}</option></select></label>
    <div v-if="current && fields" class="draft">
      <div class="draft-heading"><h3>当前草稿 · 第{{ current.revision }}版</h3><strong>{{ labels[current.status] }}</strong></div>
      <p>草稿ID：{{ current.id }}</p>
      <p v-if="Object.keys(current.issues).length">需要补充或纠正：{{ Object.values(current.issues).join('；') }}</p>
      <div class="field-grid"><label>演示项目<select v-model="fields.project" :disabled="busy || !!closed"><option value="">请选择</option><option v-for="item in options?.projects" :key="item">{{ item }}</option></select></label>
        <label>样本类型<select v-model="fields.sample_type" :disabled="busy || !!closed"><option value="">请选择</option><option v-for="item in options?.sample_types" :key="item">{{ item }}</option></select></label>
        <label>样本数量<input v-model.number="fields.quantity" type="number" min="1" max="20" :disabled="busy || !!closed" /></label>
        <label>接收日期<input v-model="fields.received_at" type="date" :disabled="busy || !!closed" /></label>
        <label>存储区域<select v-model="fields.storage" :disabled="busy || !!closed"><option value="">请选择</option><option v-for="item in options?.storages" :key="item">{{ item }}</option></select></label>
        <label>备注<input v-model="fields.note" maxlength="300" :disabled="busy || !!closed" /></label></div>
      <p v-if="dirty">有未保存编辑。先保存，当前确认不能提交。</p>
      <div v-if="!closed" class="actions"><button :disabled="busy" @click="operate('edit')">保存草稿编辑</button><button :disabled="busy || !!dirty || Object.keys(current.issues).length > 0" @click="operate('review')">核对当前版本</button><button class="secondary" :disabled="busy" @click="operate('cancel')">取消服务端草稿</button></div>
      <div v-if="reviewToken && !closed" class="confirmation"><h3>确认对象：第{{ current.revision }}版草稿</h3><p>{{ fields.project }} · {{ fields.quantity }}份{{ fields.sample_type }} · {{ fields.received_at }} · {{ fields.storage }}</p><label class="check"><input v-model="checked" type="checkbox" :disabled="busy" />我已核对以上当前版本，明确确认写入模拟登记</label><button :disabled="busy || !checked || !!dirty" @click="operate('confirm')">明确确认模拟登记</button></div>
      <details><summary>查看登记审计</summary><ol><li v-for="(item, i) in audit" :key="i">{{ labels[item.action] }} · 第{{ item.revision }}版 · {{ item.created_at }}</li></ol></details>
    </div>
    <h3>本人服务端模拟记录 · {{ rows.length }}批</h3><p v-if="!rows.length">尚无已确认登记。草稿、核对和取消不会增加这里的记录。</p>
    <article v-for="row in rows" :key="row.id" class="record"><strong>{{ row.fields.project }} · {{ row.fields.quantity }}份{{ row.fields.sample_type }}</strong><p>登记ID：{{ row.id }} · 草稿第{{ row.revision }}版</p><p>{{ row.fields.received_at }} · {{ row.fields.storage }}</p><details><summary>查看合成样本编号</summary><p>{{ row.sample_ids.join('、') }}</p></details></article>
  </section>
</template>

<style scoped>
.registration-panel{margin-top:20px;padding:20px;background:#fff;border:1px solid #d8dce3;color:#202329;font-family:Arial,"Microsoft YaHei",sans-serif}.registration-panel header,.draft-heading{display:flex;justify-content:space-between;align-items:start;gap:16px}.registration-panel h2{font-size:17px}.registration-panel h3{font-size:14px;margin:18px 0 10px}.registration-panel p,li,summary{font-size:12px;line-height:1.8;overflow-wrap:anywhere}.registration-panel header p{color:#626773}.registration-panel label{display:flex;flex-direction:column;gap:8px;font-size:12px}.registration-panel form{display:flex;gap:12px;align-items:end;margin:18px 0}.registration-panel form label{flex:1}.registration-panel button{padding:10px 14px;background:#002FA7;color:#fff;border:1px solid #002FA7;font:inherit;font-size:12px;cursor:pointer}.registration-panel button:disabled{opacity:.45;cursor:not-allowed}.registration-panel input,.registration-panel select,.registration-panel textarea{border:1px solid #bbc2ce;border-radius:0;padding:10px;background:#fff;color:inherit;font:inherit}.registration-panel input:focus,.registration-panel select:focus,.registration-panel textarea:focus{outline:2px solid #002FA7;outline-offset:2px}.field-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:16px 0}.draft,.record{border-top:1px solid #d8dce3;margin-top:20px;padding-top:16px}.actions{display:flex;flex-wrap:wrap;gap:12px;margin:16px 0}.registration-panel .secondary{background:#fff;color:#002FA7}.confirmation{border-left:3px solid #002FA7;background:#F7F7F8;padding:12px 16px;margin:16px 0}.confirmation .check{display:flex;flex-direction:row;align-items:center;margin:14px 0}.error{border-left:3px solid #a32c32;color:#a32c32;padding:10px}.notice{border-left:3px solid #002FA7;padding:10px}@media(max-width:700px){.field-grid{grid-template-columns:1fr 1fr}.registration-panel header,.registration-panel form{flex-direction:column;align-items:stretch}}@media(max-width:450px){.field-grid{grid-template-columns:1fr}}
</style>
