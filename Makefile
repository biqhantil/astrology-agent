# ── Astrology Agent — Developer Makefile ──────────────────────────────────────
# Stack: FastAPI + SQLite + Vite (local). Docker: backend + nginx.

.PHONY: help validate validate-unit validate-frontend validate-scenarios \
	dev-backend dev-frontend up down logs migrate seed test lint format clean sqlite

ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
BACKEND := $(ROOT)backend
FRONTEND := $(ROOT)frontend
PY := $(BACKEND)/.venv/bin/python
BASE_URL ?= http://localhost:8001

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ── Validation gates ──────────────────────────────────────────────────────────

validate: validate-unit validate-frontend ## Full gate: unit tests + FE typecheck/build

validate-unit: ## Backend unit/API tests (no live server)
	cd $(BACKEND) && $(PY) -m pytest tests/ -q --ignore=tests/scenarios

validate-frontend: ## Frontend tsc + production build
	cd $(FRONTEND) && npx tsc --noEmit && npx vite build

validate-scenarios: ## Scenario E2E against live API (BASE_URL=$(BASE_URL))
	cd $(BACKEND) && $(PY) -m tests.scenario_runner --base-url $(BASE_URL)

validate-harness: ## Live multi-turn chat harness (real LLM, API only — needs OPENCODE credits)
	cd $(BACKEND) && $(PY) -m tests.harness.multi_turn_runner --base-url $(BASE_URL) --timeout 180

test: validate-unit ## Alias for unit tests

# ── Local dev ─────────────────────────────────────────────────────────────────

dev-backend: ## uvicorn on :8001 (AUTH_DEV_MODE on)
	cd $(BACKEND) && AUTH_DEV_MODE_ENABLED=true $(PY) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

dev-frontend: ## Vite on :5174 (proxies /v1 → :8001)
	cd $(FRONTEND) && npm run dev

# ── Docker ────────────────────────────────────────────────────────────────────

up: ## Start docker compose (backend + nginx)
	docker compose up -d --build
	@echo "App: http://localhost (nginx). Backend internal :8000"

down: ## Stop docker compose
	docker compose down

logs: ## Follow docker logs
	docker compose logs -f

# ── Database (SQLite) ─────────────────────────────────────────────────────────

migrate: ## Apply SQLite migrations (local)
	cd $(BACKEND) && $(PY) run_migrations.py

seed: ## Seed local SQLite
	cd $(BACKEND) && $(PY) seed.py

sqlite: ## Open sqlite3 shell on local DB
	sqlite3 $(BACKEND)/data/astrology.db

# ── Lint ──────────────────────────────────────────────────────────────────────

lint: ## Ruff check backend
	cd $(BACKEND) && $(PY) -m ruff check app/ tests/

format: ## Ruff format backend
	cd $(BACKEND) && $(PY) -m ruff format app/ tests/

# ── Utilities ─────────────────────────────────────────────────────────────────

clean: ## Remove Python/JS caches
	find $(ROOT) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find $(ROOT) -type f -name '*.pyc' -delete
	rm -rf $(FRONTEND)/dist $(FRONTEND)/tsconfig*.tsbuildinfo 2>/dev/null || true
