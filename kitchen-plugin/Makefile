# Kitchen Plugin Makefile
# Usage: make help

# Blender path (macOS default)
BLENDER ?= /Applications/Blender.app/Contents/MacOS/Blender

# Python (virtual env)
PYTHON ?= .venv/bin/python

# Config files
CONFIG_I ?= configs/ref_i_shape.json
CONFIG_L ?= configs/ref_l_shape.json
CONFIG_U ?= configs/ref_u_shape.json

# Output directory
OUTPUT_DIR ?= output/meshes

.PHONY: help test generate generate-all clean check-blender

help: ## Show this help message
	@echo ""
	@echo "Kitchen Plugin — Available Commands:"
	@echo "====================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Examples:"
	@echo "  make test                    Run all tests"
	@echo "  make generate                Generate U-shape kitchen"
	@echo "  make generate-all            Generate all reference kitchens"
	@echo "  make open                    Open U-shape in Blender"
	@echo ""

check-blender: ## Check if Blender is installed
	@if [ -f "$(BLENDER)" ]; then \
		echo "✅ Blender found at: $(BLENDER)"; \
		$(BLENDER) --version 2>/dev/null | head -1; \
	else \
		echo "❌ Blender not found at: $(BLENDER)"; \
		echo "   Install Blender or set BLENDER variable:" \
		echo "   make BLENDER=/path/to/blender generate"; \
		exit 1; \
	fi

test: ## Run all tests (no Blender required)
	$(PYTHON) -m pytest tests/ -v --tb=short

test-core: ## Run core geometry tests only
	$(PYTHON) -m pytest tests/test_core_geometry.py -v

test-kitchen: ## Run kitchen domain tests only
	$(PYTHON) -m pytest tests/test_kitchen.py -v

test-config: ## Run config parser tests only
	$(PYTHON) -m pytest tests/test_config_parser.py -v

test-fast: ## Run tests without verbose output
	$(PYTHON) -m pytest tests/ --tb=line -q

generate: check-blender ## Generate U-shape kitchen (default)
	@echo ""
	@echo "🏗️  Generating U-shape kitchen..."
	@mkdir -p $(OUTPUT_DIR)
	$(BLENDER) --background --python src/main.py -- $(CONFIG_U) --export-blend --export-obj
	@echo ""
	@echo "✅ Generated: $(OUTPUT_DIR)/ref_u_shape.blend"
	@echo "   Run 'make open' to view in Blender"

generate-i: check-blender ## Generate I-shape kitchen
	@echo ""
	@echo "🏗️  Generating I-shape kitchen..."
	@mkdir -p $(OUTPUT_DIR)
	$(BLENDER) --background --python src/main.py -- $(CONFIG_I) --export-blend --export-obj
	@echo ""
	@echo "✅ Generated: $(OUTPUT_DIR)/ref_i_shape.blend"

generate-l: check-blender ## Generate L-shape kitchen
	@echo ""
	@echo "🏗️  Generating L-shape kitchen..."
	@mkdir -p $(OUTPUT_DIR)
	$(BLENDER) --background --python src/main.py -- $(CONFIG_L) --export-blend --export-obj
	@echo ""
	@echo "✅ Generated: $(OUTPUT_DIR)/ref_l_shape.blend"

generate-all: generate-i generate-l generate ## Generate all reference kitchens
	@echo ""
	@echo "✅ All reference kitchens generated!"
	@ls -lh $(OUTPUT_DIR)/ref_*.blend

open: ## Open U-shape kitchen in Blender
	@if [ -f "$(OUTPUT_DIR)/ref_u_shape.blend" ]; then \
		open $(OUTPUT_DIR)/ref_u_shape.blend; \
	else \
		echo "❌ File not found. Run 'make generate' first."; \
	fi

open-i: ## Open I-shape kitchen in Blender
	@if [ -f "$(OUTPUT_DIR)/ref_i_shape.blend" ]; then \
		open $(OUTPUT_DIR)/ref_i_shape.blend; \
	else \
		echo "❌ File not found. Run 'make generate-i' first."; \
	fi

open-l: ## Open L-shape kitchen in Blender
	@if [ -f "$(OUTPUT_DIR)/ref_l_shape.blend" ]; then \
		open $(OUTPUT_DIR)/ref_l_shape.blend; \
	else \
		echo "❌ File not found. Run 'make generate-l' first."; \
	fi

validate: ## Validate all reference configs
	@echo "📋 Validating configs..."
	$(PYTHON) -c "\
	from src.config_parser import load_config; \
	from src.validators import validate_config; \
	configs = ['$(CONFIG_I)', '$(CONFIG_L)', '$(CONFIG_U)']; \
	[print(f'  ✅ {c}') if not validate_config(load_config(c)) else None for c in configs]; \
	"

clean: ## Remove generated files
	@echo "🧹 Cleaning output directory..."
	rm -rf $(OUTPUT_DIR)/*.blend $(OUTPUT_DIR)/*.obj
	@echo "✅ Cleaned"

info: ## Show project info
	@echo ""
	@echo "Kitchen Plugin — Project Info"
	@echo "============================="
	@echo ""
	@echo "Python: $(PYTHON)"
	@echo "Blender: $(BLENDER)"
	@echo "Output: $(OUTPUT_DIR)"
	@echo ""
	@echo "Tests:"
	@$(PYTHON) -m pytest tests/ --tb=line -q 2>/dev/null | tail -1
	@echo ""
	@echo "Configs:"
	@for f in configs/ref_*.json; do \
		echo "  - $$f"; \
	done
	@echo ""
