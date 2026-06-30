# Catalog Makefile — Material catalog API
# Usage: make help
# Run from: catalog/ dir

BLUE := \033[36m
YELLOW := \033[33m
GREEN := \033[32m
RESET := \033[0m

.DEFAULT_GOAL := help

##@ General
.PHONY: help
help: ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\n$(BLUE)Catalog API$(RESET)\n\n  make $(YELLOW)<target>$(RESET)\n"} \
		/^[a-zA-Z0-9_-]+:.*?##/ { printf "  $(YELLOW)%-20s$(RESET) %s\n", $$1, $$2 } \
		/^##@/ { printf "\n$(GREEN)%s$(RESET)\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ Development
.PHONY: dev
dev: ## Start FastAPI dev server (uvicorn --reload)
	cd .. && .venv/bin/uvicorn catalog.api.main:app --reload --port 8000

.PHONY: seed
seed: ## Seed database from YAML files
	cd .. && .venv/bin/python -m catalog.scripts.seed catalog/data/kronospan_full.yaml catalog/data/kronoswiss_full.yaml

##@ Testing
.PHONY: test
test: ## Run pytest (API + schema tests)
	cd .. && .venv/bin/python -m pytest catalog/tests/test_catalog_api.py -v

.PHONY: test-all
test-all: ## Run all tests
	cd .. && .venv/bin/python -m pytest catalog/tests/ -v

##@ Production
.PHONY: prod
prod: ## Start production server
	cd .. && .venv/bin/uvicorn catalog.api.main:app --port 8000

##@ Maintenance
.PHONY: clean
clean: ## Remove generated files
	rm -f db/catalog.db db/catalog.db-shm db/catalog.db-wal
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	@echo "$(GREEN)Cleaned$(RESET)"
