import os
import secrets
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values, set_key
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseModel):
    model_config = ConfigDict(extra='forbid')

    app_env: Literal['local', 'test'] = 'local'
    database_path: Path = BACKEND_ROOT / 'data' / 'app.db'
    jwt_secret: SecretStr = Field(repr=False, exclude=True)
    token_minutes: int = Field(default=60, ge=1, le=1440)
    jwt_issuer: str = 'medical-agent-local'
    jwt_audience: str = 'medical-agent-api'
    deepseek_api_key: SecretStr = Field(default=SecretStr(''), repr=False, exclude=True)
    mem0_api_key: SecretStr = Field(default=SecretStr(''), repr=False, exclude=True)
    deepseek_base_url: str = 'https://api.deepseek.com'
    deepseek_model: str = 'deepseek-flash'
    # None preserves the application's provider default; evaluations set an explicit value.
    deepseek_temperature: float | None = Field(default=None, ge=0, le=2)
    deepseek_thinking_enabled: bool = False
    deepseek_enabled: bool = False
    mem0_enabled: bool = False
    web_search_enabled: bool = False
    knowledge_enabled: bool = False
    knowledge_profile: Literal['synthetic', 'medical'] = 'synthetic'
    medical_reviewer_enabled: bool = True
    knowledge_path: Path = BACKEND_ROOT / 'data' / 'knowledge_v3.db'
    embedding_cache: Path = BACKEND_ROOT / 'data' / 'models'
    reranker_enabled: bool = False
    reranker_device: Literal['auto', 'cpu', 'cuda'] = 'auto'
    reranker_path: Path = Path('D:/rag_project/models/reranker/bge-reranker-v2-m3')
    reranker_threshold: float = Field(default=0.60, ge=0.0, le=1.0)
    search_top_k: int = Field(default=5, ge=1, le=10)
    provider_timeout_seconds: float = Field(default=15, gt=0, le=40)
    model_max_tokens: int = Field(default=4096, ge=128, le=8192)
    reviewer_max_tokens: int = Field(default=4096, ge=256, le=8192)
    # Per plan/synthesis/review stage; worker repair is shared across all workers.
    # All repair calls still consume the same run/provider model budgets.
    schema_repair_limit: int = Field(default=1, ge=0, le=1)
    maintenance_enabled: bool = True
    maintenance_batch_size: int = Field(default=3, ge=1, le=10)
    recent_turns: int = Field(default=10, ge=1, le=20)
    summary_max_chars: int = Field(default=3000, ge=200, le=6000)
    cloud_model_request_limit: int = Field(default=2000, ge=1, le=50000)
    cloud_memory_request_limit: int = Field(default=2000, ge=1, le=50000)
    cloud_web_request_limit: int = Field(default=500, ge=1, le=5000)
    max_model_calls: int = Field(default=20, ge=1, le=30)
    max_tool_calls: int = Field(default=6, ge=0, le=15)
    max_worker_model_calls: int = Field(default=6, ge=1, le=8)
    max_worker_tool_calls: int = Field(default=5, ge=0, le=8)
    max_parallel_tasks: int = Field(default=2, ge=1, le=2)
    max_worker_iterations: int = Field(default=5, ge=1, le=5)
    run_timeout_seconds: float = Field(default=90, gt=0, le=120)
    step_timeout_seconds: float = Field(default=25, gt=0, le=60)
    max_context_chars: int = Field(default=16000, ge=100, le=64000)

    @property
    def knowledge_database(self):
        if self.knowledge_profile == 'medical' and self.knowledge_path == BACKEND_ROOT / 'data/knowledge_v3.db':
            return BACKEND_ROOT / 'data/knowledge_medical_v1.db'
        return self.knowledge_path

    @field_validator('database_path', 'knowledge_path', 'embedding_cache', 'reranker_path')
    @classmethod
    def resolve_database_path(cls, value):
        return (value if value.is_absolute() else BACKEND_ROOT / value).resolve()

    @field_validator('jwt_secret')
    @classmethod
    def check_secret(cls, value):
        if len(value.get_secret_value().encode('utf-8')) < 32:
            raise ValueError('JWT签名密钥至少需要32字节')
        return value


def load_settings(env_file: Path = BACKEND_ROOT / '.env') -> Settings:
    """Read private values inside the application, never log or return them."""
    try:
        values = dotenv_values(env_file, interpolate=False)
        names = {
            'APP_ENV': 'app_env', 'DATABASE_PATH': 'database_path', 'JWT_SECRET': 'jwt_secret',
            'DEEPSEEK_API_KEY': 'deepseek_api_key', 'MEM0_API_KEY': 'mem0_api_key',
            'DEEPSEEK_BASE_URL': 'deepseek_base_url', 'DEEPSEEK_MODEL': 'deepseek_model',
            'DEEPSEEK_THINKING_ENABLED': 'deepseek_thinking_enabled',
            'DEEPSEEK_ENABLED': 'deepseek_enabled', 'MEM0_ENABLED': 'mem0_enabled',
            'WEB_SEARCH_ENABLED': 'web_search_enabled',
            'KNOWLEDGE_ENABLED': 'knowledge_enabled', 'KNOWLEDGE_PATH': 'knowledge_path',
            'KNOWLEDGE_PROFILE': 'knowledge_profile',
            'MEDICAL_REVIEWER_ENABLED': 'medical_reviewer_enabled',
            'EMBEDDING_CACHE': 'embedding_cache', 'MAINTENANCE_ENABLED': 'maintenance_enabled',
            'RERANKER_ENABLED': 'reranker_enabled', 'RERANKER_PATH': 'reranker_path',
            'RERANKER_DEVICE': 'reranker_device',
            'PROVIDER_TIMEOUT_SECONDS': 'provider_timeout_seconds', 'MODEL_MAX_TOKENS': 'model_max_tokens',
            'REVIEWER_MAX_TOKENS': 'reviewer_max_tokens',
            'RUN_TIMEOUT_SECONDS': 'run_timeout_seconds', 'STEP_TIMEOUT_SECONDS': 'step_timeout_seconds',
            'MAX_MODEL_CALLS': 'max_model_calls', 'MAX_TOOL_CALLS': 'max_tool_calls',
        }
        data = {field: os.environ.get(name, values.get(name)) for name, field in names.items()}
        data = {key: value for key, value in data.items() if value is not None}
        if not data.get('jwt_secret'):
            data['jwt_secret'] = secrets.token_hex(32)
            env_file.parent.mkdir(parents=True, exist_ok=True)
            set_key(str(env_file), 'JWT_SECRET', data['jwt_secret'], encoding='utf-8')
        return Settings(**data)
    except (OSError, ValidationError):
        raise RuntimeError('配置读取或验证失败，请检查后端配置字段；详情不会包含密钥') from None
