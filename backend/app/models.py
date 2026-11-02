from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_id():
    return str(uuid4())


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(40), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class Conversation(Base):
    __tablename__ = 'sessions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    title: Mapped[str] = mapped_column(String(100))
    next_seq: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)
    updated_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class Run(Base):
    __tablename__ = 'runs'
    __table_args__ = (UniqueConstraint('user_id', 'request_id'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'), index=True)
    request_id: Mapped[str] = mapped_column(String(36))
    fingerprint: Mapped[str] = mapped_column(String(64))
    run_status: Mapped[str] = mapped_column(String(20), default='running')
    result_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    safe_error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)
    finished_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    details_json: Mapped[str] = mapped_column(Text, default='{}', server_default='{}')
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False, server_default='0')


class Message(Base):
    __tablename__ = 'messages'
    __table_args__ = (
        UniqueConstraint('session_id', 'seq'),
        CheckConstraint("role in ('user', 'assistant')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'), index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey('runs.id'), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(12))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)



class ExecutionEvent(Base):
    __tablename__ = 'execution_events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey('runs.id'), index=True)
    stage: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20))
    event_key: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class ProviderCall(Base):
    __tablename__ = 'provider_calls'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str | None] = mapped_column(ForeignKey('runs.id'), index=True, nullable=True)
    provider: Mapped[str] = mapped_column(String(20))
    operation: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default='started')
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    safe_error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    elapsed_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    usage_json: Mapped[str] = mapped_column(Text, default='{}')
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class SessionSummary(Base):
    __tablename__ = 'session_summaries'
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    content: Mapped[str] = mapped_column(Text, default='')
    covered_until_seq: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=0)
    input_hash: Mapped[str] = mapped_column(String(64), default='')
    status: Mapped[str] = mapped_column(String(30), default='empty')
    updated_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class MemoryFact(Base):
    __tablename__ = 'memory_facts'
    __table_args__ = (UniqueConstraint('user_id', 'key'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    key: Mapped[str] = mapped_column(String(40))
    content: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str] = mapped_column(String(30), default='self')
    version: Mapped[int] = mapped_column(Integer, default=1)
    synced_version: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default='active')
    remote_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_message_ids_json: Mapped[str] = mapped_column(Text, default='[]')
    current_source_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    updated_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class SessionLearningState(Base):
    __tablename__ = 'session_learning_states'
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    learning_goal: Mapped[str] = mapped_column(String(200), default='心血管与慢病循证知识学习')
    completed_topics_json: Mapped[str] = mapped_column(Text, default='[]')
    unresolved_questions_json: Mapped[str] = mapped_column(Text, default='[]')
    next_steps_json: Mapped[str] = mapped_column(Text, default='[]')
    last_topic: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_entities_json: Mapped[str] = mapped_column(Text, default='[]')
    updated_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class MemoryJob(Base):
    __tablename__ = 'memory_jobs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    operation_key: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey('runs.id'), index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'), index=True)
    fact_id: Mapped[str | None] = mapped_column(ForeignKey('memory_facts.id'), nullable=True)
    action: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text, default='')
    version: Mapped[int] = mapped_column(Integer, default=0)
    covered_until_seq: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default='pending')
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    remote_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    event_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lease_token: Mapped[str | None] = mapped_column(String(36), nullable=True)
    lease_until: Mapped[float] = mapped_column(Float, default=0)
    safe_error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)
    updated_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class FakeMemoryBlob(Base):
    __tablename__ = 'fake_memory_blobs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[str] = mapped_column(Text, default='{}')


class RegistrationDraft(Base):
    __tablename__ = 'registration_drafts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'), index=True)
    fields_json: Mapped[str] = mapped_column(Text)
    issues_json: Mapped[str] = mapped_column(Text, default='{}')
    revision: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(24))
    confirmation_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)
    updated_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class RegistrationRecord(Base):
    __tablename__ = 'registration_records'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    draft_id: Mapped[str] = mapped_column(ForeignKey('registration_drafts.id'), unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    fields_json: Mapped[str] = mapped_column(Text)
    sample_ids_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class RegistrationAction(Base):
    __tablename__ = 'registration_actions'
    __table_args__ = (UniqueConstraint('user_id', 'request_id'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    draft_id: Mapped[str] = mapped_column(ForeignKey('registration_drafts.id'), index=True)
    request_id: Mapped[str] = mapped_column(String(36))
    fingerprint: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(20))
    response_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)
