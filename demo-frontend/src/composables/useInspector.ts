import { computed, nextTick, ref } from 'vue'
import type { MappedAnswerClaim } from '../medicalLabels'
import type { SourceItem } from '../types'

export interface UseInspectorOptions {
  saveTrigger?: (el?: HTMLElement | EventTarget | null) => void
  restoreTriggerFocus?: () => void
  onClaimFocused?: () => void
  onOmittedSectionFocused?: () => void
}

export function useInspector(options: UseInspectorOptions = {}) {
  const rightInspectorTab = ref<'evidence' | 'trace'>('evidence')
  const highlightedSourceId = ref<string | null>(null)
  const selectedClaim = ref<MappedAnswerClaim | null>(null)
  const claimFilter = ref<'all' | 'omitted'>('all')

  const desktopInspectorOpen = ref(false)
  const mobileInspectorOpen = ref(false)

  const popoverClaim = ref<MappedAnswerClaim | null>(null)
  const popoverAnchorEl = ref<HTMLElement | null>(null)
  const popoverOpen = ref(false)

  function closePopover() {
    popoverOpen.value = false
    popoverClaim.value = null
    popoverAnchorEl.value = null
  }

  function resetSelection() {
    highlightedSourceId.value = null
    selectedClaim.value = null
    claimFilter.value = 'all'
    closePopover()
  }

  function openRightPanel(triggerEl?: HTMLElement | null, isNarrow = false) {
    options.saveTrigger?.(triggerEl)
    desktopInspectorOpen.value = true
    if (isNarrow) {
      mobileInspectorOpen.value = true
    }
  }

  function closeRightPanel() {
    desktopInspectorOpen.value = false
    mobileInspectorOpen.value = false
    options.restoreTriggerFocus?.()
  }

  function handleSelectClaim(
    seg: MappedAnswerClaim,
    triggerEl: HTMLElement | null,
    isRightPanelVisible: boolean,
    isNarrow = false,
  ) {
    selectedClaim.value = seg
    rightInspectorTab.value = 'evidence'
    highlightedSourceId.value = seg.evidenceAnchors[0]?.source_id || null

    if (isRightPanelVisible) {
      closePopover()
      options.onClaimFocused?.()
    } else {
      options.saveTrigger?.(triggerEl)
      popoverClaim.value = seg
      popoverAnchorEl.value = triggerEl
      popoverOpen.value = true
    }
  }

  function handleOpenFullInspectorFromPopover(
    claim: MappedAnswerClaim,
    isNarrow = false,
  ) {
    const anchor = popoverAnchorEl.value
    closePopover()
    selectedClaim.value = claim
    rightInspectorTab.value = 'evidence'
    highlightedSourceId.value = claim.evidenceAnchors[0]?.source_id || null
    openRightPanel(anchor, isNarrow)
    nextTick(() => {
      options.onClaimFocused?.()
    })
  }

  function handleInspectSource(
    source: SourceItem,
    triggerEl: HTMLElement | null,
    isNarrow = false,
  ) {
    selectedClaim.value = null
    rightInspectorTab.value = 'evidence'
    highlightedSourceId.value = source.id
    openRightPanel(triggerEl, isNarrow)
    nextTick(() => {
      const el = document.getElementById(`source-card-${source.id}`)
      el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    })
  }

  function handleInspectOmittedClaims(
    triggerEl: HTMLElement | null,
    isNarrow = false,
  ) {
    selectedClaim.value = null
    rightInspectorTab.value = 'trace'
    claimFilter.value = 'omitted'
    openRightPanel(triggerEl, isNarrow)
    options.onOmittedSectionFocused?.()
  }

  function handleOpenTraceView(
    section: 'overview' | 'omitted' | 'dag',
    triggerEl: HTMLElement | null,
    isNarrow = false,
  ) {
    selectedClaim.value = null
    rightInspectorTab.value = 'trace'
    claimFilter.value = section === 'omitted' ? 'omitted' : 'all'
    openRightPanel(triggerEl, isNarrow)
    if (section === 'omitted') {
      options.onOmittedSectionFocused?.()
    }
  }

  function handleFocusSourceCard(sourceId: string) {
    highlightedSourceId.value = sourceId
    nextTick(() => {
      const el = document.getElementById(`source-card-${sourceId}`)
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    })
  }

  return {
    rightInspectorTab,
    highlightedSourceId,
    selectedClaim,
    claimFilter,
    desktopInspectorOpen,
    mobileInspectorOpen,
    popoverClaim,
    popoverAnchorEl,
    popoverOpen,
    closePopover,
    resetSelection,
    openRightPanel,
    closeRightPanel,
    handleSelectClaim,
    handleOpenFullInspectorFromPopover,
    handleInspectSource,
    handleInspectOmittedClaims,
    handleOpenTraceView,
    handleFocusSourceCard,
  }
}
