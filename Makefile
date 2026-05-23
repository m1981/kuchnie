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
install: ## Install Synthadoc globally using uv tool
	uv tool install -e ~/synthadoc

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


##@ Danger Zone
.PHONY: reset-wiki
reset-wiki: ## ⚠️ DANGER: Delete the entire AI brain and start from scratch
	@echo "$(YELLOW)====================================================$(RESET)"
	@echo "$(YELLOW)⚠️ WARNING: This will delete all AI-generated pages!$(RESET)"
	@echo "$(YELLOW)Your original files will be safe, but the wiki will be wiped.$(RESET)"
	@echo "$(YELLOW)====================================================$(RESET)"
	@echo "Are you sure you want to rebuild from scratch? [y/N] " && read ans && [ $${ans:-N} = y ]
	$(MAKE) down
	@echo "$(BLUE)Waiting for server to release database locks...$(RESET)"
	sleep 2
	rm -rf .synthadoc wiki AGENTS.md log.md
	synthadoc uninstall temp-wiki
	@echo "$(BLUE)Re-initializing wiki...$(RESET)"
	synthadoc install temp-wiki --target . --domain "Projektowanie, sprzedaż i montaż mebli kuchennych. Standardy, materiały, ergonomia i instrukcje montażu."
	mv temp-wiki/.synthadoc ./
	mv temp-wiki/wiki ./
	mv temp-wiki/AGENTS.md ./
	mv temp-wiki/log.md ./ 2>/dev/null || true
	rm -rf temp-wiki
	synthadoc use .
	$(MAKE) up
	@echo "$(GREEN)Wiki reset successfully! Run 'make sync' to rebuild the brain.$(RESET)"