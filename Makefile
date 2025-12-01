.PHONY: help quickstart docker-start docker-stop docker-logs clean
.PHONY: extract index validate query stats check disk-usage
.PHONY: local-extract local-index local-query local-stats local-check local-validate
.PHONY: analyze-chunks compare-chunks

help:
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║          Laravel RAG System - Make Commands               ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  make quickstart              Complete setup: extract + index docs"
	@echo ""
	@echo "📦 Docker Commands:"
	@echo "  make docker-start            Start all services"
	@echo "  make docker-stop             Stop all services"
	@echo "  make docker-logs             View container logs"
	@echo ""
	@echo "📚 Documentation Workflow:"
	@echo "  make extract                 Extract Laravel docs from GitHub"
	@echo "  make index                   Index docs into vector store"
	@echo "  make validate                Validate index health and quality"
	@echo "  make query Q='...'           Query documentation"
	@echo "  make stats                   Show database statistics"
	@echo "  make check                   Check system status"
	@echo ""
	@echo "💻 Local Development (no Docker):"
	@echo "  make local-extract           Extract docs locally"
	@echo "  make local-index             Index docs locally"
	@echo "  make local-query Q='...'     Query locally"
	@echo "  make local-stats             Show stats locally"
	@echo "  make local-check             Check status locally"
	@echo ""
	@echo "🛠️  Utilities:"
	@echo "  make disk-usage              Show disk usage by folder"
	@echo "  make analyze-chunks          Analyze chunking strategy"
	@echo "  make compare-chunks          Compare anchor vs adaptive strategies"
	@echo "  make clean                   Remove all data (models, db, cache)"
	@echo ""

# ============================================================================
# Quick Start - Complete Workflow
# ============================================================================

quickstart:
	@echo "🚀 Starting Laravel RAG System..."
	@echo ""
	@echo "Step 1/5: Creating directories..."
	@mkdir -p models chromadb sources logs data
	@echo "✓ Directories created"
	@echo ""
	@echo "Step 2/5: Starting Docker services..."
	@docker compose up -d
	@echo "✓ Services started"
	@echo ""
	@echo "Step 3/5: Waiting for services to be ready..."
	@sleep 10
	@echo "✓ Services ready"
	@echo ""
	@echo "Step 4/5: Extracting Laravel v12 documentation..."
	@docker compose exec -T rag-app python -m src.cli.main extract --version 12
	@echo "✓ Documentation extracted"
	@echo ""
	@echo "Step 5/5: Indexing documentation (this may take a few minutes)..."
	@docker compose exec -T rag-app python -m src.cli.main index --version 12
	@echo "✓ Documentation indexed"
	@echo ""
	@echo "Step 6/6: Validating index..."
	@docker compose exec -T rag-app python -m src.cli.main validate --version 12 || true
	@echo "✓ Validation complete"
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ✅ Setup Complete! Your RAG system is ready to use       ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Try a query:"
	@echo "  make query Q='How do I create an Eloquent model?'"
	@echo ""
	@echo "View statistics:"
	@echo "  make stats"
	@echo ""
	@echo "Validate index:"
	@echo "  make validate"
	@echo ""

# ============================================================================
# Docker Management
# ============================================================================

docker-start:
	@echo "Starting Docker services..."
	@mkdir -p models chromadb sources logs data
	@docker compose up -d
	@echo "✓ Services started"
	@echo ""
	@echo "API available at: http://localhost:8000"
	@echo "Ollama available at: http://localhost:11434"

docker-stop:
	@echo "Stopping Docker services..."
	@docker compose down
	@echo "✓ Services stopped"

docker-logs:
	@docker compose logs -f

# ============================================================================
# Documentation Workflow (Docker)
# ============================================================================

extract:
	@echo "Extracting Laravel documentation..."
	@docker compose exec rag-app python -m src.cli.main extract --version 12
	@echo "✓ Extraction complete"

index: ## Index documentation with concurrent processing
	@echo "Indexing documentation into vector store (concurrent processing enabled)..."
	@docker compose exec rag-app python -m src.cli.main index --version 12
	@echo "✓ Indexing complete"

query:
	@if [ -z "$(Q)" ]; then \
		echo "Usage: make query Q='your question'"; \
		echo "Example: make query Q='How do I create a model?'"; \
		exit 1; \
	fi
	@docker compose exec rag-app python -m src.cli.main query "$(Q)" --show-sources

stats:
	@docker compose exec rag-app python -m src.cli.main stats

check:
	@docker compose exec rag-app python -m src.cli.main check

validate:
	@docker compose exec rag-app python -m src.cli.main validate

queue-status: ## Check Redis queue status
	@docker compose exec rag-app python -m src.cli.main queue-status

queue-clear-failed: ## Clear failed jobs from queue
	@docker compose exec rag-app python -m src.cli.main queue-clear --clear-failed

queue-clear-finished: ## Clear finished jobs from queue
	@docker compose exec rag-app python -m src.cli.main queue-clear --clear-finished

# ============================================================================
# Local Development (No Docker)
# ============================================================================

local-extract:
	@if [ ! -d ".venv" ]; then \
		echo "Virtual environment not found. Creating..."; \
		python3 -m venv .venv; \
		. .venv/bin/activate && pip install -q -r requirements.txt; \
	fi
	@echo "Extracting Laravel documentation..."
	@. .venv/bin/activate && python -m src.cli.main extract --version 12
	@echo "✓ Extraction complete"

local-index:
	@if [ ! -d ".venv" ]; then \
		echo "Virtual environment not found. Run 'make local-extract' first."; \
		exit 1; \
	fi
	@echo "Indexing documentation into vector store..."
	@. .venv/bin/activate && python -m src.cli.main index --version 12
	@echo "✓ Indexing complete"

local-query:
	@if [ -z "$(Q)" ]; then \
		echo "Usage: make local-query Q='your question'"; \
		echo "Example: make local-query Q='How do I create a model?'"; \
		exit 1; \
	fi
	@. .venv/bin/activate && python -m src.cli.main query "$(Q)" --show-sources

local-stats:
	@. .venv/bin/activate && python -m src.cli.main stats

local-check:
	@. .venv/bin/activate && python -m src.cli.main check

local-validate:
	@. .venv/bin/activate && python -m src.cli.main validate

# ============================================================================
# Utilities
# ============================================================================

disk-usage:
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║              Disk Usage by Folder                          ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@printf "%-15s %s\n" "Folder" "Size"
	@printf "%-15s %s\n" "──────" "────"
	@du -sh models 2>/dev/null | awk '{printf "%-15s %s\n", "models/", $$1}' || printf "%-15s %s\n" "models/" "0"
	@du -sh chromadb 2>/dev/null | awk '{printf "%-15s %s\n", "chromadb/", $$1}' || printf "%-15s %s\n" "chromadb/" "0"
	@du -sh sources 2>/dev/null | awk '{printf "%-15s %s\n", "sources/", $$1}' || printf "%-15s %s\n" "sources/" "0"
	@du -sh logs 2>/dev/null | awk '{printf "%-15s %s\n", "logs/", $$1}' || printf "%-15s %s\n" "logs/" "0"
	@du -sh data 2>/dev/null | awk '{printf "%-15s %s\n", "data/", $$1}' || printf "%-15s %s\n" "data/" "0"
	@echo ""
	@printf "%-15s %s\n" "Total:" "$$(du -sh . 2>/dev/null | awk '{print $$1}')"

analyze-chunks:
	@if [ ! -d ".venv" ]; then \
		echo "Virtual environment not found. Creating..."; \
		python3 -m venv .venv; \
		. .venv/bin/activate && pip install -q -r requirements.txt; \
	fi
	@echo "Analyzing chunking strategy..."
	@. .venv/bin/activate && python analyze_chunks.py $(if $(STRATEGY),--strategy $(STRATEGY),) $(if $(MAX),--max-chunk-size $(MAX),) $(if $(MIN),--min-chunk-size $(MIN),) $(if $(OVERLAP),--chunk-overlap $(OVERLAP),)

compare-chunks:
	@if [ ! -d ".venv" ]; then \
		echo "Virtual environment not found. Creating..."; \
		python3 -m venv .venv; \
		. .venv/bin/activate && pip install -q -r requirements.txt; \
	fi
	@echo "Comparing chunking strategies..."
	@. .venv/bin/activate && python analyze_chunks.py --strategy compare

clean:
	@echo "⚠️  Warning: This will remove all data, including:"
	@echo "  - Ollama models (~2.5 GB)"
	@echo "  - Vector database"
	@echo "  - Documentation cache"
	@echo "  - Logs"
	@echo ""
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "Stopping containers..."; \
		docker compose down; \
		echo "Removing data directories..."; \
		rm -rf chromadb/ data/ sources/ logs/ models/; \
		echo "✓ Cleanup complete"; \
	else \
		echo "Cancelled."; \
	fi

.DEFAULT_GOAL := help
