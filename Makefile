.PHONY: backend-run backend-test infra-up infra-down

backend-run:
	cd backend && python -m uvicorn app.main:app --reload

backend-test:
	cd backend && python -m pytest -q

infra-up:
	docker compose -f infra/docker-compose.yml up --build

infra-down:
	docker compose -f infra/docker-compose.yml down -v
