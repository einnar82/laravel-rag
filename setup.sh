#!/bin/bash

# Laravel RAG System Setup Script
# This script initializes the system and downloads required models

set -e

echo "========================================"
echo "Laravel RAG System Setup"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker is running${NC}"

# Check if .env exists, if not create from .env.example
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env file${NC}"
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi

# Create necessary directories
echo ""
echo "Creating necessary directories..."
mkdir -p data chromadb sources logs
echo -e "${GREEN}✓ Directories created${NC}"

# Start Docker services
echo ""
echo "Starting Docker services..."
docker compose up -d

# Wait for Ollama to be ready
echo ""
echo "Waiting for Ollama to be ready..."
sleep 10

max_retries=30
retry_count=0
while ! docker exec laravel-rag-ollama ollama list > /dev/null 2>&1; do
    retry_count=$((retry_count + 1))
    if [ $retry_count -ge $max_retries ]; then
        echo -e "${RED}Error: Ollama failed to start after ${max_retries} attempts${NC}"
        exit 1
    fi
    echo "Waiting for Ollama... (attempt $retry_count/$max_retries)"
    sleep 2
done

echo -e "${GREEN}✓ Ollama is ready${NC}"

# Pull required models
echo ""
echo "Pulling required Ollama models..."
echo "This may take several minutes depending on your internet connection."
echo ""

# Pull embedding model
echo -e "${YELLOW}Pulling nomic-embed-text (embedding model)...${NC}"
docker exec laravel-rag-ollama ollama pull nomic-embed-text
echo -e "${GREEN}✓ Embedding model downloaded${NC}"

# Pull LLM model
echo -e "${YELLOW}Pulling gemma:2b (LLM model)...${NC}"
docker exec laravel-rag-ollama ollama pull gemma:2b
echo -e "${GREEN}✓ LLM model downloaded${NC}"

# Check system status
echo ""
echo "Checking system status..."
docker compose exec rag-app python -m src.cli.main check

echo ""
echo "========================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Extract Laravel documentation:"
echo "   docker compose exec rag-app python -m src.cli.main extract"
echo ""
echo "2. Index the documentation:"
echo "   docker compose exec rag-app python -m src.cli.main index"
echo "   (This will automatically validate the index after indexing)"
echo ""
echo "3. Validate the index (optional):"
echo "   docker compose exec rag-app python -m src.cli.main validate"
echo ""
echo "4. Query the documentation:"
echo "   docker compose exec rag-app python -m src.cli.main query \"How do I create a model?\" --show-sources"
echo ""
echo "5. Query with verification:"
echo "   docker compose exec rag-app python -m src.cli.main query \"How do I create a model?\" --min-similarity 0.6"
echo ""
echo "6. Or use interactive mode:"
echo "   docker compose exec rag-app python -m src.cli.main interactive"
echo ""
echo "7. API is available at: http://localhost:8000"
echo "   API docs: http://localhost:8000/docs"
echo ""
echo "New Features:"
echo "- Answer verification: All answers are verified against retrieved context"
echo "- Similarity filtering: Only answers above similarity threshold"
echo "- Index validation: Validate index quality and completeness"
echo "- Caching: Embeddings and retrieval results are cached for better performance"
echo ""
