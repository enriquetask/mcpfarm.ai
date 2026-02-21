.PHONY: help dev docker-dev docker-down test lint type-check format install clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Install ──────────────────────────────────────────────────

install: ## Install all dependencies
	uv sync --all-packages
	cd frontend && pnpm install

# ── Development ──────────────────────────────────────────────

dev: ## Start gateway in development mode
	cd gateway && uv run uvicorn mcpfarm_gateway.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Start frontend in development mode
	cd frontend && pnpm dev

docker-dev: ## Start full stack with Docker Compose
	docker compose up --build -d

docker-down: ## Stop all Docker services
	docker compose down

docker-logs: ## Tail logs from all services
	docker compose logs -f

docker-rebuild: ## Rebuild and restart all services
	docker compose down && docker compose up --build -d

docker-observability: ## Start full stack + Prometheus + Grafana
	docker compose -f docker-compose.yml -f docker-compose.observability.yml up --build -d

grafana: ## Open Grafana dashboard (admin/mcpfarm)
	@echo "Grafana: http://localhost:3000 (admin/mcpfarm)"
	@open http://localhost:3000 2>/dev/null || true

# ── Quality ──────────────────────────────────────────────────

lint: ## Run linter
	uv run ruff check gateway/src sdk/src

format: ## Auto-format code
	uv run ruff format gateway/src sdk/src
	uv run ruff check --fix gateway/src sdk/src

type-check: ## Run type checker
	uv run mypy gateway/src sdk/src

# ── Testing ──────────────────────────────────────────────────

test: ## Run all Python tests
	uv run pytest

test-gateway: ## Run gateway tests only
	uv run pytest gateway/tests/

test-sdk: ## Run SDK tests only
	uv run pytest sdk/tests/

test-frontend: ## Run frontend tests
	cd frontend && pnpm test

# ── Database ─────────────────────────────────────────────────

db-migrate: ## Run database migrations
	cd gateway && uv run alembic upgrade head

db-revision: ## Create a new migration (usage: make db-revision msg="description")
	cd gateway && uv run alembic revision --autogenerate -m "$(msg)"

db-downgrade: ## Downgrade database by one revision
	cd gateway && uv run alembic downgrade -1

# ── Demo ─────────────────────────────────────────────────────

demo: ## Run LangGraph agent demo (usage: make demo query="Add 5 and 3")
	cd examples && uv run python langgraph_agent.py "$(query)"

# ── Cleanup ──────────────────────────────────────────────────

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/
