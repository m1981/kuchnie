# Catalog Makefile — Material catalog browser
# Usage: make help
# Run from: project root (cd .. && make -C catalog) or catalog/ dir

BLUE := \033[36m
YELLOW := \033[33m
GREEN := \033[32m
RESET := \033[0m

# Paths relative to catalog/ (parent = project root)
ROOT := ..
DATA := $(ROOT)/data/materials
DIST := $(ROOT)/data/dist

.DEFAULT_GOAL := help

##@ General
.PHONY: help
help: ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\n$(BLUE)Catalog$(RESET)\n\n  make $(YELLOW)<target>$(RESET)\n"} \
		/^[a-zA-Z0-9_-]+:.*?##/ { printf "  $(YELLOW)%-20s$(RESET) %s\n", $$1, $$2 } \
		/^##@/ { printf "\n$(GREEN)%s$(RESET)\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ Development
.PHONY: dev
dev: ## Start dev server (watch YAML + rebuild + Vite HMR)
	node dev.js

.PHONY: build
build: ## Build catalog.json from YAML sources
	cd $(ROOT) && NODE_PATH=$(CURDIR)/node_modules node data/materials/build.js

.PHONY: test
test: ## Run validation tests (55 checks)
	cd $(ROOT) && NODE_PATH=$(CURDIR)/node_modules node --test data/materials/tests/validate.test.js

.PHONY: validate
validate: build test ## Build + test (full validation)

##@ Production
.PHONY: prod
prod: ## Build production bundle
	cd $(ROOT) && NODE_PATH=$(CURDIR)/node_modules node data/materials/build.js
	cd $(ROOT) && npx vite build --config catalog/vite.config.mjs

.PHONY: preview
preview: ## Preview production build locally
	cd $(ROOT) && npx vite preview --config catalog/vite.config.mjs

##@ Maintenance
.PHONY: clean
clean: ## Remove generated files
	rm -rf $(DIST)/*.json dist public/catalog.json
	@echo "$(GREEN)Cleaned$(RESET)"
