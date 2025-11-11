# Troubleshooting Guide

## Common Issues and Solutions

### Ollama Embedding Warnings

**Symptom:**
```
init: embeddings required but some input tokens were not marked as outputs -> overriding
```

**Explanation:**
This warning appears when generating embeddings with Ollama's nomic-embed-text model. It's an internal message from the model's token handling layer (GGML/llama.cpp) indicating that it's automatically adjusting the output token configuration.

**Status:** **Harmless - Can be safely ignored**

This warning does not affect:
- ✅ Embedding generation quality
- ✅ Vector similarity calculations
- ✅ RAG query accuracy
- ✅ System performance

**Why it happens:**
The nomic-embed-text model's configuration expects certain input/output token mappings, and Ollama automatically corrects any mismatches when generating embeddings. The "overriding" part means Ollama is fixing the issue automatically.

**To minimize warnings (optional):**
These warnings come from the C++ layer and cannot be completely suppressed without rebuilding Ollama. However, you can redirect stderr if desired:

```bash
# When running Docker Compose, redirect stderr
docker compose up -d 2>/dev/null

# Or filter logs when viewing
docker logs laravel-rag-app 2>&1 | grep -v "init: embeddings"
```

---

## Other Common Issues

### ChromaDB SQLite Version Error

**Symptom:**
```
RuntimeError: Your system has an unsupported version of sqlite3. Chroma requires sqlite3 >= 3.35.0.
```

**Solution:**
This should be fixed in the current Docker setup. We use `python:3.11-slim-bookworm` which includes SQLite 3.40.1.

If you encounter this:
1. Ensure you're using the latest Docker image: `docker compose build --no-cache`
2. Verify SQLite version: `docker exec laravel-rag-app python -c "import sqlite3; print(sqlite3.sqlite_version)"`

---

### ChromaDB Telemetry Errors

**Symptom:**
```
Failed to send telemetry event ClientStartEvent: capture() takes 1 positional argument but 3 were given
```

**Solution:**
This has been fixed with the chromadb_fix module. If you still see these:
1. Ensure the fix module exists: `src/utils/chromadb_fix.py`
2. Restart containers: `docker compose restart`

---

### Model Not Available

**Symptom:**
```
WARNING | Model gemma:2b not found. Available: []
```

**Solution:**
The LLM or embedding models haven't been pulled yet. Run:

```bash
# Pull both models
docker exec laravel-rag-ollama ollama pull gemma:2b
docker exec laravel-rag-ollama ollama pull nomic-embed-text

# Or use the setup script
./setup.sh
```

---

### Container Unhealthy

**Symptom:**
```
laravel-rag-ollama   Up 3 minutes (unhealthy)
```

**Solution:**
This was an issue with the healthcheck command using `curl` which wasn't available. Fixed by using `ollama list` instead.

If you still see this:
1. Check container logs: `docker logs laravel-rag-ollama`
2. Verify Ollama is responding: `curl http://localhost:11434/api/tags`
3. Restart: `docker compose restart ollama`

---

### Dependency Conflicts

**Symptom:**
```
ERROR: Cannot install httpx==0.26.0 because ollama 0.1.6 depends on httpx<0.26.0
```

**Solution:**
This has been fixed in requirements.txt with proper version constraints:
```
httpx>=0.25.2,<0.26.0
```

If you encounter new conflicts:
1. Check requirements.txt for version pins
2. Rebuild: `docker compose build --no-cache`

---

## Getting Help

If you encounter issues not covered here:

1. **Check logs:**
   ```bash
   docker logs laravel-rag-app
   docker logs laravel-rag-ollama
   ```

2. **Verify system status:**
   ```bash
   docker compose exec rag-app python -m src.cli.main check
   ```

3. **Review configuration:**
   ```bash
   cat .env
   docker exec laravel-rag-app python -c "from src.config import settings; print(settings)"
   ```

4. **Clean restart:**
   ```bash
   docker compose down
   docker compose build --no-cache
   docker compose up -d
   ```

5. **Check GitHub issues:** [Laravel RAG Issues](https://github.com/yourusername/laravel-rag/issues)
