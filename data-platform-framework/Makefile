# Data Platform Framework - Makefile
# UV-based development workflows and automation
# All commands use UV as the package manager

.PHONY: help install install-dev test lint format type-check security build clean docs pre-commit setup-dev

# Default target
help:
	@echo "🏗️  Data Platform Framework - Development Commands"
	@echo "=================================================="
	@echo ""
	@echo "📦 Installation:"
	@echo "  make install      Install production dependencies"
	@echo "  make install-dev  Install development dependencies"
	@echo "  make setup-dev    Complete development environment setup"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test         Run test suite"
	@echo "  make test-cov     Run tests with coverage report"
	@echo "  make test-watch   Run tests in watch mode"
	@echo ""
	@echo "🔍 Code Quality:"
	@echo "  make lint         Run all linters with ruff"
	@echo "  make format       Format code with ruff"
	@echo "  make type-check   Run mypy type checking"
	@echo "  make security     Run security scans"
	@echo ""
	@echo "🚀 Development:"
	@echo "  make docs         Build documentation"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  make clean        Clean build artifacts"
	@echo "  make pre-commit   Run pre-commit on all files"

# Installation targets
install:
	@echo "📦 Installing production dependencies with UV..."
	uv sync --no-dev

install-dev:
	@echo "📦 Installing development dependencies with UV..."
	uv sync --extra dev --extra testing --extra async

setup-dev: install-dev
	@echo "🔧 Setting up development environment..."
	uv run pre-commit install
	uv run pre-commit install --hook-type pre-push --config .pre-push-config.yaml
	@echo "✅ Development environment ready!"

# Testing targets
test:
	@echo "🧪 Running test suite..."
	uv run pytest tests/ -v

test-cov:
	@echo "🧪 Running tests with coverage..."
	uv run pytest tests/ --cov=data_platform_framework --cov-report=term-missing --cov-report=html

test-watch:
	@echo "🧪 Running tests in watch mode..."
	uv run pytest-watch tests/ -v

# Code quality targets
lint:
	@echo "🔍 Running ruff linter..."
	uv run ruff check data_platform_framework/ tests/ scripts/

format:
	@echo "🎨 Formatting code with ruff..."
	uv run ruff format data_platform_framework/ tests/ scripts/
	uv run ruff check --fix data_platform_framework/ tests/ scripts/

type-check:
	@echo "🔍 Running type checks..."
	uv run mypy data_platform_framework/

security:
	@echo "🔒 Running security scans..."
	uv run bandit -r data_platform_framework/ -f json
	uv run safety check

# Build targets (commented out - not publishing packages)
# build:
# 	@echo "🚀 Building package..."
# 	uv build

docs:
	@echo "📚 Building documentation..."
	@if [ -f mkdocs.yml ]; then \
		uv run mkdocs build; \
	else \
		echo "No mkdocs.yml found - skipping docs build"; \
	fi

# Maintenance targets
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

pre-commit:
	@echo "🔧 Running pre-commit on all files..."
	pre-commit run --all-files

# CI/CD targets (for automated environments)
ci-install:
	@echo "📦 CI: Installing dependencies..."
	uv sync --extra dev --extra testing

ci-test:
	@echo "🧪 CI: Running full test suite..."
	uv run pytest tests/ --cov=data_platform_framework --cov-report=xml --cov-fail-under=80

ci-lint:
	@echo "🔍 CI: Running all quality checks..."
	uv run ruff check data_platform_framework/ tests/
	uv run ruff format --check data_platform_framework/ tests/
	uv run mypy data_platform_framework/
	uv run bandit -r data_platform_framework/

ci-security:
	@echo "🔒 CI: Running security checks..."
	uv run safety check --json

# Development shortcuts
dev-check: format lint type-check test
	@echo "✅ All development checks passed!"

quick-test:
	@echo "⚡ Running quick tests..."
	uv run pytest tests/unit/ -v
