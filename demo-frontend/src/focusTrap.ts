const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not(:disabled)',
  'input:not(:disabled):not([type="hidden"])',
  'select:not(:disabled)',
  'textarea:not(:disabled)',
  'summary',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')

function isElementVisibleAndInteractive(el: HTMLElement, root: HTMLElement): boolean {
  let curr: HTMLElement | null = el
  while (curr && curr !== root) {
    if (
      curr.hasAttribute('inert') ||
      curr.getAttribute('aria-hidden') === 'true' ||
      curr.hasAttribute('hidden')
    ) {
      return false
    }
    const parentDetails = curr.parentElement
    if (
      parentDetails &&
      parentDetails.tagName === 'DETAILS' &&
      !(parentDetails as HTMLDetailsElement).open &&
      curr.tagName !== 'SUMMARY'
    ) {
      return false
    }
    if (typeof window !== 'undefined' && typeof window.getComputedStyle === 'function') {
      const style = window.getComputedStyle(curr)
      if (style.display === 'none' || style.visibility === 'hidden') {
        return false
      }
    }
    curr = curr.parentElement
  }
  return true
}

export function getFocusableElements(container: HTMLElement | null | undefined): HTMLElement[] {
  if (!container) return []
  if (container.hasAttribute('inert') || container.getAttribute('aria-hidden') === 'true') {
    return []
  }
  const nodes = Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR))
  return nodes.filter(el => isElementVisibleAndInteractive(el, container))
}

export function focusInitialElement(
  container: HTMLElement | null | undefined,
  preferredSelector?: string,
): HTMLElement | null {
  if (!container) return null
  if (preferredSelector) {
    const preferred = container.querySelector<HTMLElement>(preferredSelector)
    if (preferred && isElementVisibleAndInteractive(preferred, container)) {
      preferred.focus()
      return preferred
    }
  }
  const focusables = getFocusableElements(container)
  if (focusables.length > 0) {
    focusables[0]!.focus()
    return focusables[0]!
  }
  if (!container.hasAttribute('tabindex')) {
    container.setAttribute('tabindex', '-1')
  }
  container.focus()
  return container
}

export function trapFocusOnTab(
  event: KeyboardEvent,
  container: HTMLElement | null | undefined,
): boolean {
  if (event.key !== 'Tab' || !container) return false
  const focusables = getFocusableElements(container)
  if (focusables.length === 0) {
    event.preventDefault()
    if (!container.hasAttribute('tabindex')) {
      container.setAttribute('tabindex', '-1')
    }
    container.focus()
    return true
  }

  const first = focusables[0]!
  const last = focusables[focusables.length - 1]!
  const active = (typeof document !== 'undefined' ? document.activeElement : null) as HTMLElement | null
  const inside = active ? container.contains(active) : false

  if (event.shiftKey) {
    if (!inside || active === first) {
      event.preventDefault()
      last.focus()
      return true
    }
  } else {
    if (!inside || active === last) {
      event.preventDefault()
      first.focus()
      return true
    }
  }
  return false
}
