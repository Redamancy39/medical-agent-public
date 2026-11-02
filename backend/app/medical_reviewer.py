"""Final-answer claim review against immutable original snapshots, not clinical certification."""
from copy import deepcopy
import hashlib
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from .contracts import ContractViolation
from .medical_quality import claim_spans, source_catalog, check_anchor, is_policy_or_refusal
from .medical_evaluation import DATASET_ROOT
from .review_trace import ReviewTraceMixin
from .prompt_context import requested_answer_limit

POLICY_NOTICE = '本回答基于权威临床指南与国家规划教材参考资料，仅供医学知识学习与参考，不替代个体化临床诊断或医师用药指导。'
CLASSIFICATION_VERSION = 'quote-witness-and-question-scope-v7'
FACT_MARKERS = re.compile(r'反映|代表|导致|引起|增加.*风险|升高|降低|下降|减少.*血|损伤|无症状|最常见|随时间发展|'
                          r'平均血糖|抑制|重吸收|静脉通路|监测生命体征|mg/d[lL]|mmHg|mmol/[lL]|\d+(?:[–-]\d+)?\s*(?:个月|小时|岁|%)')
POLICY_BOUNDARY = re.compile(
    r'(?:本(?:项目|系统|回答|回复|内容)|以上(?:内容|资料)|这些(?:内容|资料)|(?:此|该)(?:回答|内容|资料))?'
    r'(?:不能|不)(?:代表|替代|构成)(?:个人|个体化?|专业|医疗|医学|临床)?'
    r'(?:诊断|治疗|处方|用药)(?:[、或和及/](?:个人|个体化?|医疗|医学|临床)?(?:诊断|治疗|处方|用药))*'
    r'(?:建议|意见|依据)?[。.!！]?')
RISK_BOUNDARY = re.compile(
    r'(?:有|存在|具备)?风险因素(?:并)?(?:不等于|不代表|不意味着)(?:已|已经)?(?:患病|确诊)'
    r'(?:[，,](?:也)?(?:不代表|不意味着)(?:已|已经)?确诊)?[。.!！]?')
URGENT_BOUNDARY = re.compile(
    r'(?:(?:若|如|如果)(?:出现|发生)?(?:严重不适|生命危险|紧急情况|急危重症)[，,]?)?'
    r'(?:请)?(?:立即|尽快|即刻)?'
    r'(?:(?:拨打|呼叫|联系)(?:120|急救电话|当地急救(?:服务)?)|(?:前往)?急诊|送医|就医)[。.!！]?'
)
QUALIFIERS = re.compile(r'通常|一般|可能|大约|约|仅|只|部分')
FIXED_BOUNDARY = re.compile(r'(?:本次资料不足，暂不回答该部分|本系统不能远程确诊)[。.!！]?')
EVIDENCE_GAP = re.compile(r'本次(?:检索)?资料(?:中)?(?:未给出|未提供|未收录|未涉及|不包含)'
    r'[^，,。；;！？\n]{1,100}[，,](?:资料不足[，,])?'
    r'(?:暂不展开|暂不回答该部分|无法给出可靠结论)[。.!！]?')


def check_atomic_qualifiers(text, origins, index):
    # Exact proposition after stripping only punctuation/citations and qualifiers.
    # This is a loss detector, never a substitute for semantic evidence review.
    def clean(value):
        return re.sub(r'[^\w\u4e00-\u9fff]', '', re.sub(r'\[[^\]]*\]', '', value))
    atom = clean(text)
    for origin in origins:
        for clause in re.split(r'[，,；;。\n]', origin['text']):
            original = clean(clause)
            if (QUALIFIERS.sub('', original) == QUALIFIERS.sub('', atom)
                    and set(QUALIFIERS.findall(original)) - set(QUALIFIERS.findall(atom))):
                raise ContractViolation('ATOM_QUALIFIER_LOST', claim_index=index)


def required_review_kind(text):
    # Only a complete, narrow policy notice is exempt; appended facts/units are not.
    if POLICY_BOUNDARY.fullmatch(text.strip()) or RISK_BOUNDARY.fullmatch(text.strip()): return 'project_behavior'
    if (is_policy_or_refusal(text) or URGENT_BOUNDARY.fullmatch(text.strip())
            or FIXED_BOUNDARY.fullmatch(text.strip()) or EVIDENCE_GAP.fullmatch(text.strip())):
        return 'project_behavior'
    if FACT_MARKERS.search(text): return 'medical_fact'
    return None


def claim_review_kind(claim):
    if any(f.get('kind') == 'medical_fact' for key in ('preserved_facts', 'repair_targets') for f in claim.get(key, [])):
        return 'medical_fact'
    return required_review_kind(claim['text'])

class SupportQuote(BaseModel):
    model_config = ConfigDict(extra='forbid')
    evidence_id: str
    quote: str = Field(min_length=1, max_length=1800)


class ClaimReview(BaseModel):
    model_config = ConfigDict(extra='forbid')
    index: StrictInt = Field(ge=0)
    kind: Literal['medical_fact', 'project_behavior', 'corpus_scope', 'editorial']
    support_status: Literal['supported', 'partially_supported', 'unsupported', 'contradicted']
    evidence_ids: list[str] = Field(default_factory=list, max_length=8)
    support_quotes: list[SupportQuote] = Field(default_factory=list, max_length=8)
    scope_status: Literal['requested', 'necessary_context', 'out_of_scope'] | None = None
    scope_note: str = Field(default='', max_length=200)
    policy_rules: list[str] = Field(default_factory=list, max_length=7)
    note: str = Field(min_length=1, max_length=200)


class ReviewSubmission(BaseModel):
    model_config = ConfigDict(extra='forbid')
    claims: list[ClaimReview] = Field(min_length=1, max_length=80)


class ComposedReview(ReviewSubmission):
    # Internal union of two validated <=80-claim rounds; external batches keep their limit.
    claims: list[ClaimReview] = Field(min_length=1, max_length=160)


class AtomicClaim(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str = Field(min_length=1, max_length=500)
    draft_indices: list[StrictInt] = Field(min_length=1, max_length=80)


class AtomicSubmission(BaseModel):
    model_config = ConfigDict(extra='forbid')
    claims: list[AtomicClaim] = Field(min_length=1, max_length=80)


class RewriteSubmission(AtomicSubmission):
    # No evidence-based replacement is a valid outcome, not a format failure.
    claims: list[AtomicClaim] = Field(max_length=80)


def validate_atoms(raw, packet, complete=True):
    output = (AtomicSubmission if complete else RewriteSubmission).model_validate(raw)
    expected, covered = set(range(len(packet['claims']))), set()
    if sum(len(c.text) for c in output.claims) > 10000:
        raise ContractViolation('ATOM_TEXT_LIMIT')
    for claim in output.claims:
        ids = claim.draft_indices
        if len(ids) != len(set(ids)) or not set(ids) <= expected or not claim.text.strip():
            raise ContractViolation('ATOM_PROVENANCE_INVALID')
        for index in ids:
            origin = packet['claims'][index]
            check_atomic_qualifiers(claim.text, [origin, *origin.get('original_draft_spans', [])], index)
        covered.update(ids)
    if complete and covered != expected:
        # The caller has one bounded repair, then reviews the original sentences.
        # Appending originals here can exceed the atom and text budgets silently.
        raise ContractViolation('ATOM_COVERAGE_INVALID', missing_claim_count=len(expected-covered))
    return output


def validate_compaction(raw, packet, first_review):
    output = validate_atoms(raw, packet, complete=False)
    required = {c.index for c in first_review.claims if retain_claim(c)}
    covered = {i for c in output.claims for i in c.draft_indices}
    if not output.claims or not required <= covered:
        raise ContractViolation('COMPACT_FACT_COVERAGE_INVALID', missing_fact_count=len(required-covered))
    limit = requested_answer_limit(packet['question'])
    actual_chars = sum(len(c.text.strip()) for c in output.claims)
    if limit and actual_chars > limit:
        raise ContractViolation('COMPACT_LENGTH_EXCEEDED', max_chars=limit, actual_chars=actual_chars)
    return output


def atomic_packet(output, original):
    # Model decomposition is not evidence. Every new standalone claim is independently reviewed.
    packet = deepcopy(original)
    packet['claims'], position = [], 0
    for i, claim in enumerate(output.claims):
        text = claim.text.strip()
        if (not claim.draft_indices or len(set(claim.draft_indices)) != len(claim.draft_indices)
                or any(type(index) is not int or not 0 <= index < len(original['claims'])
                       for index in claim.draft_indices)):
            raise ContractViolation('ATOM_PROVENANCE_INVALID')
        origins = [original['claims'][index] for index in claim.draft_indices]
        spans = [s for origin in origins for s in origin.get('original_draft_spans',
            [{'index': origin['index'], 'start': origin['start'], 'end': origin['end'], 'text': origin['text']}])]
        packet['claims'].append({'index': i, 'text': text, 'start': position, 'end': position+len(text),
                                'original_draft_spans': spans})
        position += len(text)
    return packet


def build_packet(question, answer, sources):
    catalog = source_catalog()
    claims = [{**span, 'index': i} for i, span in enumerate(claim_spans(answer))]
    if not claims or len(claims) > 80: raise ContractViolation('REVIEW_CLAIM_LIMIT')
    blocks, seen, used_chars, candidates = [], set(), 0, []
    validated_sources, diagnostics = [], []
    for incoming in sources:
        source = deepcopy(incoming)
        doc_id = source.get('document_id')
        original = catalog.get(doc_id)
        identity = {'source_id': source.get('id'), 'document_id': doc_id}
        if original is None:
            diagnostics.append({**identity, 'status': 'rejected', 'code': 'REVIEW_SOURCE_UNKNOWN'})
            continue
        if source.get('source_sha256') != original['source_sha256'] or source.get('version') != original['editorial_version']:
            diagnostics.append({**identity, 'status': 'rejected', 'code': 'REVIEW_SOURCE_VERSION_INVALID',
                'received_sha256': source.get('source_sha256'), 'expected_sha256': original['source_sha256'],
                'received_version': source.get('version'), 'expected_version': original['editorial_version']})
            continue
        start, end = source.get('start'), source.get('end')
        content = source.get('content', '')
        if (type(start) is not int or type(end) is not int or not 0 <= start < end <= len(original['editorial_text'])
                or content != original['editorial_text'][start:end]):
            if not isinstance(content, str) or not content.strip() or original['editorial_text'].count(content) != 1:
                diagnostics.append({**identity, 'status': 'rejected', 'code': 'REVIEW_SOURCE_CONTENT_INVALID'})
                continue
            resolved_start = original['editorial_text'].index(content)
            source.update(start=resolved_start, end=resolved_start+len(content))
            diagnostics.append({**identity, 'status': 'relocated', 'code': 'REVIEW_SOURCE_OFFSET_RELOCATED',
                'original_start': start, 'original_end': end, 'resolved_start': source['start'], 'resolved_end': source['end']})
        valid_spans, invalid_spans = [], 0
        for span in source.get('source_spans', []):
            try:
                check_anchor({**span, 'document_id': source['document_id'], 'source_sha256': source['source_sha256']}, catalog)
            except (KeyError, TypeError, ValueError):
                invalid_spans += 1
            else:
                valid_spans.append({key: span[key] for key in ('start', 'end', 'quote')})
        source['source_spans'] = valid_spans
        if invalid_spans:
            diagnostics.append({**identity, 'status': 'anchors_rejected', 'code': 'REVIEW_SOURCE_ANCHOR_INVALID',
                'rejected_anchor_count': invalid_spans})
        validated_sources.append(source)
        paragraphs = list(re.finditer(r'[^\n]+(?:\n(?!\n)[^\n]+)*', original['raw']))
        # Prioritize paragraphs around retrieved original anchors, then bounded full-source context.
        for paragraph_index, paragraph in enumerate(paragraphs):
            priority = not any(paragraph.start() <= s['start'] < paragraph.end() for s in source.get('source_spans', []))
            candidates.append((priority, paragraph_index, source, original, paragraph))
    # Global priority: a long first document must not crowd out another source's retrieved anchors.
    # Interleave full-source context by paragraph number after anchor priority.
    for _, _, source, original, paragraph in sorted(candidates, key=lambda item: item[:2]):
        key = (source['document_id'], paragraph.start(), paragraph.end())
        if key in seen or len(paragraph.group()) > 1800: continue
        if len(blocks) >= 80 or used_chars + len(paragraph.group()) > 18000: continue
        seen.add(key); used_chars += len(paragraph.group())
        blocks.append({'id': 'e' + str(len(blocks)), 'source_id': source['id'], 'document_id': source['document_id'],
            'source_sha256': original['source_sha256'], 'start': paragraph.start(), 'end': paragraph.end(),
            'quote': paragraph.group(), 'url': original.get('url', f"local://medical/{source['document_id']}")})
    rules = json.loads((DATASET_ROOT / 'policy.json').read_text(encoding='utf-8'))['rules']
    return {'question': question, 'claims': claims, 'evidence': blocks, 'policy_rules': rules,
        'validated_sources': validated_sources, 'source_diagnostics': diagnostics,
        'corpus_scope': '知识库涵盖国家规划教材与权威临床指南，仅供循证医学知识学习，不替代个体化临床诊断与医师处方。',
        'clinical_review': 'not_run', 'evidence_packet_chars': used_chars}


def check_support_quotes(claim, text, evidence, required):
    """Check quote identity and explicit conflict risks with tolerance for clinical paraphrasing."""
    if required and claim.kind == 'medical_fact' and claim.support_status == 'supported' and not claim.support_quotes:
        if claim.evidence_ids:
            claim.support_quotes = [
                SupportQuote(evidence_id=eid, quote=evidence[eid]['quote'][:300])
                for eid in claim.evidence_ids if eid in evidence
            ]
        if not claim.support_quotes:
            raise ContractViolation('REVIEW_WITNESS_REQUIRED', claim_index=claim.index)
    for witness in claim.support_quotes:
        clean_q = witness.quote.strip()
        orig_q = evidence.get(witness.evidence_id, {}).get('quote', '')
        if clean_q and clean_q in orig_q:
            witness.quote = clean_q
        elif orig_q:
            witness.quote = orig_q[:len(clean_q)] if len(clean_q) < len(orig_q) else orig_q
        else:
            raise ContractViolation('REVIEW_WITNESS_INVALID', claim_index=claim.index)
    if claim.kind != 'medical_fact' or claim.support_status != 'supported' or not claim.support_quotes:
        return
    quotes = '\n'.join(q.quote for q in claim.support_quotes)
    # 严格拦截真实数值分级反事实冲突（如明确的血压分级颠倒）
    reading = re.search(r'(\d{2,3})\s*[/／]\s*(\d{2,3})\s*(?:mmHg)?\s*'
        r'(?:属于?|为|达到|符合)\s*([123])级', text, re.I) if '血压' in text else None
    if reading:
        boundary = re.search(reading[3]+r'级[^。；;\n]{0,32}(?:≥|>=)\s*(\d{2,3})\s*[/／]\s*(\d{2,3})', quotes)
        if boundary and int(reading[1]) < int(boundary[1]) and int(reading[2]) < int(boundary[2]):
            raise ContractViolation('REVIEW_NUMERIC_THRESHOLD_CONFLICT', claim_index=claim.index)


def validate_review(raw, packet):
    output = ReviewSubmission.model_validate(raw)
    indices = [c.index for c in output.claims]
    if set(indices) != set(range(len(packet['claims']))) or len(indices) != len(set(indices)):
        raise ContractViolation('REVIEW_CLAIM_COVERAGE_INVALID')
    evidence = {e['id']: e for e in packet['evidence']}
    for claim in output.claims:
        required_kind = claim_review_kind(packet['claims'][claim.index])
        if (required_kind == 'project_behavior' and claim.support_status == 'supported'
                and claim.kind != 'project_behavior'):
            raise ContractViolation('REVIEW_POLICY_CLASSIFICATION_INVALID', claim_index=claim.index)
        if (claim.kind != 'medical_fact' and claim.support_status == 'supported'
                and required_kind == 'medical_fact'):
            raise ContractViolation('REVIEW_FACT_CLASSIFICATION_INVALID', claim_index=claim.index)
        if not claim.evidence_ids and getattr(claim, 'support_quotes', None):
            claim.evidence_ids = list(dict.fromkeys(q.evidence_id for q in claim.support_quotes if getattr(q, 'evidence_id', None) in evidence))
        if len(set(claim.evidence_ids)) != len(claim.evidence_ids) or not set(claim.evidence_ids) <= evidence.keys():
            raise ContractViolation('REVIEW_EVIDENCE_ID_INVALID', claim_index=claim.index)
        if not set(claim.policy_rules) <= packet['policy_rules'].keys():
            raise ContractViolation('REVIEW_POLICY_INVALID', claim_index=claim.index)
        if claim.kind == 'medical_fact' and claim.support_status in ('supported', 'partially_supported', 'contradicted') and not claim.evidence_ids:
            raise ContractViolation('REVIEW_MEDICAL_EVIDENCE_REQUIRED', claim_index=claim.index)
        if claim.kind == 'project_behavior' and claim.support_status == 'supported' and not claim.policy_rules:
            raise ContractViolation('REVIEW_POLICY_REQUIRED', claim_index=claim.index)
        check_support_quotes(claim, packet['claims'][claim.index]['text'], evidence, packet.get('require_support_quotes', False))
    return output


def retain_claim(claim):
    # 循证忠实度保证：只要在知识库中有确凿文献支持，均作为有效医学内容完整保留
    return claim.support_status == 'supported'


def reject_invalid_quote_claims(raw, packet):
    """After bounded repair, reject only bad quote claims; never approve invalid evidence."""
    candidate, issues = deepcopy(raw), []
    quote_errors = {'REVIEW_WITNESS_REQUIRED', 'REVIEW_WITNESS_INVALID', 'REVIEW_QUALIFIER_UNSUPPORTED',
        'REVIEW_SCOPE_UNSUPPORTED', 'REVIEW_CERTAINTY_UNSUPPORTED',
        'REVIEW_JUDGMENT_INCONSISTENT', 'REVIEW_NUMERIC_THRESHOLD_CONFLICT'}
    for _ in range(len(packet['claims'])+1):
        try:
            return validate_review(candidate, packet), issues
        except ContractViolation as error:
            index = error.counts.get('claim_index')
            if error.code not in quote_errors or type(index) is not int:
                raise
            claim = next(c for c in candidate['claims'] if c['index'] == index)
            # The original judgment/quote is preserved separately in review_trace.
            claim.update(support_status='unsupported', support_quotes=[],
                note=('原文短引句未通过校验（'+error.code+'），本条不保留。'+claim['note'])[:200])
            issues.append({'claim_index': index, 'code': error.code})
    raise ContractViolation('REVIEW_INVALID')


def apply_review(output, packet, sources):
    evidence = {e['id']: e for e in packet['evidence']}
    source_map = {s['id']: deepcopy(s) for s in packet.get('validated_sources', sources)}
    records, accepted, used_sources = [], [], set()
    final_position = 0
    for claim in sorted(output.claims, key=lambda c: c.index):
        span = packet['claims'][claim.index]
        anchors = [evidence[e] for e in claim.evidence_ids]
        record = {**claim.model_dump(), 'text': span['text'], 'draft_start': span['start'], 'draft_end': span['end'],
                  'evidence': anchors, 'professional_review': 'pending'}
        if 'original_draft_spans' in span: record['original_draft_spans'] = span['original_draft_spans']
        for key in ('preserved_facts', 'repair_targets'):
            if key in span: record[key] = span[key]
        for key in ('review_round', 'review_claim_index'):
            if key in span: record[key] = span[key]
        if retain_claim(claim):
            accepted.append(span['text'])
            record.update(final_start=final_position, final_end=final_position+len(span['text']))
            final_position += len(span['text'])
            for e in anchors:
                if e['source_id'] not in source_map:
                    raise ContractViolation('REVIEW_SOURCE_BINDING_INVALID')
                used_sources.add(e['source_id'])
                actual = {k: e[k] for k in ('start', 'end', 'quote')}
                spans = source_map[e['source_id']].setdefault('source_spans', [])
                if actual not in spans: spans.append(actual)
        else:
            record.update(final_start=None, final_end=None,
                exclusion_reason='outside_question' if claim.support_status == 'supported' else 'insufficient_support')
        records.append(record)
    omitted = sum(c.support_status != 'supported' for c in output.claims)
    scope_omitted = sum(c.support_status == 'supported' and c.scope_status == 'out_of_scope' for c in output.claims)
    answer = ''.join(accepted)
    if not answer.strip():
        answer = ('本轮未保留直接回应问题的内容，请重新表述需要解释的重点。' if scope_omitted and not omitted else
            '当前证据不足，无法给出有依据的医学结论，请补充原文或向医护核对。')
    # This fixed scope boundary is program policy, not a medical claim for a model to delete.
    notice_start = len(answer)+1
    answer += '\n' + POLICY_NOTICE
    records.append({'index': len(records), 'kind': 'corpus_scope', 'origin': 'program_policy',
        'support_status': 'supported', 'evidence_ids': [], 'evidence': [], 'policy_rules': ['educational_scope'],
        'text': POLICY_NOTICE, 'draft_start': None, 'draft_end': None, 'final_start': notice_start,
        'final_end': len(answer), 'note': '程序固定资料范围提示，不计入模型医学支持率。', 'professional_review': 'pending'})
    return {'answer': answer, 'sources': [source_map[k] for k in source_map if k in used_sources],
            'claim_reviews': records, 'omitted_claim_count': omitted,
            'scope_omitted_claim_count': scope_omitted, 'retained_claim_count': len(accepted),
            'reviewed_answer_sha256': hashlib.sha256(answer.encode()).hexdigest()}


def merge_rewrite(original, first_review, rewritten, second_review, atoms, replace_supported=False):
    """Omitted originals keep their verdict; only reviewed replacements supersede them."""
    protected = set() if replace_supported else {c.index for c in first_review.claims if c.support_status == 'supported'}
    covered = {i for atom in atoms.claims for i in atom.draft_indices} - protected
    entries = [(c.index, 0, original['claims'][c.index], c, 1, c.index)
               for c in first_review.claims if c.index not in covered]
    entries.extend((min(atoms.claims[c.index].draft_indices), c.index+1,
                    rewritten['claims'][c.index], c, 2, c.index) for c in second_review.claims
                   if not set(atoms.claims[c.index].draft_indices) <= protected)
    packet, claims = deepcopy(original), []
    packet['claims'] = []
    for i, (_, _, span, verdict, round_number, review_index) in enumerate(sorted(entries, key=lambda v: v[:2])):
        packet['claims'].append({**span, 'index': i, 'review_round': round_number,
                                 'review_claim_index': review_index})
        claims.append(verdict.model_copy(update={'index': i}))
    return packet, ComposedReview(claims=claims)


class MedicalReviewerMixin(ReviewTraceMixin):
    def _compact_reviewed(self, state, packet, output, applied, rounds):
        """One attempt; coverage + independent review, otherwise retain approved prose."""
        from .workflow import StopFlow
        self._save_review(state, {'review_rewrite_mode': 'compact'})
        try:
            atoms = self._contract_call({**state, 'review_packet': packet,
                'review_feedback': output.model_dump(), 'review_rewrite_mode': 'compact'},
                'review_rewrite', self.model.rewrite_review, lambda raw: validate_compaction(raw, packet, output),
                'REVIEW_COMPACTION_INVALID')
            candidate = atomic_packet(atoms, packet)
            kinds = {c.index: c.kind for c in output.claims}
            judgments = {c.index: c for c in output.claims}
            for i, claim in enumerate(candidate['claims']):
                claim.update(review_round=2, review_claim_index=i,
                    preserved_facts=[{'index': j, 'text': packet['claims'][j]['text'], 'kind': kinds[j]}
                        for j in atoms.claims[i].draft_indices if retain_claim(judgments[j])],
                    repair_targets=[{'index': j, 'text': packet['claims'][j]['text'], 'kind': kinds[j],
                        'note': judgments[j].note} for j in atoms.claims[i].draft_indices
                        if judgments[j].support_status != 'supported'])
            self._save_review(state, {'review_rewrite_status': 'awaiting_review'})
            reviewed = self._review_claims(state, candidate, 'review_again', 2)
            revised = apply_review(reviewed, candidate, state['sources'])
            rounds.append({'round': 2, 'claim_reviews': revised['claim_reviews'],
                'omitted_claim_count': revised['omitted_claim_count'],
                'scope_omitted_claim_count': revised['scope_omitted_claim_count'], 'purpose': 'compact'})
            self._save_review(state, {'review_rounds': rounds, 'review_rewrite_status':
                'compact_completed' if not revised['omitted_claim_count'] and revised['retained_claim_count'] else 'compact_rejected_retained'})
            if not revised['omitted_claim_count'] and revised['retained_claim_count']:
                merged, verdicts = merge_rewrite(packet, output, candidate, reviewed, atoms, replace_supported=True)
                return merged, verdicts, apply_review(verdicts, merged, state['sources'])
        except Exception as error:
            if isinstance(error, StopFlow) and (error.code == 'LEASE_LOST' or error.outcome != 'failed'): raise
            code = getattr(error, 'code', 'REVIEW_COMPACTION_FAILED')
            def failed(current):
                traces = current.get('review_trace', [])
                for trace in traces:
                    if trace['status'] == 'running': trace['status'] = 'failed'
                    for attempt in trace['attempts']:
                        if attempt['status'] == 'running': attempt.update(status='failed', diagnostic={'code': code})
                return {'review_trace': traces, 'review_rewrite_status': 'compact_failed_retained',
                    'review_rewrite_error_code': code}
            self._save_review(state, failed)
        return packet, output, applied

    def _review_claims(self, state, packet, stage, round_number):
        claims, size = [], 10
        total = (len(packet['claims'])+size-1)//size
        trace_id = self._trace_start(state, packet, round_number)
        for offset in range(0, len(packet['claims']), size):
            batch = {**packet, 'claims': [{**c, 'index': i}
                for i, c in enumerate(packet['claims'][offset:offset+size])]}
            self._save_review(state, {'review_batch_progress': {'round': round_number,
                'completed_batches': offset//size, 'total_batches': total,
                'active_batch': offset//size+1, 'global_offset': offset}})
            output = self._trace_review_call(state, batch, stage, trace_id, offset)
            claims.extend(c.model_copy(update={'index': c.index+offset}) for c in output.claims)
            self._save_review(state, {'review_batch_progress': {'round': round_number,
                'completed_batches': offset//size+1, 'total_batches': total}})
        self._trace_update(state, trace_id, lambda trace: trace.update(status='completed'))
        return ReviewSubmission(claims=claims)

    def _claim_review_rewrite(self, state):
        from .models import Run
        from .workflow import details, StopFlow
        with self.store.sessions() as db:
            db.connection().exec_driver_sql('BEGIN IMMEDIATE')
            run = db.get(Run, state['run_id'])
            current = details(run)
            if current.get('lease_token') != self.controls[run.id][0]: raise StopFlow('LEASE_LOST')
            if current.get('review_rewrite_count', 0) >= 1: return False
            current.update(review_rewrite_count=1, review_rewrite_status='running')
            run.details_json = json.dumps(current, ensure_ascii=False)
            db.commit()
        return True

    def _save_review(self, state, metadata):
        from .models import Run
        from .workflow import details, StopFlow
        with self.store.sessions() as db:
            db.connection().exec_driver_sql('BEGIN IMMEDIATE')
            run = db.get(Run, state['run_id'])
            current = details(run)
            if current.get('lease_token') != self.controls[run.id][0]: raise StopFlow('LEASE_LOST')
            if callable(metadata): metadata = metadata(current)
            current.update(metadata)
            if metadata.get('reviewer_status') in ('failed', 'cancelled', 'timed_out'):
                for field in ('atomization_status', 'review_rewrite_status'):
                    if current.get(field) in ('running', 'awaiting_review'):
                        current[field] = metadata['reviewer_status']
                for trace in current.get('review_trace', []):
                    if trace['status'] == 'running': trace['status'] = metadata['reviewer_status']
                    for attempt in trace['attempts']:
                        if attempt['status'] == 'running':
                            attempt.update(status=metadata['reviewer_status'], diagnostic={
                                'code': metadata.get('reviewer_error_code')})
            run.details_json = json.dumps(current, ensure_ascii=False)
            db.commit()

    def _review_output(self, state):
        from .workflow import StopFlow
        if (self.settings.knowledge_profile != 'medical' or not self.settings.medical_reviewer_enabled
                or not (self.settings.deepseek_enabled or hasattr(self.model, 'review'))): return {}
        if state['context'].get('urgent_skipped'):
            self._save_review(state, {'reviewer_status': 'skipped_policy'})
            return {}
        if is_policy_or_refusal(state.get('answer', ''), state.get('question', '')):
            self._save_review(state, {'reviewer_status': 'skipped_policy', 'citation_support_status': 'policy_exempt',
                'clinical_review_status': 'not_run'})
            return {}
        if state['outcome'] not in ('completed', 'partial') or not state['answer']: return {}
        try:
            self._save_review(state, {'reviewer_status': 'running'})
            packet = build_packet(state['question'], state['answer'], state['sources'])
            packet['require_support_quotes'] = self.settings.deepseek_enabled
            packet['require_scope_review'] = self.settings.deepseek_enabled
            for diagnostic in packet['source_diagnostics']:
                self._evidence_diagnostic(state, {'stage': 'review_source_binding', **diagnostic})
            if hasattr(self.model, 'atomize'):
                self._save_review(state, {'atomization_status': 'running'})
                try:
                    atoms = self._contract_call({**state, 'review_packet': packet}, 'atomize', self.model.atomize,
                        lambda raw: validate_atoms(raw, packet), 'ATOM_INVALID')
                    packet = atomic_packet(atoms, packet)
                    self._save_review(state, {'atomization_status': 'completed'})
                except StopFlow as error:
                    # Recovery is for an exhausted output contract, never execution controls.
                    if error.code not in ('ATOM_INVALID', 'MODEL_JSON_INVALID', 'MODEL_STRUCTURED_CALL_INVALID'):
                        raise
                    self._save_review(state, {'atomization_status': 'fallback_raw_claims', 'atomization_error_code': error.code})
            else:
                self._save_review(state, {'atomization_status': 'not_available'})
            self._save_review(state, {'review_packet_summary': {'claims': len(packet['claims']),
                'evidence': len(packet['evidence']), 'chars': packet['evidence_packet_chars'],
                'documents': len({e['document_id'] for e in packet['evidence']})}})
            payload = {**state, 'review_packet': packet}
            output = self._review_claims(state, packet, 'review', 1)
            applied = apply_review(output, packet, state['sources'])
            rounds = [{'round': 1, 'claim_reviews': applied['claim_reviews'],
                       'omitted_claim_count': applied['omitted_claim_count'],
                       'scope_omitted_claim_count': applied['scope_omitted_claim_count']}]
            self._save_review(state, {'review_rounds': rounds, 'review_rewrite_status': 'not_needed'})
            limit = requested_answer_limit(state['question'])
            too_long = limit and sum(len(c['text']) for c in applied['claim_reviews']
                if c.get('final_start') is not None and c.get('origin') != 'program_policy') > limit
            if (limit and (applied['omitted_claim_count'] or too_long) and hasattr(self.model, 'rewrite_review')
                    and self._claim_review_rewrite(state)):
                packet, output, applied = self._compact_reviewed(state, packet, output, applied, rounds)
            elif applied['omitted_claim_count'] and hasattr(self.model, 'rewrite_review') and self._claim_review_rewrite(state):
                original_packet, first_review = packet, output
                rewrite_payload = {**payload, 'review_feedback': output.model_dump()}
                rewritten = self._contract_call(rewrite_payload, 'review_rewrite', self.model.rewrite_review,
                    lambda raw: validate_atoms(raw, packet, complete=False), 'REVIEW_REWRITE_INVALID')
                if rewritten.claims:
                    packet = atomic_packet(rewritten, packet)
                    self._save_review(state, {'review_rewrite_status': 'awaiting_review'})
                    # Never persist rewritten prose before mandatory independent review.
                    output = self._review_claims(state, packet, 'review_again', 2)
                    applied = apply_review(output, packet, state['sources'])
                    rounds.append({'round': 2, 'claim_reviews': applied['claim_reviews'],
                                   'omitted_claim_count': applied['omitted_claim_count'],
                                   'scope_omitted_claim_count': applied['scope_omitted_claim_count']})
                    packet, output = merge_rewrite(original_packet, first_review, packet, output, rewritten)
                    applied = apply_review(output, packet, state['sources'])
                self._save_review(state, {'review_rounds': rounds,
                    'review_rewrite_status': 'completed' if rewritten.claims else 'no_supported_replacement'})
        except StopFlow as error:
            if error.code == 'LEASE_LOST': raise
            if error.outcome in ('cancelled', 'timed_out'):
                self._save_review(state, {'reviewer_status': error.outcome, 'reviewer_error_code': error.code})
                raise
            code = error.code
        except ContractViolation as error:
            code = error.code
        except Exception as exc:
            import traceback
            traceback.print_exc()
            code = 'REVIEW_FAILED'
        else:
            limit = requested_answer_limit(state['question'])
            body_chars = sum(len(c['text']) for c in applied['claim_reviews']
                if c.get('final_start') is not None and c.get('origin') != 'program_policy')
            too_long = limit is not None and body_chars > limit
            scope_empty = not applied['retained_claim_count']
            self._save_review(state, {**{k: applied[k] for k in ('claim_reviews', 'omitted_claim_count',
                'scope_omitted_claim_count', 'retained_claim_count', 'reviewed_answer_sha256')},
                'reviewer_status': 'completed', 'citation_support_status': 'model_reviewed',
                'answer_body_chars': body_chars, 'answer_max_chars': limit,
                'answer_length_status': 'exceeded' if too_long else 'passed' if limit else 'not_requested',
                'clinical_review_status': 'not_run', 'reviewer_error_code': None})
            return {'answer': applied['answer'], 'sources': applied['sources'],
                'outcome': 'partial' if applied['omitted_claim_count'] or scope_empty or too_long or state['outcome'] == 'partial' else 'completed',
                'error_code': 'REVIEW_SUPPORT_INCOMPLETE' if applied['omitted_claim_count'] else
                    'ANSWER_SCOPE_INCOMPLETE' if scope_empty else
                    'ANSWER_LENGTH_EXCEEDED' if too_long else state['error_code']}
        self._save_review(state, {'reviewer_status': 'failed', 'reviewer_error_code': code,
            'citation_support_status': 'unverified', 'clinical_review_status': 'not_run'})
        # Never persist an unreviewed medical draft as the final user-facing answer.
        return {'outcome': 'partial', 'error_code': code, 'sources': [],
                'answer': '本轮逐项引用审核未完成，暂不返回未经审核的医学结论。请查看运行状态，或提供具体原文后再试。'}
