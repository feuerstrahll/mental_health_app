# Model Behavior Policy

- Qwen is a response composer, not a decision engine.
- Backend decision fields are source of truth.
- If Qwen is unavailable, backend fallback response is returned.
- Safety outcomes must remain unchanged regardless of LLM output.
