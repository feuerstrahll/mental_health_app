# Safety Policy (MVP)

- Safety checks run before recommendation and composition.
- `high` or `urgent` risk must set `escalation_required=true`.
- LLM output must not override safety classification.
- Emergency resource recommendation must be available for urgent outcomes.
- Keep auditable risk flags in backend decision objects.
