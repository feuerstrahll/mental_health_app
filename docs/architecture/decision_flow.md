# Decision Flow

`POST /api/v1/wellbeing-signals`

1. Validate input schema.
2. Extract features.
3. Evaluate safety with the deterministic safety router.
4. Apply rule-based support profile/scoring.
5. Retrieve practice/context support as needed.
6. Build structured decision.
7. Compose verbal response using Qwen adapter (optional).
