.PHONY: help setup start stop restart logs clean extract index query interactive stats check api-test

help:
	@echo "Laravel RAG System - Make Commands"
	@echo ""
	@echo "Setup & Management:"
	@echo "  make setup       - Initial setup (Docker + pull models)"
	@echo "  make start       - Start all services"
	@echo "  make stop        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make logs        - View logs"
	@echo "  make clean       - Clean up (remove volumes and data)"
	@echo ""
	@echo "Documentation:"
	@echo "  make extract     - Extract Laravel docs from GitHub"
	@echo "  make index       - Index docs into vector store"
	@echo "  make reindex     - Force re-index documentation"
	@echo ""
	@echo "Querying:"
	@echo "  make query Q='your question'  - Query documentation"
	@echo "  make interactive              - Start interactive mode"
	@echo "  make stats                    - Show statistics"
	@echo "  make check                    - Check system status"
	@echo ""
	@echo "API:"
	@echo "  make api-test    - Test API endpoints"
	@echo ""

setup:
	@bash setup.sh

start:
	docker compose up -d
	@echo "Services started. Waiting for health check..."
	@sleep 5
	@echo "API available at: http://localhost:8000"

stop:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

clean:
	@echo "Warning: This will remove all data, including indexed documentation."
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose down -v; \
		rm -rf chromadb/ data/ sources/ logs/; \
		echo "Cleanup complete."; \
	fi

extract:
	docker compose exec rag-app python -m src.cli.main extract

index:
	docker compose exec rag-app python -m src.cli.main index

reindex:
	docker compose exec rag-app python -m src.cli.main index --force

query:
	@if [ -z "$(Q)" ]; then \
		echo "Usage: make query Q='your question'"; \
		exit 1; \
	fi
	docker compose exec rag-app python -m src.cli.main query "$(Q)" --show-sources

interactive:
	docker compose exec rag-app python -m src.cli.main interactive

stats:
	docker compose exec rag-app python -m src.cli.main stats

check:
	docker compose exec rag-app python -m src.cli.main check

api-test:
	@echo "Testing API endpoints..."
	@echo ""
	@echo "1. Health check:"
	@curl -s http://localhost:8000/health | python -m json.tool
	@echo ""
	@echo "2. Stats:"
	@curl -s http://localhost:8000/stats | python -m json.tool
	@echo ""
	@echo "3. Versions:"
	@curl -s http://localhost:8000/versions | python -m json.tool
	@echo ""
	@echo "4. Sample query:"
	@curl -s -X POST http://localhost:8000/query \
		-H "Content-Type: application/json" \
		-d '{"question": "How do I create a model?", "include_sources": true}' \
		| python -m json.tool

.DEFAULT_GOAL := help
