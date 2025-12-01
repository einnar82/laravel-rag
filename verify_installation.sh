#!/bin/bash

# Laravel RAG System - Installation Verification Script
# This script verifies that all components are properly set up

set -e

echo "========================================"
echo "Laravel RAG System Verification"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
PASSED=0
FAILED=0

# Helper function for checks
check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $1"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ FAIL${NC}: $1"
        FAILED=$((FAILED + 1))
    fi
}

echo -e "${BLUE}1. Checking File Structure${NC}"
echo "----------------------------------------"

# Check core directories
test -d src/extraction && check "src/extraction directory exists" || check "src/extraction directory exists"
test -d src/indexing && check "src/indexing directory exists" || check "src/indexing directory exists"
test -d src/retrieval && check "src/retrieval directory exists" || check "src/retrieval directory exists"
test -d src/api && check "src/api directory exists" || check "src/api directory exists"
test -d src/cli && check "src/cli directory exists" || check "src/cli directory exists"
test -d tests && check "tests directory exists" || check "tests directory exists"

# Check core files
test -f docker-compose.yml && check "docker-compose.yml exists" || check "docker-compose.yml exists"
test -f Dockerfile && check "Dockerfile exists" || check "Dockerfile exists"
test -f requirements.txt && check "requirements.txt exists" || check "requirements.txt exists"
test -f Makefile && check "Makefile exists" || check "Makefile exists"
test -f .env.example && check ".env.example exists" || check ".env.example exists"
test -f setup.sh && check "setup.sh exists" || check "setup.sh exists"
test -f verify_installation.sh && check "verify_installation.sh exists" || check "verify_installation.sh exists"

# Check documentation
test -f README.md && check "README.md exists" || check "README.md exists"
test -f QUICKSTART.md && check "QUICKSTART.md exists" || check "QUICKSTART.md exists"
test -f API.md && check "API.md exists" || check "API.md exists"
test -f DEPLOYMENT.md && check "DEPLOYMENT.md exists" || check "DEPLOYMENT.md exists"
test -f ARCHITECTURE.md && check "ARCHITECTURE.md exists" || check "ARCHITECTURE.md exists"

echo ""
echo -e "${BLUE}2. Checking Python Files${NC}"
echo "----------------------------------------"

# Check main application files
test -f src/config.py && check "src/config.py exists" || check "src/config.py exists"
test -f src/extraction/docs_fetcher.py && check "docs_fetcher.py exists" || check "docs_fetcher.py exists"
test -f src/extraction/markdown_parser.py && check "markdown_parser.py exists" || check "markdown_parser.py exists"
test -f src/indexing/embeddings.py && check "embeddings.py exists" || check "embeddings.py exists"
test -f src/indexing/vector_store.py && check "vector_store.py exists" || check "vector_store.py exists"
test -f src/indexing/validator.py && check "validator.py exists" || check "validator.py exists"
test -f src/retrieval/rag_chain.py && check "rag_chain.py exists" || check "rag_chain.py exists"
test -f src/api/main.py && check "api/main.py exists" || check "api/main.py exists"
test -f src/cli/main.py && check "cli/main.py exists" || check "cli/main.py exists"
test -f src/utils/cache.py && check "cache.py exists" || check "cache.py exists"
test -f src/utils/logger.py && check "logger.py exists" || check "logger.py exists"

echo ""
echo -e "${BLUE}3. Checking Dependencies${NC}"
echo "----------------------------------------"

# Check if requirements.txt has key dependencies
grep -q "langchain" requirements.txt && check "langchain in requirements" || check "langchain in requirements"
grep -q "chromadb" requirements.txt && check "chromadb in requirements" || check "chromadb in requirements"
grep -q "ollama" requirements.txt && check "ollama in requirements" || check "ollama in requirements"
grep -q "fastapi" requirements.txt && check "fastapi in requirements" || check "fastapi in requirements"
grep -q "click" requirements.txt && check "click in requirements" || check "click in requirements"

echo ""
echo -e "${BLUE}4. Checking Docker Configuration${NC}"
echo "----------------------------------------"

# Check docker-compose services
grep -q "ollama:" docker-compose.yml && check "Ollama service defined" || check "Ollama service defined"
grep -q "rag-app:" docker-compose.yml && check "RAG app service defined" || check "RAG app service defined"
grep -q "platform: linux/arm64" docker-compose.yml && check "M1 Mac platform configured" || check "M1 Mac platform configured"

# Check volumes
grep -q "ollama_data:" docker-compose.yml && check "Ollama volume defined" || check "Ollama volume defined"
grep -q "chromadb_data:" docker-compose.yml && check "ChromaDB volume defined" || check "ChromaDB volume defined"

echo ""
echo -e "${BLUE}5. Checking Configuration Files${NC}"
echo "----------------------------------------"

# Check .env.example
grep -q "OLLAMA_HOST" .env.example && check "OLLAMA_HOST in .env.example" || check "OLLAMA_HOST in .env.example"
grep -q "LLM_MODEL" .env.example && check "LLM_MODEL in .env.example" || check "LLM_MODEL in .env.example"
grep -q "EMBEDDING_MODEL" .env.example && check "EMBEDDING_MODEL in .env.example" || check "EMBEDDING_MODEL in .env.example"
grep -q "LARAVEL_VERSION" .env.example && check "LARAVEL_VERSION in .env.example" || check "LARAVEL_VERSION in .env.example"

# Check system.yaml
test -f config/system.yaml && check "config/system.yaml exists" || check "config/system.yaml exists"
grep -q "min_similarity_threshold" config/system.yaml && check "min_similarity_threshold in system.yaml" || check "min_similarity_threshold in system.yaml"
grep -q "cache" config/system.yaml && check "cache configuration in system.yaml" || check "cache configuration in system.yaml"
grep -q "hnsw" config/system.yaml && check "HNSW configuration in system.yaml" || check "HNSW configuration in system.yaml"

echo ""
echo -e "${BLUE}6. Checking Documentation Quality${NC}"
echo "----------------------------------------"

# Check README completeness
grep -q "Quick Start" README.md && check "README has Quick Start section" || check "README has Quick Start section"
grep -q "Installation" README.md && check "README has Installation section" || check "README has Installation section"
grep -q "Usage" README.md && check "README has Usage section" || check "README has Usage section"

# Check API documentation
grep -q "POST /query" documentation/API.md && check "API docs have /query endpoint" || check "API docs have /query endpoint"
grep -q "GET /search" documentation/API.md && check "API docs have /search endpoint" || check "API docs have /search endpoint"
grep -q "GET /validate-index" documentation/API.md && check "API docs have /validate-index endpoint" || check "API docs have /validate-index endpoint"
grep -q "GET /cache-stats" documentation/API.md && check "API docs have /cache-stats endpoint" || check "API docs have /cache-stats endpoint"

echo ""
echo -e "${BLUE}7. Checking Scripts${NC}"
echo "----------------------------------------"

test -x setup.sh && check "setup.sh is executable" || check "setup.sh is executable"
test -f Makefile && check "Makefile exists" || check "Makefile exists"

# Check Makefile targets
grep -q "^setup:" Makefile && check "Makefile has setup target" || check "Makefile has setup target"
grep -q "^extract:" Makefile && check "Makefile has extract target" || check "Makefile has extract target"
grep -q "^index:" Makefile && check "Makefile has index target" || check "Makefile has index target"
grep -q "^query:" Makefile && check "Makefile has query target" || check "Makefile has query target"
grep -q "^validate:" Makefile && check "Makefile has validate target" || check "Makefile has validate target"

echo ""
echo -e "${BLUE}8. Checking Tests${NC}"
echo "----------------------------------------"

test -f tests/test_extraction.py && check "test_extraction.py exists" || check "test_extraction.py exists"
test -f tests/test_api.py && check "test_api.py exists" || check "test_api.py exists"
test -f tests/conftest.py && check "conftest.py exists" || check "conftest.py exists"

echo ""
echo "========================================"
echo -e "${BLUE}Verification Summary${NC}"
echo "========================================"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All checks passed! ✓${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Run: make setup"
    echo "2. Run: make extract"
    echo "3. Run: make index"
    echo "4. Run: make query Q='How do I create a model?'"
    echo ""
    exit 0
else
    echo -e "${RED}Some checks failed. Please review the output above.${NC}"
    echo ""
    exit 1
fi
