// Run with Codex CUA tabs; assertions read DOM and interact with visible controls.
import assert from 'node:assert/strict'
import { writeFile } from 'node:fs/promises'

export async function checkReading(tab) {
  const checks = []
  const state = () => tab.getAXState({ emit: false })
  const button = name => tab.playwright.getByRole('button', { name, exact: true })
  const prose = () => tab.playwright.evaluate(() => [...document.querySelectorAll('.prose-paragraph')].map(e =>
    [...e.querySelectorAll('.claim-sentence>span:first-child,.plain-text-segment')].map(n => n.textContent).join('')).join('\n'))
  const check = (name, actual, expected) => { assert.deepEqual(JSON.parse(JSON.stringify(actual)), expected, name); checks.push({ name, passed: true }) }
  const before = await prose()
  check('section headings are 16px and blue citation links keep a transparent background', await tab.playwright.evaluate(() => ({
    headings: [...document.querySelectorAll('.para-section-label')].every(e => getComputedStyle(e).fontSize === '16px' && Number(getComputedStyle(e).fontWeight) >= 600),
    citations: [...document.querySelectorAll('.claim-cite-btn')].every(e => getComputedStyle(e).color === 'rgb(0, 47, 167)'),
    sources: [...document.querySelectorAll('.source-pill-btn')].every(e => getComputedStyle(e).color === 'rgb(0, 47, 167)'),
  })), { headings: true, citations: true, sources: true })
  check('citations are transparent superscripts with no inline anchor-count badges', await tab.playwright.evaluate(() => ({
    transparent: [...document.querySelectorAll('.claim-cite-btn')].every(e => getComputedStyle(e).backgroundColor === 'rgba(0, 0, 0, 0)'),
    counts: document.querySelectorAll('.claim-cite-btn .anchor-count').length,
    labels: [...document.querySelectorAll('.claim-cite-btn')].every(e => /^查看第 \d+ 句的原文依据$/.test(e.getAttribute('aria-label'))),
  })), { transparent: true, counts: 0, labels: true })
  await button('本轮回答说明 →').click(); await state()
  check('all three detail groups are collapsed by default', await tab.playwright.evaluate(() => ({
    count: document.querySelectorAll('.trace-disclosure').length,
    open: document.querySelectorAll('.trace-disclosure[open]').length,
  })), { count: 3, open: 0 })
  await tab.playwright.getByText('开发者诊断', { exact: true }).click(); await state()
  check('developer diagnostics remain available on demand', await tab.playwright.locator('.secondary-trace-body').isVisible(), true)
  await tab.playwright.getByText('开发者诊断', { exact: true }).click(); await state()
  await button('查看第 2 句的原文依据').click(); await state()
  check('citation still locates every English anchor for the selected fact', await tab.playwright.locator('.selected-claim-locator .locator-quote').count(), 3)
  check('citation and panel changes preserve every body character', await prose(), before)
  await button('收起右侧详情栏').click(); await state()
  await button('HbA1c 与指尖血糖对比及空腹要求 部分完成 (省略2条)').click(); await state()
  await button('为什么未采用？').click(); await state()
  check('omission entry opens the disclosure and only the two excluded sentences', await tab.playwright.evaluate(() => ({
    open: document.querySelector('details[aria-label="原子事实审核与省略记录"]')?.open,
    excluded: document.querySelectorAll('.claim-list .excluded-claim-card').length,
    supported: document.querySelectorAll('.claim-list .claim-card.supported').length,
    explanation: document.querySelector('.omitted-filter-banner')?.textContent.includes('模型核对误判'),
  })), { open: true, excluded: 2, supported: 0, explanation: true })
  return checks
}

export async function checkProgress(tab, folder) {
  const checks = []
  const state = () => tab.getAXState({ emit: false })
  const button = name => tab.playwright.getByRole('button', { name, exact: true })
  const check = (name, actual, expected) => { assert.deepEqual(JSON.parse(JSON.stringify(actual)), expected, name); checks.push({ name, passed: true }) }
  const waitText = text => tab.playwright.getByText(text, { exact: true }).waitFor({ state: 'visible', timeoutMs: 6000 })
  await tab.playwright.getByRole('tab', { name: /后端联调/ }).click(); await state()
  await tab.playwright.getByLabel('本地用户名 (3–40 位字母/数字/下划线)', { exact: true }).fill('ui_demo')
  await tab.playwright.getByLabel('登录密码 (至少 8 位字符)', { exact: true }).fill('offline-qa-only')
  await button('登录已有账号').click(); await state()
  await tab.playwright.getByLabel('后端联调问题输入', { exact: true }).fill('离线界面回归：验证等待阶段')
  await button('发送提问').click(); await state()
  check('pending request waits for its own record with no numeric progress', await tab.playwright.evaluate(() => ({
    text: document.querySelector('.run-progress-detail')?.textContent.trim(),
    numeric: document.querySelector('[role="progressbar"]')?.getAttribute('aria-valuenow'),
    current: document.querySelectorAll('.run-progress-steps .current').length,
  })), { text: '正在提交，等待后端返回进度。', numeric: null, current: 0 })
  await button('模拟规划记录').click(); await state(); await waitText('后端最近记录：理解问题。')
  check('planner checkpoint remains in the understanding phase', await tab.playwright.locator('.run-progress-steps .current').innerText(), '理解问题')
  await button('模拟检索记录').click(); await state(); await waitText('后端最近记录：查询与作答。')
  await button('模拟引用核对').click(); await state(); await waitText('正在逐句核对回答与原文依据。')
  check('review metadata updates the live progress phase', await tab.playwright.locator('.run-progress-steps .current').innerText(), '核对引用')
  await writeFile(folder+'/03-progress-offline.png', await tab.getScreenshot({ emit: false }))
  await button('模拟进度断联').click(); await state()
  await waitText('进度更新暂时中断，正在等待连接恢复；尚未确认新的处理状态。')
  check('status connection failure pauses the indicator and preserves the last state', await tab.playwright.locator('.run-progress-track.is-delayed').count(), 1)
  await button('恢复进度连接').click(); await state(); await waitText('正在逐句核对回答与原文依据。')
  const callsWhileWaiting = await tab.playwright.locator('#qa-api-count').getAttribute('data-calls')
  const calls = JSON.parse(callsWhileWaiting)
  const during = calls.slice(calls.findIndex(c => c.startsWith('POST ') && c.endsWith('/chat')) + 1)
  check('waiting polls only run status and events, without repeatedly loading maintenance or provider records', during.every(c => c.endsWith('/runs') || c.endsWith('/events')), true)
  await button('完成本地回归').click(); await state()
  await tab.playwright.locator('.run-progress').waitFor({ state: 'hidden', timeoutMs: 6000 })
  check('finished answer leaves the right panel closed', await tab.playwright.locator('.med-inspector-col').isVisible(), false)
  await tab.playwright.getByLabel('后端联调问题输入', { exact: true }).fill('离线界面回归：第二轮不可借用旧进度')
  await button('发送提问').click(); await state()
  await waitText('正在提交，等待后端返回进度。')
  check('new request does not inherit the previous answer review status', await tab.playwright.locator('.run-progress-steps .current').count(), 0)
  await button('完成本地回归').click(); await state()
  await tab.playwright.locator('.run-progress').waitFor({ state: 'hidden', timeoutMs: 6000 })
  return checks
}

export async function checkMobileOmission(tab, browser, folder) {
  const checks = []
  const viewport = await browser.capabilities.get('viewport')
  const state = () => tab.getAXState({ emit: false })
  const button = name => tab.playwright.getByRole('button', { name, exact: true })
  const check = (name, actual, expected) => { assert.deepEqual(JSON.parse(JSON.stringify(actual)), expected, name); checks.push({ name, passed: true }) }
  try {
    await viewport.set({ width: 390, height: 844 }); await state()
    await button('打开会话导航').click(); await state()
    await button('HbA1c 与指尖血糖对比及空腹要求 部分完成 (省略2条)').click(); await state()
    await button('为什么未采用？').click(); await state()
    check('mobile omission opens its disclosure and focuses inside the evidence modal', await tab.playwright.evaluate(() => ({
      modal: document.querySelector('.med-inspector-col')?.getAttribute('aria-modal'),
      disclosure: document.querySelector('details[aria-label="原子事实审核与省略记录"]')?.open,
      focusInside: document.querySelector('.med-inspector-col')?.contains(document.activeElement),
    })), { modal: 'true', disclosure: true, focusInside: true })
    check('mobile omission does not automatically expand tasks or developer diagnostics', await tab.playwright.evaluate(() =>
      document.querySelectorAll('.trace-disclosure[open]').length), 1)
    await writeFile(folder+'/06-mobile-omission.png', await tab.getScreenshot({ emit: false }))
    await tab.playwright.locator('.back-all-claims-btn').press('Escape'); await state()
    check('mobile omission Escape restores its exact explanation trigger', await tab.playwright.evaluate(() => document.activeElement?.textContent.trim()), '为什么未采用？')
    return checks
  } finally { await viewport.reset() }
}
