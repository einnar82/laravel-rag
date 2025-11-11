# System Architecture

## Overview

The Laravel RAG system is a multi-component application designed for efficient retrieval and generation of Laravel documentation queries using local LLMs.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Layer                              │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────────┐          │
│  │   CLI    │  │ Interactive  │  │   REST API      │          │
│  │ Commands │  │     Mode     │  │  (FastAPI)      │          │
│  └────┬─────┘  └──────┬───────┘  └────────┬────────┘          │
└───────┼────────────────┼──────────────────┼────────────────────┘
        │                │                  │
        └────────────────┴──────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │     Application Layer            │
        │  ┌──────────────────────────┐   │
        │  │    RAG Chain Manager     │   │
        │  │     (LangChain)          │   │
        │  └───────┬──────────┬───────┘   │
        │          │          │            │
        │  ┌───────▼──────┐  ┌▼──────────┐│
        │  │  Retrieval   │  │ Generation││
        │  │   Pipeline   │  │  Pipeline  ││
        │  └───────┬──────┘  └┬──────────┘│
        └──────────┼──────────┼────────────┘
                   │          │
        ┌──────────▼──────┐  ┌▼─────────────┐
        │   Data Layer    │  │  Model Layer  │
        │                 │  │               │
        │  ┌───────────┐  │  │ ┌──────────┐ │
        │  │ ChromaDB  │  │  │ │  Ollama  │ │
        │  │  Vector   │  │  │ │          │ │
        │  │  Store    │  │  │ │ Gemma2:2B│ │
        │  └───────────┘  │  │ │  nomic-  │ │
        │  ┌───────────┐  │  │ │  embed   │ │
        │  │  Laravel  │  │  │ └──────────┘ │
        │  │   Docs    │  │  │               │
        │  │  Cache    │  │  │               │
        │  └───────────┘  │  │               │
        └─────────────────┘  └───────────────┘
```

## Component Architecture

### 1. Extraction Layer

**Purpose**: Fetch and parse Laravel documentation

```
┌─────────────────────────────────────┐
│      Extraction Pipeline            │
│                                     │
│  ┌──────────────┐                  │
│  │ DocsFetcher  │                  │
│  │              │                  │
│  │ - Git clone  │                  │
│  │ - Version    │                  │
│  │   checkout   │                  │
│  └──────┬───────┘                  │
│         │                          │
│         ▼                          │
│  ┌──────────────┐                  │
│  │   Markdown   │                  │
│  │    Parser    │                  │
│  │              │                  │
│  │ - H2 section │                  │
│  │   chunking   │                  │
│  │ - Metadata   │                  │
│  │   extraction │                  │
│  └──────┬───────┘                  │
│         │                          │
│         ▼                          │
│  ┌──────────────┐                  │
│  │  DocSection  │                  │
│  │   Objects    │                  │
│  └──────────────┘                  │
└─────────────────────────────────────┘
```

**Key Classes**:
- `DocsFetcher`: Git repository management
- `MarkdownParser`: H2-based chunking
- `DocSection`: Section data model

**Data Flow**:
1. Clone Laravel docs repository
2. Checkout specific version branch
3. Parse markdown files
4. Extract H2 sections
5. Generate metadata (version, file, anchor, heading_path)

### 2. Indexing Layer

**Purpose**: Generate embeddings and store in vector database

```
┌─────────────────────────────────────┐
│      Indexing Pipeline              │
│                                     │
│  ┌──────────────┐                  │
│  │ DocSection   │                  │
│  │   Input      │                  │
│  └──────┬───────┘                  │
│         │                          │
│         ▼                          │
│  ┌──────────────┐                  │
│  │   Ollama     │                  │
│  │  Embeddings  │                  │
│  │              │                  │
│  │ - nomic-     │                  │
│  │   embed-text │                  │
│  │ - 768 dim    │                  │
│  └──────┬───────┘                  │
│         │                          │
│         ▼                          │
│  ┌──────────────┐                  │
│  │  ChromaDB    │                  │
│  │ VectorStore  │                  │
│  │              │                  │
│  │ - Persistent │                  │
│  │ - Cosine     │                  │
│  │   similarity │                  │
│  └──────────────┘                  │
└─────────────────────────────────────┘
```

**Key Classes**:
- `OllamaEmbeddings`: Embedding generation
- `VectorStore`: ChromaDB integration

**Data Flow**:
1. Receive DocSection objects
2. Generate embeddings (batch processing)
3. Store in ChromaDB with metadata
4. Persist to disk

**Storage Schema**:
```
Document:
  - id: "{version}_{file}_{chunk_index}"
  - embedding: [768-dim vector]
  - document: "section text"
  - metadata:
      - version: "12"
      - file: "eloquent.md"
      - section: "Defining Models"
      - anchor: "eloquent.md#defining-models"
      - heading_path: "Eloquent ORM > Defining Models"
      - chunk_index: 0
```

### 3. Retrieval Layer

**Purpose**: Search and retrieve relevant documentation

```
┌─────────────────────────────────────┐
│      Retrieval Pipeline             │
│                                     │
│  ┌──────────────┐                  │
│  │ User Query   │                  │
│  └──────┬───────┘                  │
│         │                          │
│         ▼                          │
│  ┌──────────────┐                  │
│  │   Embed      │                  │
│  │   Query      │                  │
│  └──────┬───────┘                  │
│         │                          │
│         ▼                          │
│  ┌──────────────┐                  │
│  │  Similarity  │                  │
│  │   Search     │                  │
│  │ (ChromaDB)   │                  │
│  └──────┬───────┘                  │
│         │                          │
│         ▼                          │
│  ┌──────────────┐                  │
│  │  Top-K       │                  │
│  │  Results     │                  │
│  └──────┬───────┘                  │
│         │                          │
│         ▼                          │
│  ┌──────────────┐                  │
│  │  Context     │                  │
│  │  Assembly    │                  │
│  └──────────────┘                  │
└─────────────────────────────────────┘
```

**Key Classes**:
- `RAGChain`: Orchestrates retrieval and generation

**Data Flow**:
1. Receive user query
2. Generate query embedding
3. Search vector store (cosine similarity)
4. Retrieve top-K results
5. Format context with metadata

### 4. Generation Layer

**Purpose**: Generate natural language responses

```
┌─────────────────────────────────────┐
│     Generation Pipeline             │
│                                     │
│  ┌──────────────┐                  │
│  │   Context    │                  │
│  │     +        │                  │
│  │   Query      │                  │
│  └──────┬───────┘                  │
│         │                          │
│         ▼                          │
│  ┌──────────────┐                  │
│  │   Prompt     │                  │
│  │  Template    │                  │
│  │              │                  │
│  │ - System     │                  │
│  │   context    │                  │
│  │ - Retrieved  │                  │
│  │   docs       │                  │
│  │ - Question   │                  │
│  └──────┬───────┘                  │
│         │                          │
│         ▼                          │
│  ┌──────────────┐                  │
│  │   Ollama     │                  │
│  │  Gemma2:2B   │                  │
│  │              │                  │
│  │ - Chat API   │                  │
│  │ - Streaming  │                  │
│  └──────┬───────┘                  │
│         │                          │
│         ▼                          │
│  ┌──────────────┐                  │
│  │  Generated   │                  │
│  │  Response    │                  │
│  └──────────────┘                  │
└─────────────────────────────────────┘
```

**Prompt Template**:
```
System: You are a Laravel documentation assistant.
Context: [Retrieved documentation sections]
Question: [User question]
Answer: [Generated by LLM]
```

### 5. Interface Layer

**Purpose**: User interaction interfaces

#### CLI Interface

```
┌──────────────────────────────────┐
│         CLI Commands             │
│                                  │
│  - extract: Fetch docs           │
│  - index: Generate embeddings    │
│  - query: One-off query          │
│  - interactive: Chat mode        │
│  - stats: Statistics             │
│  - check: Health check           │
└──────────────────────────────────┘
```

#### REST API

```
┌──────────────────────────────────┐
│         REST Endpoints           │
│                                  │
│  POST /query                     │
│  GET  /search                    │
│  GET  /stats                     │
│  GET  /versions                  │
│  GET  /health                    │
└──────────────────────────────────┘
```

## Data Models

### DocSection

```python
@dataclass
class DocSection:
    version: str              # Laravel version
    file: str                 # Source file name
    section: str              # Section title
    content: str              # Section content
    heading_path: str         # Full heading path
    anchor: str               # GitHub anchor
    chunk_index: int          # Index in file
    h1_title: Optional[str]   # Page title
```

### Configuration

```python
class Settings:
    # Ollama
    ollama_host: str
    llm_model: str
    embedding_model: str

    # ChromaDB
    chroma_persist_dir: Path
    chroma_collection_name: str

    # Laravel
    laravel_version: str
    docs_cache_dir: Path

    # RAG
    top_k: int
    chunk_size: int
    response_timeout: int
```

## Performance Characteristics

### Latency Breakdown

```
Query Processing:
├─ Query embedding: ~100ms
├─ Vector search: ~50ms
├─ Context assembly: ~10ms
└─ LLM generation: 1-2s
Total: ~1.5-2.5s
```

### Resource Usage

```
Memory:
├─ Ollama + Gemma2:2B: 2-3GB
├─ nomic-embed-text: 500MB
└─ ChromaDB: 100-200MB
Total: ~3-4GB

Storage:
├─ Laravel v12 docs: 5-10MB
├─ Embeddings: 100-200MB
└─ ChromaDB overhead: 50MB
Total: ~150-250MB per version
```

### Throughput

```
Indexing:
- 50 sections/batch
- ~5-10 batches/minute
- ~250-500 sections/minute

Querying:
- Sequential: 1-2 queries/second
- Parallel: 5-10 queries/second (with scaling)
```

## Scalability Considerations

### Vertical Scaling

- Increase container memory limits
- Add more CPU cores for parallel processing
- Use faster storage (SSD) for ChromaDB

### Horizontal Scaling

```
┌─────────────────────────────────────┐
│         Load Balancer               │
└────────┬─────────┬─────────┬────────┘
         │         │         │
    ┌────▼───┐ ┌───▼────┐ ┌─▼──────┐
    │ API 1  │ │ API 2  │ │ API 3  │
    └────┬───┘ └───┬────┘ └─┬──────┘
         │         │         │
         └─────────┴─────────┘
                   │
         ┌─────────▼──────────┐
         │  Shared ChromaDB   │
         │     (Remote)       │
         └────────────────────┘
```

### Distributed Architecture

```
┌──────────────────────────────────────┐
│      API Gateway / Load Balancer     │
└───────────┬──────────────────────────┘
            │
    ┌───────┴───────┐
    │               │
┌───▼────┐    ┌────▼───┐
│ API    │    │ API    │
│ Tier 1 │    │ Tier 2 │
└───┬────┘    └────┬───┘
    │              │
    └──────┬───────┘
           │
    ┌──────▼────────┐
    │   ChromaDB    │
    │   Cluster     │
    └──────┬────────┘
           │
    ┌──────▼────────┐
    │   Ollama      │
    │   Service     │
    └───────────────┘
```

## Security Architecture

### Authentication Flow

```
Client Request
    │
    ▼
API Key Validation
    │
    ├─ Valid ──► Process Request
    │
    └─ Invalid ──► 403 Forbidden
```

### Data Protection

- No user data stored
- Documentation only
- Audit logging for queries
- Rate limiting per IP

## Monitoring Architecture

### Metrics Collection

```
Application
    │
    ├─ Request metrics ──► Prometheus
    ├─ Error logs ──────► Loguru
    └─ Performance ─────► Custom metrics
```

### Health Checks

```
Health Check Pipeline:
├─ Ollama connectivity
├─ ChromaDB availability
├─ Vector store size
└─ Model availability
```

## Future Architecture Enhancements

1. **Caching Layer**: Redis for frequent queries
2. **Message Queue**: RabbitMQ for async processing
3. **CDN**: Static content delivery
4. **Fine-tuned Models**: Custom Laravel-specific models
5. **Multi-tenancy**: Support multiple projects
6. **Observability**: OpenTelemetry integration
