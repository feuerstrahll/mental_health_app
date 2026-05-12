# Mental Well-being MVP Monorepo

This repository is organized as a modular monorepo for a Flutter mobile client, FastAPI backend, and deployment infrastructure.

## Top-level modules
- `mental_health_app/`: Existing Flutter app (kept as-is for MVP initialization).
- `mobile/`: Target Flutter architecture template and migration notes.
- `backend/`: FastAPI service for validation, feature extraction, safety routing, rule-based support scoring, and Qwen composition.
- `infra/`: Docker, nginx, env examples, and deployment scaffolding.
- `docs/`: Architecture, API, safety, model behavior, and setup documentation.
- `legacy/`: Archived, non-runtime artifacts kept for historical reference.

## Active MVP bot pipeline
- Feature extraction
- `SafetyGateService`
- Rule-based support profile/scoring (`backend/app/services/ml/support_model.py`)
- `QwenResponseService` (verbalization only)
- `ResponseValidationService`
- `ChatOrchestratorService`

## Archived ML artifacts
- Legacy ML training/config docs were moved to `legacy/ml/`.
- Legacy mobile ML experiment package was moved to `mental_health_app/legacy/ml/`.
- These files are not part of the active backend decision architecture.
- LightGBM artifacts remain archived only and are not imported or wired into the active backend pipeline.

## Quick start
- Backend local run: `cd backend && python -m uvicorn app.main:app --reload`
- Infra local stack: `docker compose -f infra/docker-compose.yml up --build`
