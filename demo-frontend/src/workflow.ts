export type DraftStatus = 'incomplete' | 'ready' | 'confirmation_pending' | 'completed' | 'cancelled'
export type Fields = {
  project: string
  sampleType: string
  quantity: number | null
  receivedAt: string
  storage: string
  note: string
}
export type Draft = Fields & { id: string; revision: number; status: DraftStatus; createdAt: string }
export type Message = { id: string; role: 'user' | 'assistant'; text: string; time: string }
export type Audit = { id: string; action: string; detail: string; time: string }
export type Registration = Fields & { id: string; draftId: string; revision: number; confirmedAt: string; sampleIds: string[] }
export type DemoState = { version: 1; draft: Draft | null; messages: Message[]; audit: Audit[]; records: Registration[] }
export type Confirmation = { draftId: string; revision: number; signature: string }

export const PROJECTS = ['DEMO-A', 'DEMO-B']
export const STORAGES = ['DEMO-B 区域', 'DEMO-C 区域']
export const SAMPLE_TYPES = ['组织', '血液', '唾液']
export const STORAGE_KEY = 'medical-research-demo:v1'
export const now = () => new Date().toISOString()
export const uid = () => crypto.randomUUID()
export const today = () => new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())

export function fieldsOf(draft: Fields): Fields {
  return { project: draft.project, sampleType: draft.sampleType, quantity: draft.quantity, receivedAt: draft.receivedAt, storage: draft.storage, note: draft.note }
}

export function validate(fields: Fields): Record<string, string> {
  const errors: Record<string, string> = {}
  if (!PROJECTS.includes(fields.project)) errors.project = '请选择一个演示项目'
  if (!SAMPLE_TYPES.includes(fields.sampleType)) errors.sampleType = '请选择样本类型'
  if (!Number.isInteger(fields.quantity) || Number(fields.quantity) < 1 || Number(fields.quantity) > 20) errors.quantity = '数量须为 1–20 的整数（演示规则）'
  if (!/^\d{4}-\d{2}-\d{2}$/.test(fields.receivedAt) || !Number.isFinite(Date.parse(fields.receivedAt)) || new Date(fields.receivedAt).toISOString().slice(0, 10) !== fields.receivedAt) errors.receivedAt = '请填写有效接收日期'
  if (!STORAGES.includes(fields.storage)) errors.storage = '请选择一个演示存储区域'
  if (fields.note.length > 300) errors.note = '备注最多 300 字（演示规则）'
  return errors
}

export function addMessage(state: DemoState, role: Message['role'], text: string) {
  state.messages.push({ id: uid(), role, text: text.slice(0, 2000), time: now() })
  state.messages = state.messages.slice(-40)
}

export function log(state: DemoState, action: string, detail: string) {
  state.audit.unshift({ id: uid(), action, detail, time: now() })
  state.audit = state.audit.slice(0, 200)
}

export function parseInput(text: string): Partial<Fields> {
  const fields: Partial<Fields> = {}
  const quantity = text.match(/(\d+)\s*(?:份|个|管)/)
  if (quantity) fields.quantity = Number(quantity[1])
  for (const type of SAMPLE_TYPES) if (text.includes(type)) fields.sampleType = type
  const project = text.match(/(?:DEMO-)?([A-Za-z])\s*(?:研究)?项目|项目\s*(?:DEMO-)?([A-Za-z])/)
  if (project) fields.project = `DEMO-${(project[1] || project[2])!.toUpperCase()}`
  const storage = text.match(/(?:存储在|放在|存放在)?\s*(?:DEMO-)?([A-Za-z])\s*(?:区域|区)|(?:区域|存储区域)\s*(?:DEMO-)?([A-Za-z])/)
  if (storage) fields.storage = `DEMO-${(storage[1] || storage[2])!.toUpperCase()} 区域`
  const date = text.match(/\d{4}-\d{2}-\d{2}/)
  if (date) fields.receivedAt = date[0]
  else if (text.includes('今天')) fields.receivedAt = today()
  return fields
}

export function beginDraft(state: DemoState, input: string) {
  if (state.draft && !['completed', 'cancelled'].includes(state.draft.status)) throw new Error('请先完成或取消当前草稿')
  const fields: Fields = { project: '', sampleType: '', quantity: null, receivedAt: '', storage: '', note: '', ...parseInput(input) }
  state.draft = { ...fields, id: uid(), revision: 1, createdAt: now(), status: Object.keys(validate(fields)).length ? 'incomplete' : 'ready' }
  log(state, '创建草稿', '从演示输入提取字段，尚未登记')
}

export function editDraft(state: DemoState, fields: Fields) {
  if (!state.draft || ['completed', 'cancelled'].includes(state.draft.status)) throw new Error('当前草稿不能编辑')
  if (JSON.stringify(fieldsOf(state.draft)) === JSON.stringify(fields)) return
  Object.assign(state.draft, fields, { revision: state.draft.revision + 1, status: Object.keys(validate(fields)).length ? 'incomplete' : 'ready' })
  log(state, '更新草稿', `草稿更新为第 ${state.draft.revision} 版，需重新确认`)
}

export function requestConfirmation(state: DemoState): Confirmation {
  const draft = state.draft
  if (!draft || !['ready', 'confirmation_pending'].includes(draft.status) || Object.keys(validate(draft)).length) throw new Error('请先补全并校验草稿')
  draft.status = 'confirmation_pending'
  log(state, '请求确认', `等待明确确认第 ${draft.revision} 版草稿`)
  return { draftId: draft.id, revision: draft.revision, signature: JSON.stringify(fieldsOf(draft)) }
}

export function dismissConfirmation(state: DemoState) {
  if (state.draft?.status === 'confirmation_pending') {
    state.draft.status = 'ready'
    log(state, '返回编辑', '未确认，没有新增登记记录')
  }
}

export function commitDraft(state: DemoState, confirmation: Confirmation): Registration {
  const draft = state.draft
  // A completed operation can be replayed safely, but a different revision cannot.
  const existing = state.records.find(record => record.draftId === confirmation.draftId && record.revision === confirmation.revision)
  if (existing && JSON.stringify(fieldsOf(existing)) === confirmation.signature) return existing
  if (!draft || draft.status !== 'confirmation_pending' || draft.id !== confirmation.draftId || draft.revision !== confirmation.revision || JSON.stringify(fieldsOf(draft)) !== confirmation.signature || Object.keys(validate(draft)).length) throw new Error('确认已失效，请重新核对当前草稿')
  if (state.records.length >= 100) throw new Error('演示记录已达到 100 批上限，请清空演示数据后继续')
  const record: Registration = {
    ...fieldsOf(draft), id: uid(), draftId: draft.id, revision: draft.revision, confirmedAt: now(),
    sampleIds: Array.from({ length: draft.quantity! }, (_, index) => `SYN-${draft.id.slice(0, 6).toUpperCase()}-${String(index + 1).padStart(2, '0')}`),
  }
  state.records.unshift(record)
  draft.status = 'completed'
  log(state, '确认登记', `${record.quantity} 份${record.sampleType}样本登记至当前浏览器；第 ${record.revision} 版`)
  return record
}

export function cancelDraft(state: DemoState) {
  if (!state.draft || ['completed', 'cancelled'].includes(state.draft.status)) return
  state.draft.status = 'cancelled'
  log(state, '取消草稿', '停止当前登记流程，没有新增登记记录')
}

export function initialState(): DemoState {
  const state: DemoState = { version: 1, draft: null, messages: [], audit: [], records: [] }
  addMessage(state, 'assistant', '你好，我可以协助整理样本登记草稿。先用一条合成示例体验完整流程；你可以编辑草稿字段，再确认或取消。')
  const example = '今天收到了5份组织样本，属于A项目，存储在B区域。'
  addMessage(state, 'user', example)
  beginDraft(state, example)
  addMessage(state, 'assistant', '已整理为 5 份组织样本的登记草稿，关联 DEMO-A，存储于 DEMO-B 区域。演示字段已齐全，请核对草稿面板；当前还没有登记记录。')
  return state
}

export function restoreState(raw: string | null): DemoState | null {
  if (!raw || raw.length > 1_000_000) return null
  try {
    const data = JSON.parse(raw) as DemoState
    const text = (value: unknown, max = 2000) => typeof value === 'string' && value.length <= max
    const fieldsShape = (value: Fields) => !!value && text(value.project, 60) && text(value.sampleType, 60) && (value.quantity === null || typeof value.quantity === 'number') && text(value.receivedAt, 10) && text(value.storage, 60) && text(value.note, 300)
    if (data.version !== 1 || !Array.isArray(data.records) || data.records.length > 100 || !Array.isArray(data.messages) || data.messages.length > 40 || !Array.isArray(data.audit) || data.audit.length > 200) return null
    if (data.draft && (!fieldsShape(data.draft) || !text(data.draft.id, 80) || !Number.isInteger(data.draft.revision) || data.draft.revision < 1 || !['incomplete', 'ready', 'confirmation_pending', 'completed', 'cancelled'].includes(data.draft.status) || !text(data.draft.createdAt, 40))) return null
    if (!data.messages.every(message => message && text(message.id, 80) && ['assistant', 'user'].includes(message.role) && text(message.text) && text(message.time, 40))) return null
    if (!data.audit.every(event => event && text(event.id, 80) && text(event.action, 80) && text(event.detail) && text(event.time, 40))) return null
    if (!data.records.every(record => fieldsShape(record) && !Object.keys(validate(record)).length && text(record.id, 80) && text(record.draftId, 80) && Number.isInteger(record.revision) && record.revision > 0 && text(record.confirmedAt, 40) && Array.isArray(record.sampleIds) && record.sampleIds.length === record.quantity && record.sampleIds.every(id => text(id, 80)))) return null
    if (data.draft && !['completed', 'cancelled'].includes(data.draft.status)) data.draft.status = Object.keys(validate(data.draft)).length ? 'incomplete' : 'ready'
    return data
  } catch { return null }
}
