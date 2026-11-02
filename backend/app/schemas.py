from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class AuthInput(Input):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=False)
    username: str = Field(min_length=3, max_length=40, pattern=r'^[a-zA-Z0-9_.-]+$')
    password: str = Field(min_length=8, max_length=128)

    @field_validator('username', mode='before')
    @classmethod
    def normalize_username(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    username: str


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal['bearer'] = 'bearer'
    expires_in: int


class SessionInput(Input):
    title: str = Field(default='新会话', min_length=1, max_length=100)


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class SessionPage(BaseModel):
    items: list[SessionOut]
    total: int


class ChatInput(Input):
    question: str = Field(min_length=1, max_length=8000)
    request_id: UUID = Field(default_factory=uuid4)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    run_id: str
    seq: int
    role: Literal['user', 'assistant']
    content: str
    created_at: datetime


class MessagePage(BaseModel):
    items: list[MessageOut]
    has_more: bool
    next_after_seq: int


class RunOut(BaseModel):
    run_id: str
    request_id: str
    session_id: str
    run_status: Literal['running', 'awaiting_input', 'paused', 'finished', 'failed', 'cancelled', 'timed_out']
    result_status: Literal['completed', 'partial', 'failed', 'cancelled', 'timed_out'] | None
    answer: str | None
    safe_error_code: str | None
    mode: Literal['offline_fake', 'cloud_real', 'hybrid'] = 'offline_fake'
    replayed: bool = False
    graph_version: int | None = None
    checkpoint_id: str | None = None
    stage: str | None = None
    plan_status: str = 'legacy'
    plan_reason: str | None = None
    knowledge_profile: str | None = None
    agent_id: str | None = None
    model_calls: int | None = None
    tool_calls: int | None = None
    worker_iterations: int | None = None
    context_status: str | None = None
    response_origin: str = 'agent'
    safety_policy: str | None = None
    sources: list[dict] = Field(default_factory=list)
    cancel_requested: bool = False
    task_count: int | None = None
    distinct_agent_count: int | None = None
    planned_agent_count: int | None = None
    started_task_count: int | None = None
    completed_task_count: int | None = None
    failed_task_count: int | None = None
    blocked_task_count: int | None = None
    task_results: list[dict] = Field(default_factory=list)
    evidence_status: str = 'not_run'
    evidence_diagnostics: list[dict] = Field(default_factory=list)
    reviewer_status: str = 'not_run'
    atomization_status: str = 'not_run'
    atomization_error_code: str | None = None
    review_rewrite_count: int = 0
    review_rewrite_status: str = 'not_run'
    review_rewrite_mode: str | None = None
    review_rewrite_error_code: str | None = None
    review_rounds: list[dict] = Field(default_factory=list)
    review_packet_summary: dict = Field(default_factory=dict)
    review_batch_progress: dict = Field(default_factory=dict)
    review_trace: list[dict] = Field(default_factory=list)
    citation_support_status: str = 'not_run'
    clinical_review_status: str = 'not_run'
    reviewer_error_code: str | None = None
    claim_reviews: list[dict] = Field(default_factory=list)
    omitted_claim_count: int = 0
    scope_omitted_claim_count: int = 0
    retained_claim_count: int | None = None
    reviewed_answer_sha256: str | None = None
    answer_body_chars: int | None = None
    answer_max_chars: int | None = None
    answer_length_status: Literal['not_run', 'not_requested', 'passed', 'exceeded'] = 'not_run'
    evidence_issues: list[dict] = Field(default_factory=list)
    refinement_count: int = 0
    context_details: dict = Field(default_factory=dict)
    summary_coverage: int | None = None
    memory_write_status: str = 'legacy'
    summary_write_status: str = 'not_run'
    maintenance_error_code: str | None = None
    schema_repair_count: int = 0
    contract_repair_counts: dict[str, int] = Field(default_factory=dict)
    contract_diagnostics: list[dict] = Field(default_factory=list)
    provider_contract_details: dict = Field(default_factory=dict)
    learning_state: dict | None = None
    memory_fixed_preferences: dict = Field(default_factory=dict)


class SessionLearningStateOut(BaseModel):
    learning_goal: str
    completed_topics: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    last_topic: str | None = None
    last_entities: list[str] = Field(default_factory=list)
    updated_at: str


class MemoryEdit(Input):
    operation: Literal['update', 'delete']
    content: str | None = Field(default=None, min_length=1, max_length=300)

    @model_validator(mode='after')
    def valid_operation(self):
        if self.operation == 'update' and not self.content or self.operation == 'delete' and self.content:
            raise ValueError('操作与内容不匹配')
        return self


class ResumeInput(Input):
    checkpoint_id: str = Field(min_length=1, max_length=128)
    clarification: str | None = Field(default=None, min_length=1, max_length=8000)
