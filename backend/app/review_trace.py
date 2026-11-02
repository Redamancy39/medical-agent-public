"""Bounded, owner-scoped review inputs and typed outcomes; no raw provider envelopes."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json

from pydantic import ValidationError
from .contracts import ContractViolation, contract_diagnostic
from .providers import ProviderError


class ReviewTraceMixin:
    def _trace_update(self, state, trace_id, change):
        def update(current):
            traces = current.get('review_trace', [])
            change(traces[trace_id])
            return {'review_trace': traces}
        self._save_review(state, update)

    def _trace_start(self, state, packet, round_number):
        from .medical_reviewer import (claim_review_kind, FACT_MARKERS, POLICY_BOUNDARY, RISK_BOUNDARY,
            FIXED_BOUNDARY, EVIDENCE_GAP, CLASSIFICATION_VERSION)
        drafts, draft_keys, claims = [], {}, []
        for claim in packet['claims']:
            ids = []
            for span in claim.get('original_draft_spans', [claim]):
                original = {k: span[k] for k in ('index', 'start', 'end', 'text')}
                key = json.dumps(original, sort_keys=True, ensure_ascii=False)
                if key not in draft_keys:
                    draft_keys[key] = len(drafts); drafts.append(original)
                ids.append(draft_keys[key])
            claims.append({**{k: claim[k] for k in ('index', 'start', 'end', 'text')}, 'draft_ids': ids,
                           'required_kind': claim_review_kind(claim),
                           **{k: claim[k] for k in ('preserved_facts', 'repair_targets') if k in claim}})
        snapshot = {'round': round_number, 'require_support_quotes': packet.get('require_support_quotes', False),
            'require_scope_review': packet.get('require_scope_review', False),
            'question_sha256': hashlib.sha256(state['question'].encode()).hexdigest(),
            'claims': claims, 'draft_spans': drafts, 'evidence': deepcopy(packet['evidence']),
            'policy_rules': packet['policy_rules'], 'corpus_scope': packet['corpus_scope'],
            'classification_rules_sha256': hashlib.sha256((CLASSIFICATION_VERSION+FACT_MARKERS.pattern+
                POLICY_BOUNDARY.pattern+RISK_BOUNDARY.pattern+FIXED_BOUNDARY.pattern+EVIDENCE_GAP.pattern).encode()).hexdigest()}
        snapshot['packet_sha256'] = hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        snapshot.update(status='running', attempts=[])
        result = []
        def update(current):
            from .workflow import StopFlow
            traces = current.get('review_trace', [])
            if len(traces) >= self.settings.max_model_calls: raise StopFlow('REVIEW_TRACE_LIMIT')
            result.append(len(traces)); traces.append(snapshot)
            return {'review_trace': traces}
        self._save_review(state, update)
        return result[0]

    def _trace_review_call(self, state, batch, stage, trace_id, offset):
        from .medical_reviewer import ReviewSubmission, validate_review, reject_invalid_quote_claims
        from .workflow import StopFlow
        attempt_id = []
        last = {}
        def begin(trace, repair):
            attempt_id[:] = [len(trace['attempts'])]
            trace['attempts'].append({'batch': offset//10+1, 'global_offset': offset,
                'claim_count': len(batch['claims']), 'status': 'running',
                'format_repair': repair,
                'started_at': datetime.now(timezone.utc).isoformat()})
        def finish(status, diagnostic=None, judgments=None, rejections=None):
            def change(trace):
                trace['attempts'][attempt_id[0]].update(status=status,
                    diagnostic=diagnostic, judgments=judgments or [], rejected_claims=rejections or [])
            self._trace_update(state, trace_id, change)
        def request(payload):
            self._trace_update(state, trace_id, lambda trace: begin(trace, bool(payload.get('contract_repair'))))
            try:
                return self.model.review(payload)
            except Exception as error:
                code = error.code if isinstance(error, (ProviderError, StopFlow)) else 'REVIEW_REQUEST_FAILED'
                finish('failed', {'stage': stage, 'code': code})
                raise
        def validate(raw):
            judgments = []
            last.update(raw=raw)
            try:
                typed = ReviewSubmission.model_validate(raw)
                evidence_ids = {e['id'] for e in batch['evidence']}
                for c in typed.claims:
                    judgments.append({'local_index': c.index, 'global_index': offset+c.index,
                        'kind': c.kind, 'support_status': c.support_status, 'note': c.note,
                        'scope_status': c.scope_status, 'scope_note': c.scope_note,
                        'support_quotes': [q.model_dump() for q in c.support_quotes if q.evidence_id in evidence_ids],
                        'evidence_ids': [e for e in c.evidence_ids if e in evidence_ids],
                        'unknown_evidence_count': sum(e not in evidence_ids for e in c.evidence_ids),
                        'policy_rules': [p for p in c.policy_rules if p in batch['policy_rules']]})
                output = validate_review(raw, batch)
            except (ValidationError, ContractViolation) as error:
                diagnostic = contract_diagnostic(stage, error, 'REVIEW_INVALID')
                local = diagnostic.get('claim_index')
                if type(local) is int and 0 <= local < len(batch['claims']):
                    diagnostic['global_claim_index'] = offset+local
                finish('failed', diagnostic, judgments)
                last.update(diagnostic=diagnostic, judgments=judgments)
                raise
            finish('completed', judgments=judgments)
            return output
        try:
            return self._contract_call({**state, 'review_packet': batch}, stage, request, validate, 'REVIEW_INVALID')
        except StopFlow as error:
            if error.code != 'REVIEW_INVALID' or 'raw' not in last:
                raise
            try:
                output, issues = reject_invalid_quote_claims(last['raw'], batch)
            except (ValidationError, ContractViolation):
                raise error
            if not issues: raise error
            finish('completed_with_rejections', last.get('diagnostic'), last.get('judgments'),
                [{**item, 'global_claim_index': offset+item['claim_index']} for item in issues])
            return output
