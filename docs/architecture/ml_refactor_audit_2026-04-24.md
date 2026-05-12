# ML Audit and Safe Refactor (2026-04-24)

## Scope
Repository audit for unused/outdated/architecture-incompatible ML artifacts against the active MVP bot pipeline.

## Active Runtime Architecture (kept)
- `PatternAnalysisService` (`backend/app/services/pattern_analysis_service.py`)
- `SafetyGateService` (`backend/app/services/orchestration/decision_pipeline.py`)
- `RecommendationService` (`backend/app/services/orchestration/decision_pipeline.py`)
- `QwenResponseService` (`backend/app/llm/response_composer.py`)
- `ResponseValidationService` (`backend/app/services/orchestration/decision_pipeline.py`)
- `ChatOrchestratorService` (`backend/app/services/orchestration/decision_pipeline.py`)

Dependency wiring validated in `backend/app/api/deps.py` and endpoint wiring in:
- `backend/app/api/v1/endpoints/support_decision.py`
- `backend/app/api/v1/endpoints/wellbeing_signals.py`

## Findings by Category

### A. Safe to delete (unreferenced)
- `backend/app/services/analysis/feature_extractor.py`
- `backend/app/services/analysis/pattern_analyzer.py`
- `backend/app/services/analysis/__init__.py`
- `mental_health_app/lib/core/services/analytics_service.dart`

Rationale: no imports/references found in runtime, tests, API wiring, DI, or scripts.

### B. Archived (legacy, potentially useful as historical reference)
- `mental_health_app/ml/` -> `mental_health_app/legacy/ml/`
- `mental_health_app/ML_INTEGRATION.md` -> `mental_health_app/legacy/ML_INTEGRATION.md`
- `model_config.yaml` -> `legacy/ml/model_config.yaml`
- `IMPLEMENTATION_SUMMARY.md` -> `legacy/ml/IMPLEMENTATION_SUMMARY.md`

Rationale: ML training/experimental stack does not participate in current backend MVP decision pipeline.

### C. Kept but documented as legacy-coupled
- `mental_health_app/lib/core/services/ml_service.dart`

Rationale: still used by mobile providers (`mood_provider.dart`, `chat_provider.dart`). Removing would break app behavior.

### D. Merge candidates (not changed in this refactor)
- None applied to minimize churn/risk.

### E. Uncertain (explicitly not auto-deleted)
- Mobile chat/rules modules still in active Flutter runtime:
  - `mental_health_app/lib/core/services/chatbot_service.dart`
  - `mental_health_app/lib/core/services/clinical_rules_service.dart`
  - `mental_health_app/lib/core/services/clinical_rules_engine.dart`

Rationale: architecture-incompatible with server-orchestrated bot direction, but currently wired and runtime-active in mobile app.

## Safety checks performed
- Import/reference search across backend, mobile, tests, docs.
- API route and DI inspection.
- Contract/integration/unit test folder review.
- Infra/deploy file inspection for ML service wiring.

## Result
- Active backend MVP architecture is unchanged and now more discoverable.
- Orphaned backend analysis package removed.
- Legacy ML training/experimental assets moved out of active paths into `legacy/`.
