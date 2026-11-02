// Run inside Codex cua_repl with a fresh simulation tab and its browser handle.
// Uses public UI actions and read-only DOM inspection; never calls the backend.
import assert from 'node:assert/strict'

export async function checkDrawers(tab, browser) {
  const checks = []
  const button = name => tab.playwright.getByRole('button', { name, exact: true })
  const state = () => tab.getAXState({ emit: false })
  const focus = () => tab.playwright.evaluate(() => ({
    label: document.activeElement?.getAttribute('aria-label'),
    text: document.activeElement?.textContent?.trim(),
    tag: document.activeElement?.tagName,
    role: document.activeElement?.getAttribute('role'),
    drawer: document.activeElement?.closest('[role="dialog"]')?.getAttribute('aria-label'),
  }))
  const check = (name, actual, expected) => {
    // Normalize values crossing the browser bridge into this module's JS realm.
    assert.deepEqual(JSON.parse(JSON.stringify(actual)), JSON.parse(JSON.stringify(expected)), name)
    checks.push({ name, passed: true })
  }
  const viewport = await browser.capabilities.get('viewport')
  try {
    await viewport.set({ width: 390, height: 844 })
    await state()
    check('390px has no horizontal overflow', await tab.playwright.evaluate(() => [innerWidth, document.documentElement.scrollWidth]), [390, 390])
    await button('打开会话导航').click()
    await state()
    check('navigation receives initial focus', (await focus()).label, '关闭会话导航')
    check('navigation is modal and background is inert', await tab.playwright.evaluate(() => ({
      modal: document.querySelector('.med-sidebar')?.getAttribute('aria-modal'),
      background: [...document.querySelectorAll('header.med-topbar,main.med-center')].every(e => e.hasAttribute('inert') && e.getAttribute('aria-hidden') === 'true'),
    })), { modal: 'true', background: true })
    const last = '血压 120/80 含义与测前准备 服务暂不可用'
    await button(last).press('Tab')
    await state()
    check('navigation Tab wraps forward', (await focus()).label, '关闭会话导航')
    await button('关闭会话导航').press('Shift+Tab')
    await state()
    check('navigation Tab wraps backward', (await focus()).text, '血压 120/80 含义与测前准备服务暂不可用')
    await button(last).press('Escape')
    await state()
    check('navigation Escape restores trigger', (await focus()).label, '打开会话导航')
    await button('打开会话导航').click()
    await state()
    await button('关闭会话导航').click()
    await state()
    check('navigation close restores trigger', (await focus()).label, '打开会话导航')
    await button('查看第 2 句的原文依据').click()
    await state()
    check('citation receives focus inside modal', (await focus()).drawer, '引用证据与执行审核抽屉')
    await tab.playwright.getByRole('link', { name: '打开 NLM 原始页面', exact: true }).last().press('Tab')
    await state()
    check('evidence Tab wraps forward', (await focus()).role, 'tab')
    await tab.playwright.getByRole('tab', { name: '引用证据与原文 2', exact: true }).press('Shift+Tab')
    await state()
    check('evidence Tab wraps backward', (await focus()).tag, 'A')
    await button('关闭详情抽屉').press('Escape')
    await state()
    check('citation Escape restores exact fact trigger', (await focus()).label, '查看第 2 句的原文依据')
    check('closed drawers are hidden and inert', await tab.playwright.evaluate(() =>
      [...document.querySelectorAll('.med-sidebar,.med-inspector-col')].every(e => e.hasAttribute('inert') && getComputedStyle(e).display === 'none')), true)
    await viewport.set({ width: 360, height: 800 })
    await state()
    check('360px has no horizontal overflow', await tab.playwright.evaluate(() => [innerWidth, document.documentElement.scrollWidth]), [360, 360])
    await button('打开会话导航').click()
    await state()
    await viewport.set({ width: 1280, height: 720 })
    await state()
    check('desktop restores ordinary navigation and background', await tab.playwright.evaluate(() => ({
      width: innerWidth,
      role: document.querySelector('.med-sidebar')?.getAttribute('role'),
      inert: document.querySelector('.med-center')?.hasAttribute('inert'),
      overflow: document.body.style.overflow,
    })), { width: 1280, role: null, inert: false, overflow: '' })
    return checks
  } finally {
    await viewport.reset()
  }
}

export async function checkBody(tab) {
  const checks = []
  for (const name of ['正常映射', '首条偏移错误', '缺少首条映射', '末行包含正文和声明', '正文提及来源短语']) {
    await tab.playwright.getByRole('button', { name, exact: true }).click()
    await tab.getAXState({ emit: false })
    const result = await tab.playwright.evaluate(() => ({
      expected: document.querySelector('#expected')?.textContent,
      actual: [...document.querySelectorAll('.prose-paragraph')].map(e =>
        [...e.querySelectorAll('.claim-sentence>span:first-child,.plain-text-segment')].map(x => x.textContent).join('')).join('\n'),
    }))
    // DOM paragraphs use block layout; exact original separator bytes are checked in unit tests.
    const normalizeBreaks = text => text.replace(/\r\n?/g, '\n').replace(/\n+/g, '\n')
    assert.equal(normalizeBreaks(result.actual), normalizeBreaks(result.expected), name)
    checks.push({ name, passed: true })
  }
  return checks
}
