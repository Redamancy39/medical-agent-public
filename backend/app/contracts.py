"""Contract diagnostics contain types and counts, never model payloads."""
from pydantic import ValidationError
from .providers import ProviderError


class ContractViolation(ValueError):
    def __init__(self, code, **counts):
        self.code, self.counts = code, counts
        super().__init__(code)


def contract_diagnostic(stage, error, fallback_code):
    result = {'stage': stage, 'code': fallback_code}
    if isinstance(error, ValidationError):
        allowed = {'tasks', 'task_id', 'agent_id', 'description', 'depends_on', 'require_sources',
                   'reason', 'answer', 'task_ids', 'source_ids'}
        result['validation'] = [{'location': '.'.join(str(x) if isinstance(x, int) or x in allowed else 'unknown_field'
                    for x in item['loc']), 'type': item['type']}
            for item in error.errors(include_input=False, include_context=False)[:10]]
    elif isinstance(error, ContractViolation):
        result.update(code=error.code, **error.counts)
    elif isinstance(error, ProviderError):
        result['code'] = error.code
    return result
