# Architecture Overview

## System boundaries
- Mobile app (`mental_health_app/`) captures daily well-being signals.
- Backend (`backend/`) validates, analyzes patterns, checks safety, and computes structured decisions.
- Qwen is used only to compose final text from backend decisions.

## Backend flow
1. API receives `WellbeingSignalsRequest`.
2. Analysis extracts features and pattern tags.
3. Safety computes risk score and escalation flags.
4. Recommendation selects support mode and action.
5. LLM adapter composes human-facing response.

## Non-goals for MVP
- No microservice split.
- No autonomous LLM decision logic.
