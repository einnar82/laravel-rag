# Deployment Guide

## Local Development Setup

### Prerequisites
- Docker Desktop for Mac (with M1 support)
- 16GB RAM minimum
- 10GB free disk space
- Git

### Quick Setup

1. **Initial setup**:
   ```bash
   make setup
   ```

2. **Extract and index documentation**:
   ```bash
   make extract
   make index
   ```

3. **Test the system**:
   ```bash
   make check
   make query Q="How do I create a migration?"
   ```

## Docker Deployment

### Resource Configuration

Edit `docker-compose.yml` to adjust resources:

```yaml
services:
  ollama:
    deploy:
      resources:
        limits:
          memory: 4G          # Adjust based on available RAM
        reservations:
          memory: 2G

  rag-app:
    deploy:
      resources:
        limits:
          memory: 2G          # Adjust based on needs
        reservations:
          memory: 1G
```

### Network Configuration

For production, use internal networks:

```yaml
networks:
  rag-network:
    driver: bridge
    internal: true          # Prevent external access

  api-network:
    driver: bridge          # Expose only API
```

### Volume Persistence

Ensure volumes are properly configured:

```yaml
volumes:
  ollama_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /path/to/persistent/ollama

  chromadb_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /path/to/persistent/chromadb
```

## Production Deployment

### 1. Environment Configuration

Create production `.env`:

```bash
# Ollama Configuration
OLLAMA_HOST=http://ollama:11434
LLM_MODEL=gemma:2b
EMBEDDING_MODEL=nomic-embed-text

# ChromaDB
CHROMA_PERSIST_DIR=/app/chromadb
CHROMA_COLLECTION_NAME=laravel_docs

# Laravel Documentation
LARAVEL_VERSION=12
DOCS_CACHE_DIR=/app/docs

# RAG Settings
TOP_K=5
RESPONSE_TIMEOUT=30

# Logging
LOG_LEVEL=INFO
LOG_FILE=/app/logs/laravel-rag.log

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4              # Increase for production
```

### 2. Security Hardening

#### API Authentication

Add to `src/api/main.py`:

```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

API_KEY = os.getenv("API_KEY", "your-secret-key")
api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# Apply to endpoints
@app.post("/query", dependencies=[Depends(verify_api_key)])
async def query_documentation(request: QueryRequest):
    ...
```

#### CORS Configuration

Update CORS settings:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific domains only
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

#### Rate Limiting

Install and configure:

```bash
pip install slowapi
```

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/query")
@limiter.limit("10/minute")
async def query_documentation(request: Request, data: QueryRequest):
    ...
```

### 3. Reverse Proxy Setup

#### Nginx Configuration

```nginx
upstream laravel_rag_api {
    server localhost:8000;
}

server {
    listen 80;
    server_name rag.yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name rag.yourdomain.com;

    ssl_certificate /etc/ssl/certs/your-cert.pem;
    ssl_certificate_key /etc/ssl/private/your-key.pem;

    location / {
        proxy_pass http://laravel_rag_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long-running queries
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://laravel_rag_api/health;
        access_log off;
    }
}
```

### 4. Monitoring Setup

#### Application Metrics

Add Prometheus metrics:

```python
from prometheus_fastapi_instrumentator import Instrumentator

# In main.py
@app.on_event("startup")
async def startup():
    Instrumentator().instrument(app).expose(app)
```

#### Docker Health Checks

Add to `docker-compose.yml`:

```yaml
services:
  rag-app:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

#### Log Aggregation

Configure centralized logging:

```yaml
services:
  rag-app:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        labels: "production,rag-app"
```

### 5. Backup Strategy

#### Automated Backups

Create backup script (`backup.sh`):

```bash
#!/bin/bash

BACKUP_DIR="/backups/laravel-rag"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Backup ChromaDB
docker-compose exec -T rag-app tar -czf - /app/chromadb \
  > "$BACKUP_DIR/chromadb_$TIMESTAMP.tar.gz"

# Backup configuration
cp .env "$BACKUP_DIR/env_$TIMESTAMP"
cp config/system.yaml "$BACKUP_DIR/system_$TIMESTAMP.yaml"

# Clean old backups (keep 7 days)
find "$BACKUP_DIR" -name "chromadb_*.tar.gz" -mtime +7 -delete

echo "Backup completed: $TIMESTAMP"
```

Add to crontab:
```bash
0 2 * * * /path/to/backup.sh
```

#### Restoration

```bash
# Stop services
docker-compose down

# Restore ChromaDB
tar -xzf chromadb_backup.tar.gz -C ./

# Restart
docker-compose up -d
```

## Scaling Strategies

### Horizontal Scaling

#### Multiple API Instances

Update `docker-compose.yml`:

```yaml
services:
  rag-app:
    deploy:
      replicas: 3
    ports:
      - "8000-8002:8000"
```

#### Load Balancer Configuration

Use HAProxy or Nginx:

```nginx
upstream rag_cluster {
    least_conn;
    server app1:8000;
    server app2:8000;
    server app3:8000;
}
```

### Vertical Scaling

Increase resources:

```yaml
services:
  ollama:
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4'
```

### Distributed ChromaDB

For large-scale deployments, use remote ChromaDB:

```python
# In src/indexing/vector_store.py
import chromadb
from chromadb.config import Settings

client = chromadb.HttpClient(
    host="chromadb-server",
    port=8000,
    settings=Settings(
        chroma_client_auth_provider="token",
        chroma_client_auth_credentials="your-token"
    )
)
```

## Performance Tuning

### Ollama Optimization

Adjust model parameters:

```bash
# In Ollama container
export OLLAMA_NUM_PARALLEL=4
export OLLAMA_MAX_LOADED_MODELS=2
```

### ChromaDB Optimization

Configure batch sizes:

```python
# In src/config.py
chunk_size: int = Field(default=2000, description="Larger chunks")
batch_size: int = Field(default=100, description="Larger batches")
```

### Caching

Implement query caching:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_query(question: str, version: str):
    return rag_chain.query(question, version_filter=version)
```

## Monitoring and Alerting

### Health Checks

Monitor critical endpoints:

```bash
# Add to monitoring system
curl -f http://localhost:8000/health || alert
```

### Metrics to Track

- Query response time
- Error rate
- Vector store size
- Memory usage
- API request rate

### Alerting Rules

Example Prometheus alerts:

```yaml
groups:
  - name: laravel_rag
    rules:
      - alert: HighResponseTime
        expr: query_duration_seconds > 5
        for: 5m
        annotations:
          summary: "High response time detected"

      - alert: HighErrorRate
        expr: rate(query_errors_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate detected"
```

## Disaster Recovery

### Recovery Plan

1. **Data Loss**:
   - Restore ChromaDB from backup
   - Re-index if necessary

2. **Service Failure**:
   - Restart containers: `docker-compose restart`
   - Check logs: `make logs`

3. **Complete Rebuild**:
   ```bash
   make clean
   make setup
   make extract
   make index
   ```

### Testing Recovery

Regularly test:
```bash
# Simulate failure
docker-compose down

# Restore from backup
./restore.sh

# Verify
make check
make query Q="test query"
```

## Cost Optimization

### Resource Efficiency

1. **Lazy Loading**: Load models on-demand
2. **Batch Processing**: Process queries in batches
3. **Compression**: Use compressed models
4. **Cleanup**: Regular cleanup of old data

### Infrastructure Costs

For cloud deployment:
- Use spot/preemptible instances
- Auto-scaling based on load
- S3/Cloud Storage for backups
- CDN for API responses

## Troubleshooting

### Common Issues

**High Memory Usage**:
```bash
# Check memory
docker stats

# Restart services
docker-compose restart
```

**Slow Queries**:
- Reduce `TOP_K`
- Optimize chunk size
- Add query caching

**Model Loading Errors**:
```bash
# Re-pull models
docker exec laravel-rag-ollama ollama pull gemma:2b
docker exec laravel-rag-ollama ollama pull nomic-embed-text
```

## Support and Maintenance

### Regular Maintenance

Weekly:
- Check logs for errors
- Monitor resource usage
- Test backup restoration

Monthly:
- Update dependencies
- Security patches
- Performance review

### Update Procedure

```bash
# Pull latest code
git pull

# Rebuild containers
docker-compose build --no-cache

# Restart services
docker-compose up -d

# Verify
make check
```
