# Colors for help system
BLUE := \033[36m
YELLOW := \033[33m
GREEN := \033[32m
RESET := \033[0m

BLENDER := /Applications/Blender.app/Contents/MacOS/Blender

.DEFAULT_GOAL := help

##@ General
.PHONY: help
help: ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\n$(BLUE)Usage:$(RESET)\n  make $(YELLOW)<target>$(RESET)\n"} \
		/^[a-zA-Z0-9_-]+:.*?##/ { printf "  $(YELLOW)%-20s$(RESET) %s\n", $$1, $$2 } \
		/^##@/ { printf "\n$(GREEN)%s$(RESET)\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ Development
.PHONY: run
run: ## Start the FastAPI server (http://localhost:8000)
	@echo "$(GREEN)Starting server...$(RESET)"
	uv run python main.py

.PHONY: lint
lint: ## Run type checker (mypy)
	@echo "$(GREEN)Running mypy...$(RESET)"
	uv run mypy src/

##@ Testing
.PHONY: test
test: ## Run all tests
	@echo "$(GREEN)Running all tests...$(RESET)"
	uv run pytest -v

.PHONY: test-unit
test-unit: ## Run unit tests only (infrastructure + application)
	@echo "$(GREEN)Running unit tests...$(RESET)"
	uv run pytest -v tests/infrastructure/ tests/application/

.PHONY: test-integration
test-integration: ## Run integration tests
	@echo "$(GREEN)Running integration tests...$(RESET)"
	uv run pytest -v tests/integration/

.PHONY: test-perf
test-perf: ## Run performance tests (4K benchmark)
	@echo "$(GREEN)Running performance tests...$(RESET)"
	uv run pytest -v tests/performance/ -s

.PHONY: test-cov
test-cov: ## Run tests with coverage (fail under 80%)
	@echo "$(GREEN)Running tests with coverage...$(RESET)"
	uv run pytest --cov=src --cov-report=term-missing

##@ Assets
.PHONY: render
render: ## Regenerate scene assets with Blender
	@echo "$(GREEN)Rendering scene assets...$(RESET)"
	$(BLENDER) -b -P gen_kitchen.py

##@ Cleanup
.PHONY: clean
clean: ## Remove Python caches and build artifacts
	@echo "$(GREEN)Cleaning caches...$(RESET)"
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Done.$(RESET)"
