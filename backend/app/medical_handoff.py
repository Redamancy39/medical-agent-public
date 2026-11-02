"""Dot exports are proposals. Validation never updates the corpus or gold set."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator
from .medical_evaluation import validate_dataset, DATASET_ROOT
from .medical_ingestion import _json_write


class HandoffModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Evidence(HandoffModel):
    url: HttpUrl
    locator: str = Field(min_length=1, max_length=500)
    quote: str | None = Field(default=None, max_length=800)
    access_status: Literal['opened', 'unavailable']

    @field_validator('url')
    @classmethod
    def public_https(cls, value):
        if value.scheme != 'https' or value.username or value.password:
            raise ValueError('PUBLIC_HTTPS_URL_REQUIRED')
        return value


class SourceCandidate(HandoffModel):
    id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,100}$')
    title: str = Field(min_length=1, max_length=300)
    url: HttpUrl
    publisher: str | None = Field(default=None, max_length=300)
    publication_date: str | None = Field(default=None, max_length=40)
    version: str | None = Field(default=None, max_length=100)
    jurisdiction: str | None = Field(default=None, max_length=100)
    population: str | None = Field(default=None, max_length=500)
    reuse_status: Literal['verified', 'unconfirmed', 'unavailable'] = 'unconfirmed'
    reuse_evidence_url: HttpUrl | None = None
    access_status: Literal['opened', 'unavailable']
    notes: str = Field(default='', max_length=2000)

    @field_validator('url', 'reuse_evidence_url')
    @classmethod
    def public_https(cls, value):
        if value is not None and (value.scheme != 'https' or value.username or value.password):
            raise ValueError('PUBLIC_HTTPS_URL_REQUIRED')
        return value

    @model_validator(mode='after')
    def reuse_evidence_required(self):
        if self.reuse_status == 'verified' and not self.reuse_evidence_url:
            raise ValueError('REUSE_EVIDENCE_REQUIRED')
        return self


class PointAudit(HandoffModel):
    case_id: str = Field(min_length=1, max_length=100)
    reference_point: str = Field(min_length=1, max_length=2000)
    reference_kind: Literal['medical_fact', 'project_behavior'] = 'medical_fact'
    issue_type: Literal['none', 'citation_gap', 'unsupported_claim', 'contradicted_claim',
        'scope_or_version_mismatch', 'source_metadata_issue', 'unavailable']
    support_status: Literal['supported', 'partially_supported', 'contradicted', 'insufficient_evidence']
    evidence: list[Evidence] = Field(default_factory=list, max_length=10)
    rule_ids: list[str] = Field(default_factory=list, max_length=10)
    suggested_change: str = Field(default='', max_length=3000)
    professional_review: Literal['pending'] = 'pending'

    @model_validator(mode='after')
    def evidence_required(self):
        if self.reference_kind == 'medical_fact' and self.support_status in ('supported', 'contradicted'):
            if not any(e.access_status == 'opened' and e.quote for e in self.evidence):
                raise ValueError('POINT_EVIDENCE_REQUIRED')
        if self.reference_kind == 'project_behavior' and not self.rule_ids:
            raise ValueError('PROJECT_POLICY_REQUIRED')
        return self


class HandoffBatch(HandoffModel):
    schema_version: Literal['medical-handoff-v1']
    batch_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,100}$')
    created_at: datetime
    sources: list[SourceCandidate] = Field(default_factory=list, max_length=100)
    audits: list[PointAudit] = Field(default_factory=list, max_length=1000)

    @model_validator(mode='after')
    def unique_source_ids(self):
        if self.created_at.tzinfo is None: raise ValueError('TIMEZONE_REQUIRED')
        if len({s.id for s in self.sources}) != len(self.sources): raise ValueError('DUPLICATE_SOURCE_ID')
        if not self.sources and not self.audits: raise ValueError('EMPTY_HANDOFF')
        return self


def stage_handoff(payload, root, *, allow_test_audit=False):
    batch = HandoffBatch.model_validate(payload)
    cases = {c['id']: c for c in validate_dataset()}
    rules = set(json.loads((DATASET_ROOT / 'policy.json').read_text(encoding='utf-8'))['rules'])
    for audit in batch.audits:
        if audit.case_id not in cases: raise ValueError('UNKNOWN_CASE_ID')
        if cases[audit.case_id]['split'] == 'test' and not allow_test_audit:
            raise ValueError('TEST_AUDIT_PAUSED')
        if not set(audit.rule_ids) <= rules: raise ValueError('UNKNOWN_POLICY_RULE')
    data = batch.model_dump(mode='json')
    digest = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / (batch.batch_id + '.json')
    summary = {'batch_id': batch.batch_id, 'sha256': digest, 'source_candidates': len(batch.sources),
        'point_audits': len(batch.audits), 'status': 'staged_for_review',
        'validation': 'structure_and_case_scope_only', 'clinical_review': 'not_run',
        'corpus_update': 'not_applied', 'dataset_update': 'not_applied'}
    if path.exists():
        existing = json.loads(path.read_text(encoding='utf-8'))
        if existing['summary']['sha256'] != digest: raise ValueError('BATCH_ID_CONTENT_CHANGED')
        return {**existing['summary'], 'replayed': True}
    # Cross-batch URL comparisons distinguish a new source from a changed note.
    prior_sources = {}
    prior_batches = []
    for previous in root.glob('*.json'):
        prior = json.loads(previous.read_text(encoding='utf-8'))
        if 'batch' in prior:
            prior_batches.append(HandoffBatch.model_validate(prior['batch']))
    for prior in sorted(prior_batches, key=lambda b: b.created_at):
        for source in prior.sources:
            prior_sources[str(source.url).split('#', 1)[0].rstrip('/')] = source.model_dump(mode='json')
    changes = {'new_source_candidates': 0, 'updated_source_candidates': 0, 'unchanged_source_candidates': 0}
    for source in batch.sources:
        key = str(source.url).split('#', 1)[0].rstrip('/')
        previous = prior_sources.get(key)
        current = source.model_dump(mode='json')
        label = 'new' if previous is None else ('unchanged' if previous == current else 'updated')
        changes[label + '_source_candidates'] += 1
        prior_sources[key] = current
    summary.update(changes)
    _json_write(path, {'summary': summary, 'batch': data})
    return {**summary, 'replayed': False}
