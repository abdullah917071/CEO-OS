.PHONY: install dev api dashboard infra-up infra-down test lint format check

install:
	uv sync --all-groups
	npm --prefix apps/dashboard install

infra-up:
	docker compose up -d postgres redis

infra-down:
	docker compose down

api:
	uv run uvicorn apps.api.src.ceo_os_api.main:app --reload --port 8000

dashboard:
	npm --prefix apps/dashboard run dev

dev:
	docker compose up --build

test:
	uv run pytest
	npm --prefix apps/dashboard run test

lint:
	uv run ruff check .
	npm --prefix apps/dashboard run lint

format:
	uv run ruff format .

check: lint test
	npm --prefix apps/dashboard run build

