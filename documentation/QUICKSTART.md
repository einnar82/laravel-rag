# Quick Start Guide

Get up and running with Laravel RAG in 10 minutes.

## Prerequisites

- Docker Desktop (with M1 Mac support if on Apple Silicon)
- 16GB RAM minimum
- 10GB free disk space

## Installation Steps

### 1. Setup System (5 minutes)

```bash
cd /Users/rannieollit/Desktop/WebeeLabs/laravel-rag

# Run automated setup
make setup
```

This will:
- Start Docker containers
- Pull Ollama models (gemma:2b and nomic-embed-text)
- Initialize the system

Expected output:
```
✓ Docker is running
✓ Created .env file
✓ Directories created
✓ Ollama is ready
✓ Embedding model downloaded
✓ LLM model downloaded
Setup Complete!
```

### 2. Extract Documentation (1 minute)

```bash
make extract
```

Downloads Laravel v12 documentation from GitHub.

### 3. Index Documentation (3-5 minutes)

```bash
make index
```

Generates embeddings and stores in ChromaDB. This is a one-time operation per version.

### 4. Test the System (30 seconds)

```bash
make check
```

Verifies all components are working:
```
✓ Embedding model (nomic-embed-text) is available
✓ LLM model (gemma:2b) is available
✓ Vector store has 150 documents
✓ Documentation found: 98 files
```

## Basic Usage

### Query via CLI

```bash
make query Q="How do I create a migration?"
```

### Interactive Mode

```bash
make interactive
```

Then ask questions:
```
Question: How do I create a model?
Answer: To create an Eloquent model in Laravel...

Question: What is middleware?
Answer: Middleware provides a convenient mechanism...

Question: exit
```

### Using the API

The API runs automatically at http://localhost:8000

```bash
# Query endpoint
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I use migrations?"}'

# Search endpoint
curl "http://localhost:8000/search?q=eloquent&top_k=3"

# Stats
curl http://localhost:8000/stats
```

### API Documentation

Visit http://localhost:8000/docs for interactive API documentation.

## Common Commands

```bash
# Start services
make start

# Stop services
make stop

# View logs
make logs

# Get statistics
make stats

# Test API
make api-test
```

## Example Queries

Try these to get started:

1. **Creating Models**:
   ```bash
   make query Q="How do I create an Eloquent model?"
   ```

2. **Migrations**:
   ```bash
   make query Q="How do I create and run migrations?"
   ```

3. **Relationships**:
   ```bash
   make query Q="How do I define relationships in Eloquent?"
   ```

4. **Middleware**:
   ```bash
   make query Q="What is middleware and how do I use it?"
   ```

5. **Routing**:
   ```bash
   make query Q="How do I define routes in Laravel?"
   ```

## Troubleshooting

### Models Not Found

```bash
# Check Ollama
docker exec laravel-rag-ollama ollama list

# Pull models manually if needed
docker exec laravel-rag-ollama ollama pull gemma:2b
docker exec laravel-rag-ollama ollama pull nomic-embed-text
```

### Services Not Starting

```bash
# Check Docker
docker ps

# Restart services
make restart

# View logs
make logs
```

### No Documentation Found

```bash
# Re-extract
make extract

# Re-index
make reindex
```

### Out of Memory

- Restart Docker Desktop
- Increase Docker memory limit in preferences
- Close other applications

## Next Steps

1. **Explore the API**: Visit http://localhost:8000/docs
2. **Read Full Documentation**: See README.md
3. **Configure Settings**: Edit .env file
4. **Add More Versions**: See DEPLOYMENT.md

## Support

- Full documentation: README.md
- API reference: API.md
- Deployment guide: DEPLOYMENT.md
- Project instructions: claude.md

## Cleanup

To remove all data and start fresh:

```bash
make clean
```

Warning: This removes all indexed data. You'll need to run `make extract` and `make index` again.
