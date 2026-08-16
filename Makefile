.PHONY: install dev api dashboard infra-up infra-down test lint typecheck format build check

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

lint:
	uv run ruff check .
	npm --prefix apps/dashboard run lint

typecheck:
	uv run mypy
	npm --prefix apps/dashboard run typecheck

test:
	uv run pytest
	npm --prefix apps/dashboard test

format:
	uv run ruff format .

build:
	uv build
	npm --prefix apps/dashboard run build

check: lint typecheck test build
