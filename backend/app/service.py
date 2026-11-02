import json

from sqlalchemy import select

from .models import Conversation
from .schemas import RunOut


class ApiError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message


def owned_session(db, session_id, user_id):
    value = db.scalar(select(Conversation).where(Conversation.id == session_id, Conversation.user_id == user_id))
    if value is None:
        raise ApiError(404, 'SESSION_NOT_FOUND', '会话不存在或不可访问')
    return value


def run_output(run, replayed=False):
    metadata = json.loads(run.details_json)
    tasks = metadata.get('task_results', [])
    if tasks:
        metadata.update(started_task_count=sum(r['started'] for r in tasks),
                        completed_task_count=sum(r['status'] == 'completed' for r in tasks),
                        failed_task_count=sum(r['status'] in ('failed', 'timed_out', 'cancelled', 'partial') for r in tasks),
                        blocked_task_count=sum(r['status'] == 'blocked' for r in tasks))
    return RunOut(
        run_id=run.id, request_id=run.request_id, session_id=run.session_id,
        run_status=run.run_status, result_status=run.result_status,
        answer=run.answer, safe_error_code=run.safe_error_code, replayed=replayed,
        cancel_requested=run.cancel_requested,
        **{key: metadata[key] for key in ('graph_version', 'checkpoint_id', 'stage', 'plan_status', 'plan_reason', 'knowledge_profile', 'agent_id',
                                         'model_calls', 'tool_calls', 'worker_iterations', 'context_status', 'sources',
                                         'task_count', 'distinct_agent_count', 'task_results', 'evidence_status',
                                         'evidence_issues', 'refinement_count', 'planned_agent_count', 'started_task_count',
                                         'completed_task_count', 'failed_task_count', 'blocked_task_count', 'mode',
                                         'context_details', 'summary_coverage', 'memory_write_status',
                                         'summary_write_status', 'maintenance_error_code', 'schema_repair_count',
                                         'contract_repair_counts', 'contract_diagnostics', 'provider_contract_details',
                                         'response_origin', 'safety_policy', 'evidence_diagnostics', 'reviewer_status',
                                         'citation_support_status', 'clinical_review_status', 'reviewer_error_code',
                                         'claim_reviews', 'omitted_claim_count', 'reviewed_answer_sha256',
                                         'scope_omitted_claim_count', 'retained_claim_count',
                                         'answer_body_chars', 'answer_max_chars', 'answer_length_status',
                                         'atomization_status', 'atomization_error_code', 'review_rewrite_count', 'review_rewrite_status', 'review_rounds',
                                         'review_rewrite_mode', 'review_rewrite_error_code',
                                         'review_packet_summary', 'review_batch_progress', 'review_trace',
                                         'learning_state', 'memory_fixed_preferences') if key in metadata},
    )
