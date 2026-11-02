// Browser-only QA: all /api requests are intercepted here before App mounts.
// This page never sends credentials/questions to the real backend or cloud.
import { createApp } from 'vue'
import App from '../src/App.vue'
import { MOCK_SCENARIOS } from '../src/mockMedicalScenarios'
import type { RunOut } from '../src/types'
import '../src/style.css'

const sid = 'sim-ui-progress-session'
let request: { question: string; request_id: string } | null = null
let run: RunOut | null = null
let phase = 'plan'
let disconnected = false
let recordVisible = false
let finish: (() => void) | null = null
const calls: string[] = []

const controls = document.querySelector('#qa-controls')!
controls.setAttribute('style', 'position:fixed;bottom:0;left:0;z-index:1000;background:white;border:1px solid #aaa;font-size:11px;max-width:100%;')
controls.innerHTML = '<span>离线界面回归 · 无云调用 </span><button>模拟规划记录</button><button>模拟检索记录</button><button>模拟引用核对</button><button>模拟进度断联</button><button>恢复进度连接</button><button>完成本地回归</button><output id="qa-api-count">0</output>'
const buttons = controls.querySelectorAll('button')
buttons[0]!.onclick = () => { phase = 'plan'; recordVisible = true }
buttons[1]!.onclick = () => { phase = 'task_tools'; recordVisible = true }
buttons[2]!.onclick = () => { phase = 'review_answer'; recordVisible = true }
buttons[3]!.onclick = () => { disconnected = true }
buttons[4]!.onclick = () => { disconnected = false }
buttons[5]!.onclick = () => { finish?.() }

function snapshot(): RunOut | null {
  if (!run) return null
  if (run.run_status !== 'running') return run
  return { ...run, stage: phase, reviewer_status: phase === 'review_answer' ? 'running' : 'not_run' }
}

const nativeFetch = window.fetch.bind(window)
window.fetch = async (input, init) => {
  const path = new URL(typeof input === 'string' ? input : input instanceof URL ? input.href : input.url, location.href).pathname
  if (!path.startsWith('/api/')) return nativeFetch(input, init)
  calls.push(`${init?.method || 'GET'} ${path}`)
  document.querySelector('#qa-api-count')!.textContent = `接口请求 ${calls.length} 次`
  document.querySelector('#qa-api-count')!.setAttribute('data-calls', JSON.stringify(calls))
  const result = (value: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } }))
  if (path === '/api/health') return result({ status: 'ok', mode: 'offline_fake', knowledge_profile: 'medical', providers: {} })
  if (path === '/api/auth/register') return result({ username: 'ui_demo' }, 201)
  if (path === '/api/auth/login') return result({ access_token: 'offline-ui-fixture-no-server-privilege' })
  if (path === '/api/auth/me') return result({ username: 'ui_demo' })
  if (path === '/api/memories' || path === '/api/maintenance/jobs') return result({ items: [] })
  if (path === '/api/sessions') return result({ items: [{ id: sid, title: '离线进度回归（无云调用）' }] })
  if (path.endsWith('/summary')) return result({ content: null, version: 0 })
  if (path.endsWith('/runs')) {
    if (disconnected) throw new TypeError('QA: simulated status connection loss')
    return result(run && (recordVisible || run.run_status === 'finished') ? [snapshot()] : [])
  }
  if (path.endsWith('/events')) return result({ items: run ? [{ stage: phase, task_id: null, status: 'completed' }] : [] })
  if (path.endsWith('/providers')) return result({ items: [] })
  if (path.endsWith('/messages')) return result({ items: run?.run_status === 'finished' ? [
    { id: 'sim-user', run_id: run.run_id, role: 'user', seq: 1, content: request!.question },
    { id: 'sim-assistant', run_id: run.run_id, role: 'assistant', seq: 2, content: run.answer },
  ] : [], has_more: false })
  if (path.endsWith('/chat') && init?.method === 'POST') {
    request = JSON.parse(init.body as string)
    phase = 'plan'
    recordVisible = false
    const fixture = structuredClone(MOCK_SCENARIOS[1]!.turns[0]!.run)
    run = { ...fixture, run_id: `sim-ui-progress-run-${calls.length}`, session_id: sid, request_id: request!.request_id,
      mode: 'offline_fake', run_status: 'running', result_status: null, answer: null, stage: phase,
      sources: [], claim_reviews: [], omitted_claim_count: 0, citation_support_status: 'not_run',
      reviewer_status: 'not_run', atomization_status: 'not_run', review_rewrite_status: 'not_run', task_results: [] }
    await new Promise<void>(resolve => { finish = resolve })
    run = { ...fixture, run_id: run.run_id, session_id: sid, request_id: request!.request_id, mode: 'offline_fake' }
    return result(run)
  }
  return result({ error: { message: '离线回归未实现该接口' } }, 404)
}
createApp(App).mount('#app')
