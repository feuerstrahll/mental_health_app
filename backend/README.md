# Backend Service

FastAPI backend that performs:
- request validation
- signal feature extraction
- deterministic safety routing
- rule-based support profile/scoring
- optional Qwen verbalization step (adapter-only)

## Run locally
1. Create and activate a Python 3.11+ virtualenv.
2. Install dependencies: `pip install -e .[dev]`
3. Run API: `python -m uvicorn app.main:app --reload`
4. Test: `python -m pytest`

## API
- `GET /api/v1/health`
- `POST /api/v1/wellbeing-signals`
- `POST /api/v1/support-decision`
