export type RunStatus =
  | 'running'
  | 'awaiting_input'
  | 'paused'
  | 'finished'
  | 'failed'
  | 'cancelled'
  | 'timed_out'

export type ResultStatus =
  | 'completed'
  | 'partial'
  | 'failed'
  | 'cancelled'
  | 'timed_out'
  | null

export type RunMode = 'offline_fake' | 'cloud_real' | 'hybrid'

export interface SourceSpan {
  start: number
  end: number
  quote: string
}

export interface SourceItem {
  id: string
  source: string
  content: string
  verified: boolean
  title: string | null
  url: string | null
  document_id?: string | null
  version?: string | null
  start?: number | null
  end?: number | null
  score?: number | null
  score_kind?: string | null
  content_kind?: string | null
  rerank_score?: number | null
  reranker?: string | null
  publisher?: string | null
  language?: string | null
  source_language?: string | null
  jurisdiction?: string | null
  source_family_id?: string | null
  source_sha256?: string | null
  raw_source_sha256?: string | null
  provenance_status?: string | null
  clinical_review_status?: string | null
  editorial_status?: string | null
  topic?: string | null
  publication_date?: string | null
  fetched_at?: string | null
  license?: string | null
  attribution?: string | null
  section?: string | null
  source_spans?: SourceSpan[]
}

export interface TaskResultItem {
  task_id: string
  agent_id: 'consultation_agent' | 'research_agent' | 'diagnostic_agent' | string
  description?: string
  depends_on: string[]
  status: string
  answer?: string | null
  sources?: SourceItem[]
  safe_error_code: string | null
  model_calls: number
  tool_calls: number
  worker_iterations?: number
  refined: boolean
  started?: boolean
}

export interface EvidenceAnchor {
  id: string
  source_id: string
  document_id: string
  source_sha256: string
  start: number
  end: number
  quote: string
  url: string | null
}

export interface OriginalDraftSpan {
  index: number
  start: number
  end: number
  text: string
}

export interface ClaimReviewItem {
  index: number
  kind: 'medical_fact' | 'project_behavior' | 'corpus_scope' | 'editorial' | string
  origin?: string
  support_status: 'supported' | 'partially_supported' | 'unsupported' | 'contradicted' | string
  evidence_ids: string[]
  evidence?: EvidenceAnchor[]
  policy_rules: string[]
  note: string
  text: string
  draft_start: number | null
  draft_end: number | null
  final_start: number | null
  final_end: number | null
  professional_review?: string
  review_round?: number
  review_claim_index?: number
  original_draft_spans?: OriginalDraftSpan[]
}

export interface ReviewRoundItem {
  round: number
  claim_reviews: ClaimReviewItem[]
  omitted_claim_count: number
}

export interface ReviewTraceAttempt {
  batch: number
  global_offset: number
  claim_count: number
  status: string
  format_repair: boolean
  started_at?: string
  diagnostic?: {
    stage?: string
    code?: string
    claim_index?: number
    global_claim_index?: number
  } | null
  judgments?: Array<{
    local_index: number
    global_index: number
    kind: string
    support_status: string
    note: string
    evidence_ids: string[]
    unknown_evidence_count?: number
    policy_rules: string[]
  }>
}

export interface ReviewTraceItem {
  round: number
  question_sha256: string
  packet_sha256: string
  corpus_scope: string
  status: string
  claims: Array<{
    index: number
    start: number
    end: number
    text: string
    draft_ids: number[]
    required_kind: string | null
  }>
  draft_spans: OriginalDraftSpan[]
  evidence: EvidenceAnchor[]
  policy_rules: Record<string, string>
  attempts: ReviewTraceAttempt[]
}

export interface EvidenceDiagnosticItem {
  task_id?: string | null
  stage: string
  tool?: string
  query_sha256?: string
  status?: string
  retrieved_count?: number
  retrieved_ids?: string[]
  selected_count?: number
  selected_ids?: string[]
  unknown_count?: number
  refinement?: boolean
  safe_error_code?: string | null
}

export interface ContractDiagnosticItem {
  stage: string
  code: string
  error_type?: string
  claim_index?: number
  global_claim_index?: number
}

export interface RunOut {
  run_id: string
  request_id: string
  session_id: string
  run_status: RunStatus
  result_status: ResultStatus
  answer: string | null
  safe_error_code: string | null
  mode: RunMode
  replayed?: boolean
  graph_version?: number | null
  checkpoint_id: string | null
  stage: string | null
  plan_status: string
  plan_reason?: string | null
  knowledge_profile?: string | null
  agent_id?: string | null
  model_calls: number | null
  tool_calls: number | null
  worker_iterations?: number | null
  context_status?: string | null
  response_origin?: string
  safety_policy?: string | null
  sources: SourceItem[]
  cancel_requested?: boolean
  task_count: number | null
  distinct_agent_count: number | null
  planned_agent_count?: number | null
  started_task_count?: number | null
  completed_task_count?: number | null
  failed_task_count?: number | null
  blocked_task_count?: number | null
  task_results: TaskResultItem[]
  evidence_status: string
  evidence_diagnostics?: EvidenceDiagnosticItem[]
  reviewer_status?: string
  atomization_status?: string
  review_rewrite_count?: number
  review_rewrite_status?: string
  review_rounds?: ReviewRoundItem[]
  review_packet_summary?: {
    claims?: number
    evidence?: number
    chars?: number
    documents?: number
  }
  review_batch_progress?: {
    round?: number
    completed_batches?: number
    total_batches?: number
    active_batch?: number
    global_offset?: number
  }
  review_trace?: ReviewTraceItem[]
  citation_support_status?: string
  clinical_review_status?: string
  reviewer_error_code?: string | null
  claim_reviews?: ClaimReviewItem[]
  omitted_claim_count?: number
  reviewed_answer_sha256?: string | null
  evidence_issues?: Array<{ code: string; task_id?: string; source_id?: string }>
  refinement_count: number
  context_details: {
    memory_status?: string
    memory_error_code?: string | null
    summary_status?: string
    older_history_omitted?: boolean
    history_truncated?: boolean
    memory_count?: number
  }
  summary_coverage?: number | null
  memory_write_status: string
  summary_write_status: string
  maintenance_error_code: string | null
  schema_repair_count: number
  contract_repair_counts?: Record<string, number>
  contract_diagnostics?: ContractDiagnosticItem[]
  provider_contract_details?: Record<string, unknown>
  learning_state?: {
    learning_goal?: string
    last_topic?: string | null
    completed_topics?: string[]
    unresolved_questions?: string[]
    next_steps?: string[]
  } | null
  memory_fixed_preferences?: Record<string, string>
}

export interface SessionItem {
  id: string
  title: string
  created_at?: string
  updated_at?: string
}

export interface MessageItem {
  id: string
  run_id?: string
  seq: number
  role: 'user' | 'assistant' | string
  content: string
  created_at?: string
}

export interface ExecutionEventItem {
  stage: string
  task_id: string | null
  status: string
  created_at?: string
}

export interface ProviderCallItem {
  provider: string
  operation: string
  status: string
  http_status: number | null
  safe_error_code: string | null
  elapsed_seconds?: number | null
  usage: {
    prompt_tokens?: number
    completion_tokens?: number
    total_tokens?: number
  }
}

export interface HealthStatus {
  status?: string
  database?: string
  mode: string
  external_calls_enabled: boolean
  providers: Record<string, string>
  workflow?: string
  graph_version?: number
  knowledge_profile?: string
}

export interface MemoryFactItem {
  id: string
  key: string
  content: string
  status: string
  version: number
  synced_version: number
}

export interface SessionSummaryItem {
  status: string
  content: string | null
  covered_until_seq: number
  version: number
}

export interface MaintenanceJobItem {
  id: string
  run_id?: string
  action: string
  status: string
  attempts: number
  safe_error_code: string | null
}

export interface KnowledgeCatalogSection {
  heading: string
  text: string
  quotes: string[]
}

export interface KnowledgeCatalogItem {
  id: string
  title: string
  title_en?: string
  topic: string
  topic_zh: string
  jurisdiction: string
  publisher: string
  publication_date: string
  url: string
  attribution?: string
  license?: string
  section_count: number
  sections: KnowledgeCatalogSection[]
}

export interface KnowledgeCatalogOverview {
  total_documents: number
  total_sections: number
  items: KnowledgeCatalogItem[]
}

