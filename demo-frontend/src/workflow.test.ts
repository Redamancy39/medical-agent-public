import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import {
  beginDraft,
  cancelDraft,
  commitDraft,
  editDraft,
  fieldsOf,
  initialState,
  requestConfirmation,
  restoreState,
  validate,
} from './workflow.ts'
import {
  buildTaskWaves,
  POLICY_NOTICE_TEXT,
  extractAnswerBodyAndNotices,
  reconstructVisibleBodyText,
  resolveActualTasks,
  resolveAnswerClaimSegments,
  summarizeClaims,
} from './medicalLabels.ts'
import { MOCK_SCENARIOS, generateSimulatedTurn } from './mockMedicalScenarios.ts'
import {
  VERIFIED_NLM_FIXTURE,
  OMITTED_NOTICE_LINE,
  buildVerifiedEvidenceAnchor,
  composeReviewedAnswerAndClaims,
  validateSimulatedRunConsistency,
} from './verifiedNlmFixture.ts'
import { trapFocusOnTab } from './focusTrap.ts'
import { describeRunProgress } from './runProgress.ts'

function sha256(text: string): string {
  return createHash('sha256').update(text, 'utf8').digest('hex')
}

test('waiting progress stays indeterminate until this request has a backend record', () => {
  const p = describeRunProgress(null)
  assert.equal(p.active, true)
  assert.match(p.detail, /等待后端/)
  assert.ok(p.steps.every(s => s.state === 'waiting'))
  assert.ok(!('percent' in p))
})

test('a completed planner checkpoint does not falsely announce retrieval or mark unseen phases done', () => {
  const run = { ...MOCK_SCENARIOS[0]!.turns[0]!.run, run_status: 'running' as const,
    result_status: null, stage: 'plan', reviewer_status: 'not_run', atomization_status: 'not_run', review_rewrite_status: 'not_run' }
  const p = describeRunProgress(run, [{ stage: 'plan', task_id: null, status: 'completed' }])
  assert.equal(p.steps.find(s => s.id === 'understand')!.state, 'current')
  assert.ok(p.steps.filter(s => s.id !== 'understand').every(s => s.state === 'waiting'))
  assert.match(p.detail, /最近记录：理解问题/)
})

test('live review metadata takes precedence over the last completed synthesize checkpoint', () => {
  const run = { ...MOCK_SCENARIOS[0]!.turns[0]!.run, run_status: 'running' as const,
    result_status: null, stage: 'synthesize', reviewer_status: 'running', review_rewrite_status: 'awaiting_review' }
  const p = describeRunProgress(run)
  assert.equal(p.steps.find(s => s.id === 'review')!.state, 'current')
  assert.match(p.detail, /改写后的引用/)
  assert.equal(p.steps.find(s => s.id === 'save')!.state, 'waiting')
})

test('paused, failed and urgent exits do not simulate continued model processing', () => {
  const base = MOCK_SCENARIOS[0]!.turns[0]!.run
  assert.equal(describeRunProgress({ ...base, run_status: 'awaiting_input' }).active, false)
  const failed = describeRunProgress({ ...base, run_status: 'finished', result_status: 'failed' })
  assert.equal(failed.active, false)
  assert.match(failed.title, /停止/)
  const urgent = describeRunProgress({ ...base, response_origin: 'urgent_policy' })
  assert.ok(urgent.steps.filter(s => ['answer', 'review'].includes(s.id)).every(s => s.state === 'skipped'))
})

test('a draft never becomes a record without an explicit confirmation', () => {
  const state = initialState()
  assert.equal(state.records.length, 0)
  assert.throws(() =>
    commitDraft(state, {
      draftId: state.draft!.id,
      revision: 1,
      signature: JSON.stringify(fieldsOf(state.draft!)),
    }),
  )
  assert.equal(state.records.length, 0)
})

test('editing invalidates a prior confirmation even if fields are changed back', () => {
  const state = initialState()
  const confirmation = requestConfirmation(state)
  const original = fieldsOf(state.draft!)
  editDraft(state, { ...original, quantity: 6 })
  editDraft(state, original)
  assert.throws(() => commitDraft(state, confirmation))
  assert.equal(state.records.length, 0)
})

test('confirmation replay is idempotent and cancellation cannot write', () => {
  const state = initialState()
  const confirmation = requestConfirmation(state)
  const first = commitDraft(state, confirmation)
  assert.equal(commitDraft(state, confirmation).id, first.id)
  assert.equal(state.records.length, 1)
  beginDraft(state, '今天登记2份血液样本，属于B项目，存储在C区域')
  const cancelledConfirmation = requestConfirmation(state)
  cancelDraft(state)
  assert.throws(() => commitDraft(state, cancelledConfirmation))
  assert.equal(state.records.length, 1)
})

test('missing fields, nonexistent projects, and invalid quantities are rejected', () => {
  const state = initialState()
  cancelDraft(state)
  beginDraft(state, '登记样本，属于Z项目')
  assert.deepEqual(
    Object.keys(validate(state.draft!)).sort(),
    ['project', 'quantity', 'receivedAt', 'sampleType', 'storage'].sort(),
  )
  assert.throws(() => requestConfirmation(state))
  const fields = fieldsOf(initialState().draft!)
  for (const quantity of [0, -1, 1.5, 21, NaN]) assert.ok(validate({ ...fields, quantity }).quantity)
})

test('reload preserves confirmed records but does not replay a pending confirmation', () => {
  const state = initialState()
  const confirmation = requestConfirmation(state)
  const pending = restoreState(JSON.stringify(state))!
  assert.equal(pending.draft!.status, 'ready')
  assert.throws(() => commitDraft(pending, confirmation))
  commitDraft(state, confirmation)
  const restored = restoreState(JSON.stringify(state))!
  assert.equal(restored.records.length, 1)
  assert.equal(restored.draft!.status, 'completed')
  assert.equal(restoreState('{bad json}'), null)
  assert.equal(
    restoreState(JSON.stringify({ ...state, records: [{ ...state.records[0], quantity: 0 }] })),
    null,
  )
})

test('VERIFIED_NLM_FIXTURE raw sha256, version, editorial slices, and quote offsets are 100% consistent', () => {
  for (const [docId, doc] of Object.entries(VERIFIED_NLM_FIXTURE)) {
    assert.equal(sha256(doc.raw), doc.source_sha256, `raw sha256 mismatch for ${docId}`)
    const expectedVersion = `${doc.source_sha256.slice(0, 12)}-zh-${sha256(doc.editorial_text).slice(0, 12)}`
    assert.equal(doc.version, expectedVersion, `version mismatch for ${docId}`)

    for (const sec of doc.sections) {
      assert.equal(
        doc.editorial_text.slice(sec.start, sec.end),
        sec.text,
        `editorial slice mismatch in ${docId} section ${sec.section}`,
      )
      for (const sp of sec.source_spans) {
        assert.equal(
          sp.end - sp.start,
          sp.quote.length,
          `span length mismatch in ${docId}: [${sp.start}..${sp.end}] vs ${sp.quote.length}`,
        )
        assert.equal(
          doc.raw.slice(sp.start, sp.end),
          sp.quote,
          `raw quote substring mismatch in ${docId}`,
        )
      }
    }
  }
})

test('all preset and generated simulation runs use sim- prefixes, never reuse real run_ids, and pass anchor/hash consistency', () => {
  const forbiddenRealIds = new Set([
    '50f4b19c-c2a8-491b-85d6-a9109b523f7e',
    '25e30056-3733-4995-a555-4a265a81cc61',
    '07c5ba1f-21cb-493d-a70a-aa378ceb5a90',
    '082ccd48-00b1-4297-b242-f14ad09612f2',
    '8e1d9782-a571-48ad-9a18-c420a3b1a2c6',
  ])

  for (const scenario of MOCK_SCENARIOS) {
    assert.ok(scenario.id.startsWith('sim-'), `scenario id must start with sim-: ${scenario.id}`)
    assert.ok(!/真实复现|真实回放/.test(scenario.summaryText), `scenario summary must not claim 真实复现/真实回放`)
    for (const turn of scenario.turns) {
      assert.ok(!forbiddenRealIds.has(turn.run.run_id), `must not reuse real run_id: ${turn.run.run_id}`)
      validateSimulatedRunConsistency(turn.run)
    }
    for (const sug of scenario.followUpSuggestions) {
      if (sug.presetTurn) {
        validateSimulatedRunConsistency(sug.presetTurn.run)
      }
    }
  }

  for (const sampleQ of [
    'eGFR 和 UACR 有什么区别？',
    '血压 120/80 代表什么？测前 30 分钟要注意什么？',
    '空腹验血期间能喝咖啡或停降压药吗？',
    '原发性醛固酮增多症的肾上腺静脉采血标准是什么？',
  ]) {
    const generated = generateSimulatedTurn(sampleQ, 'sim-session-test', 1)
    validateSimulatedRunConsistency(generated.run)
  }
})

test('resolveActualTasks and buildTaskWaves reflect dynamic single-agent, multi-agent DAG, and urgent policy runs', () => {
  const singleScenario = MOCK_SCENARIOS[0]!.turns[0]!.run
  const singleTasks = resolveActualTasks(singleScenario)
  assert.equal(singleTasks.length, 1)
  assert.equal(buildTaskWaves(singleTasks).length, 1)

  const multiScenario = MOCK_SCENARIOS[1]!.turns[0]!.run
  const multiTasks = resolveActualTasks(multiScenario)
  assert.equal(multiTasks.length, 3)
  const waves = buildTaskWaves(multiTasks)
  assert.equal(waves.length, 2)
  assert.equal(waves[0]!.tasks.length, 1)
  assert.equal(waves[1]!.tasks.length, 2)

  const urgentScenario = MOCK_SCENARIOS[3]!.turns[0]!.run
  assert.equal(resolveActualTasks(urgentScenario).length, 0)
})

test('resolveAnswerClaimSegments maps per-fact evidence accurately and does not guess when claim_reviews is absent', () => {
  const uacrRun = MOCK_SCENARIOS[0]!.turns[0]!.run
  const mappedUacr = resolveAnswerClaimSegments(uacrRun, uacrRun.answer)
  assert.equal(mappedUacr.hasReliableMapping, true)
  assert.equal(mappedUacr.paragraphs.length, 2)
  // First paragraph has 2 individual sentences, second sentence has 3 evidence anchors
  assert.equal(mappedUacr.paragraphs[0]!.length, 2)
  assert.equal(mappedUacr.paragraphs[0]![1]!.evidenceAnchors.length, 3)

  const partialRun = MOCK_SCENARIOS[1]!.turns[0]!.run
  const summary = summarizeClaims(partialRun.claim_reviews)
  assert.equal(summary.supported, 6)
  assert.equal(summary.omitted, 2)
  const mappedPartial = resolveAnswerClaimSegments(partialRun, partialRun.answer)
  assert.equal(mappedPartial.hasReliableMapping, true)
  assert.equal(mappedPartial.omittedClaims.length, 2)

  // Unmapped run with sources but no claim_reviews must return hasReliableMapping: false
  const unmappedRun = { ...uacrRun, claim_reviews: [] }
  const unmappedResult = resolveAnswerClaimSegments(unmappedRun, uacrRun.answer)
  assert.equal(unmappedResult.hasReliableMapping, false)
})

test('P1 reproduction & 7 regression cases: answer prose is 100% preserved across valid, invalid, missing, unmapped gap, out-of-bounds/duplicate/overlapping, emoji non-BMP, and omitted claims', () => {
  const baseRun = JSON.parse(JSON.stringify(MOCK_SCENARIOS[0]!.turns[0]!.run))
  const expectedBody = extractAnswerBodyAndNotices(baseRun.answer).bodyText
  const firstSentence = baseRun.claim_reviews[0].text as string
  const secondSentence = baseRun.claim_reviews[1].text as string

  // 1. All mappings valid: full body preserved, exact citation bindings
  const resValid = resolveAnswerClaimSegments(baseRun, baseRun.answer)
  assert.equal(resValid.hasReliableMapping, true)
  assert.equal(resValid.mappingStatus, 'complete')
  assert.equal(reconstructVisibleBodyText(resValid), expectedBody)
  assert.equal(resValid.paragraphs[0]![0]!.isMedicalFactWithEvidence, true)
  assert.equal(resValid.paragraphs[0]![1]!.evidenceAnchors.length, 3)

  // 2. One offset corrupted (first claim final_start + 1), others valid:
  // Full original prose preserved; first sentence becomes plain unmapped text without citation button; remaining 3 keep citations
  const runBadFirstOffset = JSON.parse(JSON.stringify(baseRun))
  runBadFirstOffset.claim_reviews[0].final_start += 1
  const resBadFirst = resolveAnswerClaimSegments(runBadFirstOffset, runBadFirstOffset.answer)
  assert.equal(reconstructVisibleBodyText(resBadFirst), expectedBody)
  assert.ok(reconstructVisibleBodyText(resBadFirst).startsWith(firstSentence))
  assert.equal(resBadFirst.hasReliableMapping, true)
  assert.equal(resBadFirst.mappingStatus, 'partial')
  assert.equal(resBadFirst.invalidClaimCount, 1)
  assert.equal(resBadFirst.paragraphs[0]![0]!.kind, 'text')
  assert.equal(resBadFirst.paragraphs[0]![0]!.isMedicalFactWithEvidence, false)
  assert.equal(resBadFirst.paragraphs[0]![0]!.text, firstSentence)
  assert.equal(resBadFirst.paragraphs[0]![1]!.kind, 'claim')
  assert.equal(resBadFirst.paragraphs[0]![1]!.isMedicalFactWithEvidence, true)
  assert.equal(resBadFirst.paragraphs[0]![1]!.text, secondSentence)

  // 3. Missing one claim_review (remove first claim_review):
  // First sentence still preserved verbatim in rendered body text
  const runMissingFirstClaim = JSON.parse(JSON.stringify(baseRun))
  runMissingFirstClaim.claim_reviews.shift()
  const resMissingFirst = resolveAnswerClaimSegments(
    runMissingFirstClaim,
    runMissingFirstClaim.answer,
  )
  assert.equal(reconstructVisibleBodyText(resMissingFirst), expectedBody)
  assert.equal(resMissingFirst.paragraphs[0]![0]!.kind, 'text')
  assert.equal(resMissingFirst.paragraphs[0]![0]!.isMedicalFactWithEvidence, false)
  assert.equal(resMissingFirst.paragraphs[0]![0]!.text, firstSentence)
  assert.equal(resMissingFirst.paragraphs[0]![1]!.kind, 'claim')
  assert.equal(resMissingFirst.paragraphs[0]![1]!.isMedicalFactWithEvidence, true)

  // 4. Unmapped prefix, inter-sentence gap, and suffix: content and order preserved verbatim
  const prefix = '【导读前缀】'
  const infix = '（句间补充说明）'
  const suffix = '【段尾补充说明】'
  const s1 = '第一句有依据。'
  const s2 = '第二句有依据。'
  const customBody = `${prefix}${s1}${infix}${s2}${suffix}`
  const customAnswer = `${customBody}\n资料来自美国NLM/MedlinePlus，中文为编辑解释，未经过医学专业复核；不替代个体诊断或用药建议。`
  const s1Start = prefix.length
  const s1End = s1Start + s1.length
  const s2Start = s1End + infix.length
  const s2End = s2Start + s2.length
  const runWithGaps = {
    ...baseRun,
    answer: customAnswer,
    claim_reviews: [
      {
        index: 0,
        kind: 'medical_fact',
        support_status: 'supported',
        evidence_ids: ['e0'],
        evidence: [buildVerifiedEvidenceAnchor('e0', 'nlm-uacr-test', 0, 0)],
        policy_rules: [],
        note: '支持句1',
        text: s1,
        draft_start: 0,
        draft_end: s1.length,
        final_start: s1Start,
        final_end: s1End,
      },
      {
        index: 1,
        kind: 'medical_fact',
        support_status: 'supported',
        evidence_ids: ['e1'],
        evidence: [buildVerifiedEvidenceAnchor('e1', 'nlm-uacr-test', 0, 1)],
        policy_rules: [],
        note: '支持句2',
        text: s2,
        draft_start: s1.length,
        draft_end: s1.length + s2.length,
        final_start: s2Start,
        final_end: s2End,
      },
    ],
  }
  const resWithGaps = resolveAnswerClaimSegments(runWithGaps, runWithGaps.answer)
  assert.equal(reconstructVisibleBodyText(resWithGaps), customBody)
  const flatGaps = resWithGaps.paragraphs.flat()
  assert.deepEqual(
    flatGaps.map(seg => [seg.kind, seg.text, seg.isMedicalFactWithEvidence]),
    [
      ['text', prefix, false],
      ['claim', s1, true],
      ['text', infix, false],
      ['claim', s2, true],
      ['text', suffix, false],
    ],
  )

  // 5. Out-of-bounds, duplicate, and overlapping mappings:
  // Never drops characters, never duplicates text, never binds ambiguous overlapping citations
  const overlapText = '甲乙丙丁戊己庚辛壬癸。后一句正常绑定。'
  const normalStart = '甲乙丙丁戊己庚辛壬癸。'.length
  const normalEnd = overlapText.length
  const evA = buildVerifiedEvidenceAnchor('e0', 'nlm-uacr-test', 0, 0)
  const evB = buildVerifiedEvidenceAnchor('e1', 'nlm-uacr-test', 0, 1)
  const runAnomalous = {
    ...baseRun,
    answer: overlapText,
    claim_reviews: [
      // Out-of-bounds claim
      {
        index: 0,
        kind: 'medical_fact',
        support_status: 'supported',
        evidence_ids: ['e0'],
        evidence: [evA],
        policy_rules: [],
        note: '越界',
        text: '越界文本',
        draft_start: 0,
        draft_end: 4,
        final_start: -2,
        final_end: 999,
      },
      // Overlapping pair: [0..6] ("甲乙丙丁戊己") and [3..11] ("丁戊己庚辛壬癸。")
      {
        index: 1,
        kind: 'medical_fact',
        support_status: 'supported',
        evidence_ids: ['e0'],
        evidence: [evA],
        policy_rules: [],
        note: '重叠A',
        text: overlapText.slice(0, 6),
        draft_start: 0,
        draft_end: 6,
        final_start: 0,
        final_end: 6,
      },
      {
        index: 2,
        kind: 'medical_fact',
        support_status: 'supported',
        evidence_ids: ['e1'],
        evidence: [evB],
        policy_rules: [],
        note: '重叠B',
        text: overlapText.slice(3, 11),
        draft_start: 3,
        draft_end: 11,
        final_start: 3,
        final_end: 11,
      },
      // Exact duplicate of valid second sentence
      {
        index: 3,
        kind: 'medical_fact',
        support_status: 'supported',
        evidence_ids: ['e0'],
        evidence: [evA],
        policy_rules: [],
        note: '正常句',
        text: '后一句正常绑定。',
        draft_start: 11,
        draft_end: 19,
        final_start: normalStart,
        final_end: normalEnd,
      },
      {
        index: 4,
        kind: 'medical_fact',
        support_status: 'supported',
        evidence_ids: ['e0'],
        evidence: [evA],
        policy_rules: [],
        note: '重复正常句',
        text: '后一句正常绑定。',
        draft_start: 11,
        draft_end: 19,
        final_start: normalStart,
        final_end: normalEnd,
      },
    ],
  }
  const resAnomalous = resolveAnswerClaimSegments(runAnomalous, runAnomalous.answer)
  assert.equal(reconstructVisibleBodyText(resAnomalous), overlapText)
  assert.equal(resAnomalous.invalidClaimCount, 1)
  assert.equal(resAnomalous.duplicateClaimCount, 1)
  assert.equal(resAnomalous.overlapConflictCount, 2)
  const flatAnom = resAnomalous.paragraphs.flat()
  // Overlapping first sentence is rendered once as unmapped text; second sentence is rendered once as a mapped claim
  assert.equal(flatAnom.length, 2)
  assert.equal(flatAnom[0]!.kind, 'text')
  assert.equal(flatAnom[0]!.text, '甲乙丙丁戊己庚辛壬癸。')
  assert.equal(flatAnom[0]!.isMedicalFactWithEvidence, false)
  assert.equal(flatAnom[1]!.kind, 'claim')
  assert.equal(flatAnom[1]!.text, '后一句正常绑定。')
  assert.equal(flatAnom[1]!.isMedicalFactWithEvidence, true)

  // 6. Non-BMP characters (emoji 🩺 U+1FA7A, surrogate pair in UTF-16, 1 code point in Python):
  // Python code-point offsets for subsequent claims are accurately converted to UTF-16 slices
  const emojiComposed = composeReviewedAnswerAndClaims([
    {
      kind: 'medical_fact',
      support_status: 'supported',
      text: '🩺尿白蛋白肌酐比（UACR）比较尿白蛋白与尿肌酐水平。',
      note: '含非BMP字符首句',
      evidence: [evA],
    },
    {
      kind: 'medical_fact',
      support_status: 'supported',
      text: '🧬早期肾病通常没有任何症状，建议糖尿病与高血压患者定期筛查。',
      note: '含非BMP字符次句',
      evidence: [evB],
    },
  ])
  // Verify that Python code-point length differs from UTF-16 length here
  assert.notEqual(
    Array.from(emojiComposed.claim_reviews[0]!.text).length,
    emojiComposed.claim_reviews[0]!.text.length,
  )
  const emojiRun = {
    ...baseRun,
    answer: emojiComposed.answer,
    claim_reviews: emojiComposed.claim_reviews,
  }
  const resEmoji = resolveAnswerClaimSegments(emojiRun, emojiRun.answer)
  const expectedEmojiBody = extractAnswerBodyAndNotices(emojiComposed.answer).bodyText
  assert.equal(reconstructVisibleBodyText(resEmoji), expectedEmojiBody)
  assert.equal(resEmoji.mappingStatus, 'complete')
  assert.equal(resEmoji.paragraphs[0]!.length, 2)
  assert.equal(resEmoji.paragraphs[0]![0]!.isMedicalFactWithEvidence, true)
  assert.equal(resEmoji.paragraphs[0]![1]!.isMedicalFactWithEvidence, true)
  assert.equal(
    resEmoji.paragraphs[0]![1]!.text,
    '🧬早期肾病通常没有任何症状，建议糖尿病与高血压患者定期筛查。',
  )

  // 7. Omitted draft claims (unsupported / partially_supported) never re-enter rendered body text
  const partialRun = MOCK_SCENARIOS[1]!.turns[0]!.run
  const resPartial = resolveAnswerClaimSegments(partialRun, partialRun.answer)
  const visiblePartialText = reconstructVisibleBodyText(resPartial)
  assert.equal(resPartial.omittedClaims.length, 2)
  for (const omitted of resPartial.omittedClaims) {
    assert.equal(
      visiblePartialText.includes(omitted.text),
      false,
      `Omitted claim "${omitted.text}" must never appear in rendered body text`,
    )
  }
})

test('trapFocusOnTab ignores non-Tab keys and returns false when container is null', () => {
  let prevented = false
  const escEvent = {
    key: 'Escape',
    shiftKey: false,
    preventDefault() {
      prevented = true
    },
  } as unknown as KeyboardEvent
  assert.equal(trapFocusOnTab(escEvent, null), false)
  assert.equal(prevented, false)
})

test('a fixed policy suffix on the same line never removes preceding prose', () => {
  const body = '保留前一段。\n请先确认具体检查项目。'
  const raw = body + POLICY_NOTICE_TEXT
  const result = resolveAnswerClaimSegments(null, raw)
  assert.equal(result.bodyText, body)
  assert.equal(reconstructVisibleBodyText(result), body)
  assert.equal(result.policyNotice, POLICY_NOTICE_TEXT)
})

test('source wording inside ordinary prose is not mistaken for a policy notice', () => {
  for (const body of [
    '问题说明：这份资料来自美国NLM/MedlinePlus 的哪个栏目？',
    `引用的声明是“${POLICY_NOTICE_TEXT}”，这句话是什么意思？`,
    '资料来自美国NLM/MedlinePlus 的内容也需要结合具体检查项目理解。',
  ]) {
    const result = resolveAnswerClaimSegments(null, body)
    assert.equal(result.policyNotice, '')
    assert.equal(reconstructVisibleBodyText(result), body)
  }
})

test('only exact trailing omission and policy notices are separated from prose', () => {
  const body = '请先确认检查项目。'
  for (const separator of ['\n', '\n\n', '\r\n']) {
    const result = extractAnswerBodyAndNotices(
      body + separator + OMITTED_NOTICE_LINE + separator + POLICY_NOTICE_TEXT + '\n',
    )
    assert.equal(result.bodyText, body)
    assert.equal(result.omittedNotice, OMITTED_NOTICE_LINE)
    assert.equal(result.policyNotice, POLICY_NOTICE_TEXT)
  }
  const bodyWithSimilarPrefix = '部分内容缺少充分的原文或项目规则支持，已省略这句话是否意味着没有证据？'
  assert.equal(extractAnswerBodyAndNotices(bodyWithSimilarPrefix).bodyText, bodyWithSimilarPrefix)
})

test('same-line suffix extraction leaves remaining claim offsets unchanged', () => {
  const run = structuredClone(MOCK_SCENARIOS[0]!.turns[0]!.run)
  const body = extractAnswerBodyAndNotices(run.answer).bodyText
  run.answer = body + POLICY_NOTICE_TEXT
  const result = resolveAnswerClaimSegments(run, run.answer)
  assert.equal(reconstructVisibleBodyText(result), body)
  assert.equal(result.paragraphs.flat().filter(s => s.isMedicalFactWithEvidence).length, 4)
})

test('unmapped line breaks, leading whitespace and trailing whitespace are preserved', () => {
  for (const body of [
    '第一行。\n第二行。\n\n\n第三段。',
    '\n\n  第一行。\r\n第二行。\r\n\r\n第三段。\n ',
  ]) {
    const result = resolveAnswerClaimSegments(null, body)
    assert.equal(result.bodyText, body)
    assert.equal(reconstructVisibleBodyText(result), body)
  }
})
