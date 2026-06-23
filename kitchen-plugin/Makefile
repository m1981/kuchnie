# Kitchen Plugin Makefile
# Usage: make help

BLENDER ?= /Applications/Blender.app/Contents/MacOS/Blender
PYTHON ?= .venv/bin/python
OUTPUT_DIR ?= output/meshes

.PHONY: help test generate generate-all validate open clean

help: ## Show available commands
	@echo ""
	@echo "Kitchen Plugin"
	@echo "=============="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""

test: ## Run all tests (no Blender required)
	$(PYTHON) -m pytest tests/ -q --tb=short

generate: ## Generate all reference kitchens with manifests
	@for config in configs/ref_*.json; do \
		name=$$(basename $$config .json); \
		echo ""; \
		echo "Generating $$name..."; \
		$(BLENDER) --background --python src/main.py -- $$config \
			--export-blend --validate --no-materials 2>&1 | \
			grep -E "(Generating|manifest|Objects:|Passed|Failed|Status:|Done)"; \
	done
	@echo ""
	@echo "Generated:"
	@ls -lh $(OUTPUT_DIR)/ref_*_manifest.json 2>/dev/null | awk '{print "  " $$NF " (" $$5 ")"}'
	@ls -lh $(OUTPUT_DIR)/ref_*.blend 2>/dev/null | awk '{print "  " $$NF " (" $$5 ")"}'

generate-single: ## Generate single cabinet test
	$(BLENDER) --background --python src/main.py -- configs/single_cabinet_test.json \
		--export-blend --validate --no-materials 2>&1 | \
		grep -E "(Generating|manifest|Objects:|Passed|Failed|Status:|Done)"

validate: ## Validate all manifests (no Blender required)
	@for manifest in $(OUTPUT_DIR)/ref_*_manifest.json; do \
		if [ -f "$$manifest" ]; then \
			echo ""; \
			python3 scripts/validate_manifest.py "$$manifest" 2>&1 | \
				grep -E "(Loading|Total|Passed|Failed|Status:|Errors|Warnings)"; \
		fi; \
	done

open: ## Open L-shape kitchen in Blender
	@if [ -f "$(OUTPUT_DIR)/ref_l_shape.blend" ]; then \
		open $(OUTPUT_DIR)/ref_l_shape.blend; \
	else \
		echo "Run 'make generate' first."; \
	fi

clean: ## Remove generated files
	rm -f $(OUTPUT_DIR)/*.blend $(OUTPUT_DIR)/*.obj $(OUTPUT_DIR)/*.gltf \
		$(OUTPUT_DIR)/*_manifest.json $(OUTPUT_DIR)/*_inspect.json
	@echo "Cleaned $(OUTPUT_DIR)/"
