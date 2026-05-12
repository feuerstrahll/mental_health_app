# Migration Map (MVP)

Current app path: `../mental_health_app/`
Target app path: `./template_flutter_structure/`

## Suggested migration order
1. `lib/main.dart` -> `lib/main.dart`
2. `lib/core/` -> `lib/core/`
3. `lib/features/` -> `lib/features/`
4. `lib/providers/` -> `lib/core/state/` or `lib/features/*/state/`
5. `lib/models/` -> `lib/shared/models/` or feature domain models

## Non-goals for MVP init
- No functional migration in this step.
- No rewrite of existing Flutter architecture.
