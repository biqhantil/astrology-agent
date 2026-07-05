# ── Astrology Agent — Developer Makefile ──────────────────────────────────────

.PHONY: help up down logs psql migrate seed test lint clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Docker Compose ────────────────────────────────────────────────────────────

up: ## Start all services (Postgres, Redis, Backend)
	docker compose up -d
	@echo "Backend: http://localhost:8000"
	@echo "API docs: http://localhost:8000/docs"

down: ## Stop all services
	docker compose down

logs: ## Follow logs from all services
	docker compose logs -f

restart: down up ## Restart all services

# ── Database ──────────────────────────────────────────────────────────────────

psql: ## Open psql shell on the running postgres container
	docker compose exec postgres psql -U astrology -d astrology_agent

migrate: ## Run pending database migrations
	docker compose exec backend python run_migrations.py

seed: ## Seed the database with test data
	docker compose exec backend python seed.py

db-reset: ## Drop and recreate the database from scratch
	docker compose down -v
	docker compose up -d postgres redis
	@echo "Waiting for Postgres to be healthy..."
	@sleep 5
	docker compose exec postgres psql -U astrology -d astrology_agent -c "DROP TABLE IF EXISTS _migrations CASCADE;"
	docker compose run --rm backend python run_migrations.py
	docker compose run --rm backend python seed.py

# ── Testing / Linting ─────────────────────────────────────────────────────────

test: ## Run all tests
	docker compose exec backend python -m pytest tests/ -v

test-coverage: ## Run tests with coverage report
	docker compose exec backend python -m pytest tests/ -v --cov=app --cov-report=term

lint: ## Run ruff linter
	docker compose exec backend ruff check app/ tests/

format: ## Auto-format with ruff
	docker compose exec backend ruff format app/ tests/

# ── Utilities ─────────────────────────────────────────────────────────────────

clean: ## Remove Python cache files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
