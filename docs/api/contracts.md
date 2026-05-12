# API Contracts

## Endpoints
- `GET /api/v1/health`
- `POST /api/v1/wellbeing-signals`
- `POST /api/v1/support-decision`

## Health
`GET /api/v1/health` returns one of:
- `status: "ok"` when backend, retrieval, BGE dim, and pgvector dim are compatible.
- `status: "degraded"` with `retrieval_status: "disabled"` when `MEMORY_RETRIEVAL_ENABLED=false`.
- `status: "unhealthy"` with HTTP `503` when retrieval is enabled and the embedding dim contract fails.

Embedding dim contract:
- `backend_expected_dim: 1024`
- `bge_reported_dim: 1024`
- `pgvector_column_dim: 1024`

When retrieval is disabled, BGE and pgvector checks are skipped and `embedding_dim_contract.skipped_reason` is `retrieval_disabled`.

## Core request
`SupportDecisionRequest`
- `user_id: string`
- `client_timestamp: datetime | null`
- `signals: WellbeingSignals`
- `dialogue_state: DialogueState | null`

`DialogueState`
- `version: 1`
- `turn_index: integer | null`
- `last_bot_action: string | null`
- `stop_requested: bool`
- `ui_state: string | null`

Legacy request shape `{ "state": "followup_wait" }` is accepted during transition and mapped to `ui_state`.

## Core response
`SupportDecisionResponse`
- `decision.support_mode: string`
- `decision.assessor_action: string`
- `decision.reasoning_tags: string[]`
- `safety.risk_level: low|medium|high|urgent|crisis`
- `safety.risk_score: float`
- `safety.flags: string[]`
- `safety.escalation_required: bool`
- `llm_response: string`
- `practice_card_id: string | null`
- `recommended_action: string`
- `recommended_action_deprecated: true`

`decision.assessor_action` is the assessor domain action. `practice_card_id` is the practice recommendation domain value. Top-level `recommended_action` is legacy compatibility for clients that still expect a practice action and must be treated as deprecated.
