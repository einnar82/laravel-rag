# API Documentation

## Base URL

```
http://localhost:8000
```

## Authentication

Currently no authentication required for local development. For production, implement API key authentication (see DEPLOYMENT.md).

## Interactive API Documentation

FastAPI provides automatic interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Endpoints

### 1. Health Check

Check service health and configuration.

**Endpoint**: `GET /health`

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "ollama_host": "http://ollama:11434",
  "llm_model": "gemma:2b",
  "embedding_model": "nomic-embed-text",
  "vector_store_documents": 150
}
```

**Example**:
```bash
curl http://localhost:8000/health
```

---

### 2. Query Documentation

Query Laravel documentation with LLM-generated response.

**Endpoint**: `POST /query`

**Request Body**:
```json
{
  "question": "How do I create an Eloquent model?",
  "version": "12",                    // Optional: filter by version
  "top_k": 5,                        // Optional: number of results
  "temperature": 0.7,                // Optional: LLM temperature
  "include_sources": true,           // Optional: include source docs
  "min_similarity": 0.5,             // Optional: minimum similarity threshold (0.0-1.0)
  "verify_answer": true              // Optional: verify answer against context (default: true)
}
```

**Response**:
```json
{
  "question": "How do I create an Eloquent model?",
  "answer": "To create an Eloquent model in Laravel, you can use the `php artisan make:model` command...",
  "version_filter": "12",
  "verified": true,
  "verification_status": "verified",
  "similarity_scores": [0.856, 0.823, 0.801, 0.789, 0.765],
  "cache_hit": false,
  "sources": [
    {
      "file": "eloquent.md",
      "section": "Defining Models",
      "version": "12",
      "anchor": "eloquent.md#defining-models",
      "heading_path": "Eloquent ORM > Defining Models",
      "distance": 0.144,
      "similarity": 0.856
    }
  ]
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How do I create a migration?",
    "include_sources": true,
    "temperature": 0.7
  }'
```

**Parameters**:
- `question` (required): The question to ask
- `version` (optional): Filter results by Laravel version
- `top_k` (optional, default: 5): Number of relevant sections to retrieve (1-20)
- `temperature` (optional, default: 0.7): LLM sampling temperature (0.0-1.0)
- `include_sources` (optional, default: false): Include source documents in response
- `min_similarity` (optional, default: 0.5): Minimum similarity threshold (0.0-1.0). Only results above this threshold will be used
- `verify_answer` (optional, default: true): Whether to verify the answer is supported by retrieved context

**Response Fields**:
- `verified` (boolean): Whether the answer was verified against context
- `verification_status` (string): Status of verification ("verified", "unverified", "insufficient_context", "verification_failed")
- `similarity_scores` (array): Similarity scores for retrieved documents
- `cache_hit` (boolean): Whether the result was served from cache

**Status Codes**:
- `200 OK`: Successful query
- `400 Bad Request`: Invalid request parameters
- `500 Internal Server Error`: Query processing failed

---

### 3. Search Documentation

Search documentation without LLM generation (retrieval only).

**Endpoint**: `GET /search`

**Query Parameters**:
- `q` (required): Search query
- `version` (optional): Filter by Laravel version
- `top_k` (optional, default: 5): Number of results to return (1-20)

**Response**:
```json
{
  "query": "eloquent relationships",
  "results": [
    {
      "file": "eloquent-relationships.md",
      "section": "Defining Relationships",
      "version": "12",
      "anchor": "eloquent-relationships.md#defining-relationships",
      "heading_path": "Eloquent: Relationships > Defining Relationships",
      "content": "## Defining Relationships\n\nEloquent relationships are defined as methods...",
      "distance": 0.187
    }
  ],
  "count": 5
}
```

**Example**:
```bash
curl "http://localhost:8000/search?q=eloquent%20relationships&top_k=3"
```

**Status Codes**:
- `200 OK`: Successful search
- `400 Bad Request`: Missing or invalid query parameter
- `500 Internal Server Error`: Search failed

---

### 4. Get Statistics

Retrieve vector store statistics.

**Endpoint**: `GET /stats`

**Response**:
```json
{
  "total_documents": 150,
  "versions": {
    "12": 150
  },
  "collection_name": "laravel_docs",
  "persist_dir": "/app/chromadb",
  "cache_stats": {
    "embedding": {
      "size": 45,
      "max_size": 1000,
      "hits": 234,
      "misses": 45,
      "hit_rate": 83.87,
      "ttl": 3600
    },
    "retrieval": {
      "size": 123,
      "max_size": 1000,
      "hits": 567,
      "misses": 123,
      "hit_rate": 82.17,
      "ttl": 3600
    }
  }
}
```

**Example**:
```bash
curl http://localhost:8000/stats
```

**Status Codes**:
- `200 OK`: Statistics retrieved successfully
- `500 Internal Server Error`: Failed to retrieve statistics

---

### 5. Get Versions

List available Laravel versions in the vector store.

**Endpoint**: `GET /versions`

**Response**:
```json
{
  "versions": [
    {
      "version": "12",
      "document_count": 150
    },
    {
      "version": "11",
      "document_count": 142
    }
  ],
  "total_versions": 2
}
```

**Example**:
```bash
curl http://localhost:8000/versions
```

**Status Codes**:
- `200 OK`: Versions retrieved successfully
- `500 Internal Server Error`: Failed to retrieve versions

---

### 6. Validate Index

Validate index health and quality.

**Endpoint**: `GET /validate-index`

**Query Parameters**:
- `version` (optional): Validate specific version

**Response**:
```json
{
  "status": "healthy",
  "score": 95,
  "total_documents": 150,
  "version_distribution": {
    "12": 150
  },
  "issues": [],
  "validation": {
    "valid": true,
    "issue_count": 0,
    "stats": {
      "total_documents": 150,
      "duplicates": 0,
      "missing_metadata": 0,
      "empty_chunks": 0,
      "invalid_embeddings": 0
    }
  }
}
```

**Example**:
```bash
curl "http://localhost:8000/validate-index?version=12"
```

**Status Codes**:
- `200 OK`: Validation completed successfully
- `500 Internal Server Error`: Validation failed

**Health Status Values**:
- `healthy`: Score >= 80, no critical issues
- `degraded`: Score 50-79, some issues found
- `unhealthy`: Score < 50, critical issues found

---

### 7. Get Cache Statistics

Get cache statistics for embeddings and retrieval results.

**Endpoint**: `GET /cache-stats`

**Response**:
```json
{
  "embedding": {
    "size": 45,
    "max_size": 1000,
    "hits": 234,
    "misses": 45,
    "hit_rate": 83.87,
    "ttl": 3600
  },
  "retrieval": {
    "size": 123,
    "max_size": 1000,
    "hits": 567,
    "misses": 123,
    "hit_rate": 82.17,
    "ttl": 3600
  }
}
```

**Example**:
```bash
curl http://localhost:8000/cache-stats
```

**Status Codes**:
- `200 OK`: Cache statistics retrieved successfully
- `500 Internal Server Error`: Failed to retrieve cache statistics

**Cache Statistics Fields**:
- `size`: Current number of cached items
- `max_size`: Maximum cache size
- `hits`: Number of cache hits
- `misses`: Number of cache misses
- `hit_rate`: Cache hit rate percentage
- `ttl`: Time to live in seconds

---

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common Error Codes**:
- `400 Bad Request`: Invalid input parameters
- `403 Forbidden`: Authentication failed (if enabled)
- `404 Not Found`: Endpoint not found
- `422 Unprocessable Entity`: Validation error
- `429 Too Many Requests`: Rate limit exceeded (if enabled)
- `500 Internal Server Error`: Server-side error
- `503 Service Unavailable`: Service unhealthy

---

## Rate Limiting

Currently disabled for local development. For production deployment, configure rate limiting:

```python
# Default limits (when enabled)
- 60 requests per minute per IP
- 1000 requests per hour per IP
```

Rate limit headers in response:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1609459200
```

---

## Best Practices

### Optimal Query Formation

1. **Be Specific**: "How do I create a migration for adding a column?" vs "migrations"
2. **Use Laravel Terminology**: Use Laravel-specific terms (Eloquent, Artisan, Blade)
3. **Version Specificity**: Specify version if querying version-specific features

### Temperature Settings

- `0.0-0.3`: Factual, deterministic answers (recommended for documentation)
- `0.4-0.7`: Balanced creativity and accuracy (default)
- `0.8-1.0`: More creative, less predictable

### Top-K Selection

- `1-3`: Very specific queries, need exact match
- `4-6`: Standard queries (default: 5)
- `7-10`: Broad queries, need comprehensive context
- `11+`: Research queries, exploring multiple aspects

### Similarity Threshold

- `0.0-0.3`: Very permissive, may include less relevant results
- `0.4-0.6`: Balanced (default: 0.5), good for most queries
- `0.7-0.9`: Strict, only highly relevant results
- `0.9+`: Very strict, only near-exact matches

### Answer Verification

- `verify_answer: true` (default): Verifies answer is supported by context, prevents hallucination
- `verify_answer: false`: Skips verification for faster responses (not recommended)

### Performance Optimization

1. **Batch Queries**: Group related questions
2. **Cache Results**: Embeddings and retrieval results are automatically cached
3. **Use Search First**: Use `/search` for exploratory queries, `/query` for answers
4. **Version Filtering**: Filter by version when possible
5. **Similarity Threshold**: Adjust `min_similarity` to balance relevance vs. coverage
6. **Monitor Cache**: Check `/cache-stats` to monitor cache performance

---

## Code Examples

### Python

```python
import requests

# Query documentation
response = requests.post(
    "http://localhost:8000/query",
    json={
        "question": "How do I use middleware?",
        "include_sources": True,
        "temperature": 0.7
    }
)

result = response.json()
print(result["answer"])

# Search documentation
response = requests.get(
    "http://localhost:8000/search",
    params={"q": "middleware", "top_k": 3}
)

results = response.json()
for doc in results["results"]:
    print(f"{doc['file']} - {doc['section']}")
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

// Query documentation
async function queryDocs(question) {
  const response = await axios.post('http://localhost:8000/query', {
    question: question,
    include_sources: true,
    temperature: 0.7
  });

  return response.data;
}

// Search documentation
async function searchDocs(query, topK = 5) {
  const response = await axios.get('http://localhost:8000/search', {
    params: { q: query, top_k: topK }
  });

  return response.data;
}

// Usage
queryDocs("How do I create a controller?")
  .then(result => console.log(result.answer))
  .catch(error => console.error(error));
```

### cURL

```bash
# Query with all options including verification
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How do I use Eloquent relationships?",
    "version": "12",
    "top_k": 5,
    "temperature": 0.7,
    "include_sources": true,
    "min_similarity": 0.6,
    "verify_answer": true
  }' | jq

# Validate index
curl "http://localhost:8000/validate-index?version=12" | jq

# Get cache statistics
curl http://localhost:8000/cache-stats | jq

# Search
curl "http://localhost:8000/search?q=validation&top_k=3" | jq

# Get stats
curl http://localhost:8000/stats | jq

# Health check
curl http://localhost:8000/health | jq
```

---

## WebSocket Support (Future)

WebSocket support for streaming responses is planned for future releases:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/query');

ws.send(JSON.stringify({
  question: "Explain Laravel middleware",
  stream: true
}));

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.chunk);  // Streaming response
};
```

---

## Monitoring and Analytics

### Request Logging

All requests are logged with:
- Timestamp
- Endpoint
- Query parameters
- Response time
- Status code

### Metrics Endpoint (Future)

```
GET /metrics
```

Prometheus-compatible metrics:
- Request count by endpoint
- Response time percentiles
- Error rate
- Vector store size
- Active queries

---

## Testing

### Health Check Test

```bash
# Should return status 200
curl -I http://localhost:8000/health
```

### Query Test

```bash
# Should return answer about models
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I create a model?"}' \
  | jq '.answer'
```

### Search Test

```bash
# Should return relevant sections
curl "http://localhost:8000/search?q=eloquent" | jq '.count'
```

### Load Testing

```bash
# Using Apache Bench
ab -n 100 -c 10 \
  -p query.json \
  -T application/json \
  http://localhost:8000/query

# query.json:
# {"question": "How do I use migrations?"}
```

---

## Support

For API issues:
- Check `/health` endpoint first
- Review logs: `make logs`
- Test individual components: `make check`
- Restart services: `make restart`

For feature requests or bugs, open an issue in the repository.
