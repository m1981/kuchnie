# Automatically load environment variables from .env file (if it exists)
-include .env
export

# Colors for help system
BLUE := \033[36m
YELLOW := \033[33m
GREEN := \033[32m
RESET := \033[0m

.DEFAULT_GOAL := help

##@ General
.PHONY: help
help: ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\n$(BLUE)Usage:$(RESET)\n  make $(YELLOW)<target>$(RESET)\n"} \
		/^[a-zA-Z0-9_-]+:.*?##/ { printf "  $(YELLOW)%-20s$(RESET) %s\n", $$1, $$2 } \
		/^##@/ { printf "\n$(GREEN)%s$(RESET)\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ Setup & Server
.PHONY: install
install: ## Install Synthadoc using uv (run once)
	uv venv
	uv pip install -e ~/synthadoc

.PHONY: up
up: ## Start the Synthadoc background server
	@if [ -z "$$GEMINI_API_KEY" ]; then \
		echo "$(YELLOW)Warning: GEMINI_API_KEY is not set. Please create a .env file!$(RESET)"; \
	fi
	synthadoc serve --background

.PHONY: down
down: ## Stop the background server
	@if [ -f .synthadoc/server.pid ]; then \
		kill $$(cat .synthadoc/server.pid) && echo "$(GREEN)Server stopped.$(RESET)"; \
	else \
		echo "$(YELLOW)Server is not running.$(RESET)"; \
	fi

.PHONY: logs
logs: ## Watch the live server logs (Press Ctrl+C to exit)
	tail -f .synthadoc/logs/synthadoc.log

##@ Knowledge Base
.PHONY: sync-dry
sync-dry: ## Dry-run: see what files WOULD be ingested
	./sync.sh -d

.PHONY: sync
sync: ## Run the sync script to ingest new files
	./sync.sh

.PHONY: status
status: ## Check the status of ingestion jobs
	synthadoc jobs list

.PHONY: maintain
maintain: ## Run linter (check contradictions) and rebuild index
	synthadoc lint run
	synthadoc scaffold