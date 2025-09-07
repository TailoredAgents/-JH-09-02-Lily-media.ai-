# Makefile for AI Social Media Content Agent
# Provides common development and deployment tasks

.PHONY: help setup clean test lint format build run docker dev prod install-deps update-deps security-check docs

# Variables
PYTHON := python3.11
PIP := pip
NODE := node
NPM := npm
DOCKER := docker
DOCKER_COMPOSE := docker-compose

# Python paths
BACKEND_DIR := backend
FRONTEND_DIR := frontend
VENV_DIR := venv
REQUIREMENTS := requirements.txt

# Default target
help:
	@echo "🚀 AI Social Media Content Agent - Development Commands"
	@echo "========================================================="
	@echo ""
	@echo "🔧 Setup & Installation:"
	@echo "  make setup          - Complete project setup (backend + frontend)"
	@echo "  make install-deps   - Install all dependencies"
	@echo "  make update-deps    - Update all dependencies"
	@echo "  make clean          - Clean build artifacts and caches"
	@echo ""
	@echo "💻 Development:"
	@echo "  make dev            - Start development servers (backend + frontend)"
	@echo "  make dev-backend    - Start backend development server only"
	@echo "  make dev-frontend   - Start frontend development server only"
	@echo "  make dev-workers    - Start Celery workers for background tasks"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test           - Run all tests"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo "  make test-watch     - Run tests in watch mode"
	@echo ""
	@echo "✨ Code Quality:"
	@echo "  make lint           - Run all linters"
	@echo "  make lint-backend   - Run Python linters"
	@echo "  make lint-frontend  - Run JavaScript/React linters"
	@echo "  make format         - Format all code"
	@echo "  make format-backend - Format Python code"
	@echo "  make format-frontend - Format JavaScript/React code"
	@echo ""
	@echo "🔒 Security:"
	@echo "  make security-check - Run security vulnerability scans"
	@echo "  make security-backend - Run Python security scans"
	@echo "  make security-frontend - Run Node.js security scans"
	@echo "  make generate-sbom  - Generate Software Bill of Materials"
	@echo "  make validate-security - Validate all security controls"
	@echo ""
	@echo "🗄️ Database Migration Guardrails:"
	@echo "  make migration-status - Check migration and rollback status"
	@echo "  make migration-dry-run - Test migration without changes"
	@echo "  make migration-safe - Run safe migration with backups"
	@echo "  make migration-list-backups - List available backups"
	@echo "  make migration-validate-rollback MIGRATION_ID=<id> - Validate rollback"
	@echo "  make migration-emergency-rollback MIGRATION_ID=<id> - Emergency rollback"
	@echo ""
	@echo "🐳 Docker:"
	@echo "  make docker-build   - Build Docker images"
	@echo "  make docker-up      - Start services with Docker Compose"
	@echo "  make docker-down    - Stop Docker services"
	@echo "  make docker-logs    - View Docker logs"
	@echo ""
	@echo "🚀 Production:"
	@echo "  make build          - Build production artifacts"
	@echo "  make prod           - Start production servers"
	@echo "  make deploy-staging - Deploy to staging environment"
	@echo "  make deploy-prod    - Deploy to production environment"
	@echo ""
	@echo "📚 Documentation:"
	@echo "  make docs           - Build documentation"
	@echo "  make docs-serve     - Serve documentation locally"
	@echo ""

# Setup & Installation
setup: clean install-deps setup-git-hooks
	@echo "✅ Project setup completed!"

install-deps: install-backend-deps install-frontend-deps
	@echo "✅ All dependencies installed!"

install-backend-deps:
	@echo "📦 Installing Python dependencies..."
	@$(PYTHON) -m venv $(VENV_DIR)
	@$(VENV_DIR)/bin/pip install --upgrade pip
	@$(VENV_DIR)/bin/pip install -r $(REQUIREMENTS)
	@$(VENV_DIR)/bin/pip install -e ".[dev]"

install-frontend-deps:
	@echo "📦 Installing Node.js dependencies..."
	@cd $(FRONTEND_DIR) && $(NPM) ci

update-deps:
	@echo "🔄 Updating dependencies..."
	@$(VENV_DIR)/bin/pip install --upgrade pip
	@$(VENV_DIR)/bin/pip-review --local --interactive
	@cd $(FRONTEND_DIR) && $(NPM) update

setup-git-hooks:
	@echo "🪝 Setting up Git hooks..."
	@$(VENV_DIR)/bin/pre-commit install
	@$(VENV_DIR)/bin/pre-commit install --hook-type commit-msg

# Development
dev:
	@echo "🚀 Starting development environment..."
	@$(MAKE) -j3 dev-backend dev-frontend dev-workers

dev-backend:
	@echo "🐍 Starting backend development server..."
	@cd $(BACKEND_DIR) && ../$(VENV_DIR)/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	@echo "⚛️ Starting frontend development server..."
	@cd $(FRONTEND_DIR) && $(NPM) run dev

dev-workers:
	@echo "👷 Starting Celery workers..."
	@cd $(BACKEND_DIR) && ../$(VENV_DIR)/bin/celery -A tasks.celery_app worker --loglevel=info

# Testing
test: test-backend test-frontend
	@echo "✅ All tests completed!"

test-backend:
	@echo "🧪 Running backend tests..."
	@cd $(BACKEND_DIR) && ../$(VENV_DIR)/bin/pytest

test-frontend:
	@echo "🧪 Running frontend tests..."
	@cd $(FRONTEND_DIR) && $(NPM) test

test-unit:
	@echo "🧪 Running unit tests..."
	@cd $(BACKEND_DIR) && ../$(VENV_DIR)/bin/pytest tests/unit/ -v
	@cd $(FRONTEND_DIR) && $(NPM) run test:unit

test-integration:
	@echo "🧪 Running integration tests..."
	@cd $(BACKEND_DIR) && ../$(VENV_DIR)/bin/pytest tests/integration/ -v
	@cd $(FRONTEND_DIR) && $(NPM) run test:integration

test-coverage:
	@echo "📊 Running tests with coverage..."
	@cd $(BACKEND_DIR) && ../$(VENV_DIR)/bin/pytest --cov=$(BACKEND_DIR) --cov-report=html --cov-report=term-missing
	@cd $(FRONTEND_DIR) && $(NPM) run test:coverage

test-watch:
	@echo "👀 Running tests in watch mode..."
	@cd $(BACKEND_DIR) && ../$(VENV_DIR)/bin/pytest-watch

# Code Quality
lint: lint-backend lint-frontend
	@echo "✅ All linting completed!"

lint-backend:
	@echo "🔍 Running Python linters..."
	@$(VENV_DIR)/bin/black --check $(BACKEND_DIR)/
	@$(VENV_DIR)/bin/isort --check-only $(BACKEND_DIR)/
	@$(VENV_DIR)/bin/flake8 $(BACKEND_DIR)/
	@$(VENV_DIR)/bin/mypy $(BACKEND_DIR)/ --ignore-missing-imports

lint-frontend:
	@echo "🔍 Running JavaScript/React linters..."
	@cd $(FRONTEND_DIR) && $(NPM) run lint

format: format-backend format-frontend
	@echo "✨ All code formatted!"

format-backend:
	@echo "✨ Formatting Python code..."
	@$(VENV_DIR)/bin/black $(BACKEND_DIR)/
	@$(VENV_DIR)/bin/isort $(BACKEND_DIR)/

format-frontend:
	@echo "✨ Formatting JavaScript/React code..."
	@cd $(FRONTEND_DIR) && $(NPM) run format

# Security
security-check: security-backend security-frontend
	@echo "🔒 Security scans completed!"

security-backend:
	@echo "🔒 Running Python security scans..."
	@$(VENV_DIR)/bin/safety check
	@$(VENV_DIR)/bin/bandit -r $(BACKEND_DIR)/ -ll

security-frontend:
	@echo "🔒 Running Node.js security scans..."
	@cd $(FRONTEND_DIR) && $(NPM) audit --audit-level=moderate

# Docker
docker-build:
	@echo "🐳 Building Docker images..."
	@$(DOCKER_COMPOSE) build

docker-up:
	@echo "🐳 Starting Docker services..."
	@$(DOCKER_COMPOSE) up -d

docker-down:
	@echo "🐳 Stopping Docker services..."
	@$(DOCKER_COMPOSE) down

docker-logs:
	@echo "📜 Viewing Docker logs..."
	@$(DOCKER_COMPOSE) logs -f

# Production
build: build-backend build-frontend
	@echo "🏗️ Production build completed!"

build-backend:
	@echo "🏗️ Building backend for production..."
	@$(VENV_DIR)/bin/python -m build

build-frontend:
	@echo "🏗️ Building frontend for production..."
	@cd $(FRONTEND_DIR) && $(NPM) run build

prod:
	@echo "🚀 Starting production servers..."
	@$(MAKE) -j2 prod-backend prod-frontend

prod-backend:
	@echo "🐍 Starting production backend..."
	@cd $(BACKEND_DIR) && ../$(VENV_DIR)/bin/gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

prod-frontend:
	@echo "⚛️ Serving production frontend..."
	@cd $(FRONTEND_DIR) && $(NPM) run preview

deploy-staging:
	@echo "🚀 Deploying to staging..."
	@gh workflow run deploy.yml -f environment=staging

deploy-prod:
	@echo "🚀 Deploying to production..."
	@gh workflow run deploy.yml -f environment=production

# Documentation
docs:
	@echo "📚 Building documentation..."
	@cd $(BACKEND_DIR) && ../$(VENV_DIR)/bin/python -c "from main import app; import json; print(json.dumps(app.openapi(), indent=2))" > ../docs/openapi.json

docs-serve:
	@echo "📚 Serving documentation..."
	@cd docs && python -m http.server 8080

# Database
db-migrate:
	@echo "🗃️ Running database migrations..."
	@cd $(BACKEND_DIR) && ../$(VENV_DIR)/bin/alembic upgrade head

db-rollback:
	@echo "🗃️ Rolling back database migration..."
	@cd $(BACKEND_DIR) && ../$(VENV_DIR)/bin/alembic downgrade -1

db-reset:
	@echo "🗃️ Resetting database..."
	@cd $(BACKEND_DIR) && ../$(VENV_DIR)/bin/python setup_database.py

# Utility
clean:
	@echo "🧹 Cleaning build artifacts..."
	@rm -rf $(VENV_DIR)
	@rm -rf $(BACKEND_DIR)/__pycache__
	@rm -rf $(BACKEND_DIR)/.pytest_cache
	@rm -rf $(FRONTEND_DIR)/node_modules
	@rm -rf $(FRONTEND_DIR)/dist
	@rm -rf $(FRONTEND_DIR)/build
	@rm -rf .coverage
	@rm -rf htmlcov
	@rm -rf dist
	@rm -rf build
	@rm -rf *.egg-info
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete

install-tools:
	@echo "🔧 Installing development tools..."
	@$(VENV_DIR)/bin/pip install pre-commit black isort flake8 mypy bandit safety
	@$(NPM) install -g prettier eslint

check-env:
	@echo "🔍 Checking environment..."
	@echo "Python: $(shell $(PYTHON) --version)"
	@echo "Node: $(shell $(NODE) --version)"
	@echo "NPM: $(shell $(NPM) --version)"
	@echo "Docker: $(shell $(DOCKER) --version)"
	@echo "Virtual Environment: $(VENV_DIR)"

health-check:
	@echo "🏥 Running health checks..."
	@curl -f http://localhost:8000/health || echo "❌ Backend health check failed"
	@curl -f http://localhost:3000 || echo "❌ Frontend health check failed"
	@echo "✅ Health checks completed"

logs:
	@echo "📜 Viewing application logs..."
	@tail -f $(BACKEND_DIR)/logs/*.log

# Performance
benchmark:
	@echo "⚡ Running performance benchmarks..."
	@cd $(BACKEND_DIR) && ../$(VENV_DIR)/bin/pytest tests/performance/ --benchmark-only

profile:
	@echo "📊 Running performance profiling..."
	@cd $(BACKEND_DIR) && ../$(VENV_DIR)/bin/python -m cProfile main.py

# Database Migration Guardrails
migration-status:
	@echo "🔍 Checking migration status..."
	@if [ -z "$(DATABASE_URL)" ]; then \
		echo "❌ DATABASE_URL environment variable not set"; \
		exit 1; \
	fi
	python scripts/migration-rollback.py --database-url "$(DATABASE_URL)" --status

migration-dry-run:
	@echo "🔍 Running migration dry run..."
	@if [ -z "$(DATABASE_URL)" ]; then \
		echo "❌ DATABASE_URL environment variable not set"; \
		exit 1; \
	fi
	python scripts/migration-guardrails.py --database-url "$(DATABASE_URL)" --dry-run

migration-safe:
	@echo "⚡ Running safe migration with guardrails..."
	@if [ -z "$(DATABASE_URL)" ]; then \
		echo "❌ DATABASE_URL environment variable not set"; \
		exit 1; \
	fi
	python scripts/migration-guardrails.py --database-url "$(DATABASE_URL)"

migration-rollback-status:
	@echo "🔄 Checking rollback status..."
	@if [ -z "$(DATABASE_URL)" ]; then \
		echo "❌ DATABASE_URL environment variable not set"; \
		exit 1; \
	fi
	python scripts/migration-rollback.py --database-url "$(DATABASE_URL)" --status

migration-list-backups:
	@echo "📁 Listing available migration backups..."
	@if [ -z "$(DATABASE_URL)" ]; then \
		echo "❌ DATABASE_URL environment variable not set"; \
		exit 1; \
	fi
	python scripts/migration-rollback.py --database-url "$(DATABASE_URL)" --list

migration-validate-rollback:
	@echo "🔍 Validating rollback point: $(MIGRATION_ID)"
	@if [ -z "$(DATABASE_URL)" ]; then \
		echo "❌ DATABASE_URL environment variable not set"; \
		exit 1; \
	fi
	@if [ -z "$(MIGRATION_ID)" ]; then \
		echo "❌ MIGRATION_ID environment variable not set"; \
		echo "Usage: make migration-validate-rollback MIGRATION_ID=migration_20250906_123456"; \
		exit 1; \
	fi
	python scripts/migration-rollback.py --database-url "$(DATABASE_URL)" --validate "$(MIGRATION_ID)"

migration-emergency-rollback:
	@echo "🚨 EMERGENCY ROLLBACK - This is destructive!"
	@echo "⚠️  This will restore the database to: $(MIGRATION_ID)"
	@echo "⚠️  Recent data may be lost!"
	@if [ -z "$(DATABASE_URL)" ]; then \
		echo "❌ DATABASE_URL environment variable not set"; \
		exit 1; \
	fi
	@if [ -z "$(MIGRATION_ID)" ]; then \
		echo "❌ MIGRATION_ID environment variable not set"; \
		echo "Usage: make migration-emergency-rollback MIGRATION_ID=migration_20250906_123456"; \
		exit 1; \
	fi
	@echo "Type 'yes' to confirm emergency rollback:"
	@read confirm && [ "$$confirm" = "yes" ] || (echo "❌ Rollback cancelled" && exit 1)
	python scripts/migration-rollback.py --database-url "$(DATABASE_URL)" --rollback "$(MIGRATION_ID)" --confirm

generate-sbom:
	@echo "📦 Generating Software Bill of Materials (SBOM)..."
	python scripts/generate-sbom.py --project-root . --output-dir sbom

validate-security:
	@echo "🔒 Running security validation..."
	python scripts/validate-security.py --project-root .

# CI/CD
ci-setup:
	@echo "🔧 Setting up CI/CD environment..."
	@$(MAKE) install-deps
	@$(MAKE) setup-git-hooks

ci-test:
	@echo "🧪 Running CI tests..."
	@$(MAKE) lint
	@$(MAKE) security-check
	@$(MAKE) test

ci-build:
	@echo "🏗️ Running CI build..."
	@$(MAKE) build
	@$(MAKE) docker-build