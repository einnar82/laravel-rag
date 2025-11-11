# Laravel Documentation RAG System

A production-ready Retrieval-Augmented Generation (RAG) system for querying Laravel documentation using local LLMs. Built with Ollama, ChromaDB, and LangChain for fast, version-aware documentation lookup.

## Features

- **Local LLM Inference**: Uses Ollama with Gemma 2B for privacy and speed
- **Efficient Embeddings**: nomic-embed-text (768 dimensions) optimized for retrieval
- **Persistent Vector Store**: ChromaDB with disk persistence
- **Version-Aware**: Support for multiple Laravel versions with metadata tracking
- **Smart Chunking**: H2-based section chunking preserves context and code examples
- **Multiple Interfaces**: CLI, Interactive mode, and REST API
- **Docker-Based**: Fully containerized with M1 Mac support
- **Production Ready**: Comprehensive logging, error handling, and monitoring

## 📚 Documentation

- **[Quick Start Guide](documentation/QUICKSTART.md)** - Get up and running in 10 minutes
- **[API Reference](documentation/API.md)** - Complete REST API documentation
- **[Architecture](documentation/ARCHITECTURE.md)** - System design and components
- **[Deployment](documentation/DEPLOYMENT.md)** - Production deployment guide
- **[Troubleshooting](documentation/TROUBLESHOOTING.md)** - Common issues and solutions

All documentation is in the [documentation/](documentation/) directory.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- MacBook Pro M1 (or adjust platform in docker-compose.yml)
- 16GB RAM minimum
- 10GB free disk space

### Installation

1. **Clone and setup**:
   ```bash
   cd /path/to/laravel-rag
   make setup
   ```

   This will:
   - Start Docker services
   - Pull required Ollama models (gemma:2b and nomic-embed-text)
   - Initialize the system

2. **Extract Laravel documentation**:
   ```bash
   make extract
   ```

   Downloads Laravel v12 docs from GitHub (default version).

3. **Index documentation**:
   ```bash
   make index
   ```

   Generates embeddings and stores in ChromaDB (~2-5 minutes for v12).

4. **Query documentation**:
   ```bash
   make query Q="How do I create an Eloquent model?"
   ```

## Usage

### CLI Commands

```bash
# Extract documentation
docker-compose exec rag-app python -m src.cli.main extract --version 12

# Index documentation
docker-compose exec rag-app python -m src.cli.main index

# Query (one-off)
docker-compose exec rag-app python -m src.cli.main query "What is middleware?" --show-sources

# Interactive mode
docker-compose exec rag-app python -m src.cli.main interactive

# Check system status
docker-compose exec rag-app python -m src.cli.main check

# View statistics
docker-compose exec rag-app python -m src.cli.main stats
```

### Using Make (Recommended)

```bash
# Setup and management
make setup          # Initial setup
make start          # Start services
make stop           # Stop services
make restart        # Restart services
make logs           # View logs
make clean          # Clean all data (WARNING: destructive)

# Documentation
make extract        # Extract docs
make index          # Index docs
make reindex        # Force re-index

# Querying
make query Q="your question"
make interactive
make stats
make check

# API
make api-test       # Test API endpoints
```

### REST API

Start the API (runs automatically with docker-compose):
```bash
make start
```

API available at `http://localhost:8000`

**API Documentation**: http://localhost:8000/docs

**Endpoints**:

- `POST /query` - Query documentation
  ```bash
  curl -X POST http://localhost:8000/query \
    -H "Content-Type: application/json" \
    -d '{
      "question": "How do I use migrations?",
      "include_sources": true,
      "temperature": 0.7
    }'
  ```

- `GET /search?q=query` - Search without LLM generation
  ```bash
  curl "http://localhost:8000/search?q=eloquent&top_k=5"
  ```

- `GET /stats` - Vector store statistics
- `GET /versions` - Available Laravel versions
- `GET /health` - Health check

### Interactive Mode

```bash
make interactive
```

Provides a conversational interface:
```
Question: How do I create a model?
Answer: To create an Eloquent model in Laravel...

Question: exit
```

## Configuration

### Environment Variables

Create `.env` from `.env.example`:

```bash
# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
LLM_MODEL=gemma:2b
EMBEDDING_MODEL=nomic-embed-text

# ChromaDB
CHROMA_PERSIST_DIR=./chromadb
CHROMA_COLLECTION_NAME=laravel_docs

# Laravel Documentation
LARAVEL_VERSION=12
DOCS_CACHE_DIR=./docs

# RAG Settings
TOP_K=5
RESPONSE_TIMEOUT=30
LOG_LEVEL=INFO
```

### System Configuration

Edit `/Users/rannieollit/Desktop/WebeeLabs/laravel-rag/config/system.yaml` for advanced settings:
- Model parameters
- Chunking strategy
- Performance tuning
- Logging configuration

## Performance

### Resource Usage

- **Memory**: ~3-4GB total
  - Ollama + Gemma 2B: 2-3GB
  - nomic-embed-text: ~500MB
  - ChromaDB: ~100-200MB

- **Storage**:
  - Laravel v12 raw docs: ~5-10MB
  - Embeddings: ~100-200MB
  - ChromaDB overhead: ~50MB

- **Query Performance**:
  - Response time: <3 seconds (target)
  - Embedding generation: ~100ms per query
  - Vector search: <50ms
  - LLM generation: 1-2 seconds

### Optimization Tips

1. **Batch Size**: Adjust `--batch-size` for indexing based on available memory
2. **Top-K**: Lower `TOP_K` for faster responses, higher for more context
3. **Temperature**: Lower (0.3-0.5) for factual answers, higher (0.7-1.0) for creative
4. **Context Window**: Configured in `system.yaml`

## Project Structure

```
laravel-rag/
├── docker-compose.yml          # Docker orchestration
├── Dockerfile                  # Python app container
├── requirements.txt            # Python dependencies
├── Makefile                    # Convenience commands
├── setup.sh                    # Setup script
├── .env.example               # Environment template
├── config/
│   └── system.yaml            # System configuration
├── src/
│   ├── config.py              # Configuration management
│   ├── extraction/            # Document extraction
│   │   ├── docs_fetcher.py   # Git clone & fetch
│   │   └── markdown_parser.py # H2-based chunking
│   ├── indexing/              # Embedding & storage
│   │   ├── embeddings.py     # Ollama embeddings
│   │   └── vector_store.py   # ChromaDB integration
│   ├── retrieval/             # RAG chain
│   │   └── rag_chain.py      # LangChain RAG
│   ├── api/                   # REST API
│   │   └── main.py           # FastAPI application
│   ├── cli/                   # CLI interface
│   │   └── main.py           # Click commands
│   └── utils/
│       └── logger.py          # Logging setup
├── data/                      # Application data
├── chromadb/                  # Vector store persistence
├── sources/                   # Laravel documentation sources cache
└── logs/                      # Application logs
```

## Advanced Usage

### Multiple Versions

Index multiple Laravel versions:

```bash
# Extract and index v11
docker-compose exec rag-app python -m src.cli.main extract --version 11
docker-compose exec rag-app python -m src.cli.main index --version 11

# Query specific version
docker-compose exec rag-app python -m src.cli.main query \
  "How do migrations work?" --version 11
```

### Custom Chunking

Modify `/Users/rannieollit/Desktop/WebeeLabs/laravel-rag/src/extraction/markdown_parser.py` to customize chunking strategy.

### Monitoring

View logs:
```bash
make logs                           # All services
docker-compose logs -f rag-app     # Application only
docker-compose logs -f ollama      # Ollama only
```

Log files:
- Application: `/Users/rannieollit/Desktop/WebeeLabs/laravel-rag/logs/laravel-rag.log`
- Docker: `docker-compose logs`

### Troubleshooting

**Issue**: Models not found
```bash
# Check Ollama
docker exec laravel-rag-ollama ollama list

# Pull manually
docker exec laravel-rag-ollama ollama pull gemma:2b
docker exec laravel-rag-ollama ollama pull nomic-embed-text
```

**Issue**: ChromaDB errors
```bash
# Clear and re-index
make clean
make setup
make extract
make index
```

**Issue**: Out of memory
- Reduce `batch_size` during indexing
- Check Docker resource limits
- Restart Docker

**Note**: Embedding warnings
You may see warnings like `init: embeddings required but some input tokens were not marked as outputs -> overriding`. These are harmless internal messages from the nomic-embed-text model and can be safely ignored. They do not affect embedding quality or system performance. See [documentation/TROUBLESHOOTING.md](documentation/TROUBLESHOOTING.md) for details.

## Development

### Running Tests

```bash
docker-compose exec rag-app pytest tests/ -v
```

### Adding New Features

1. Follow the modular structure in `src/`
2. Use the logger: `from src.utils.logger import app_logger as logger`
3. Update configuration in `src/config.py`
4. Add CLI commands in `src/cli/main.py`
5. Add API endpoints in `src/api/main.py`

### Code Quality

```bash
# Format code
docker-compose exec rag-app black src/

# Type checking
docker-compose exec rag-app mypy src/

# Linting
docker-compose exec rag-app flake8 src/
```

## Production Deployment

### Security Considerations

1. **API Access**: Configure CORS in `src/api/main.py`
2. **Network**: Adjust `docker-compose.yml` to use internal networks
3. **Authentication**: Add API key middleware for production
4. **Rate Limiting**: Enable in `config/system.yaml`

### Scaling

1. **Horizontal**: Run multiple API instances behind load balancer
2. **Vertical**: Increase Docker resource limits
3. **Distributed**: Use remote ChromaDB server

### Backup

```bash
# Backup vector store
tar -czf chromadb-backup.tar.gz chromadb/

# Restore
tar -xzf chromadb-backup.tar.gz
```

## Roadmap

- [ ] Support for additional Laravel versions (11, 10)
- [ ] Integration with Livewire, Filament docs
- [ ] Query result caching
- [ ] Multi-modal support (images, diagrams)
- [ ] Conversation history
- [ ] Fine-tuned models for Laravel
- [ ] Team collaboration features

## License

MIT

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## Support

For issues and questions:
- GitHub Issues: [Create an issue]
- Documentation: See `/Users/rannieollit/Desktop/WebeeLabs/laravel-rag/claude.md`

## Acknowledgments

- Laravel Framework Team for excellent documentation
- Ollama for local LLM inference
- ChromaDB for vector storage
- LangChain for RAG orchestration
