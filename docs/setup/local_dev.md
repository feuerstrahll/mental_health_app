# Local Development Setup

## Prerequisites
- Python 3.11+
- Docker + Docker Compose

## Backend
1. `cd backend`
2. `pip install -e .[dev]`
3. `python -m uvicorn app.main:app --reload`
4. Open `http://localhost:8000/docs`

## Infra stack
- `docker compose -f infra/docker-compose.yml up --build`

## Existing Flutter app
- Current app remains in `mental_health_app/`.

## Qwen local setup
- See `docs/setup/qwen_local_deployment.md` for end-to-end local Qwen + backend + Flutter wiring.

## Yandex Cloud deploy
- See `infra/deploy/yandex/README.md` for VM-based backend deployment and rollback scripts.
