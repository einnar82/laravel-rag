"""Configuration management for Laravel RAG system."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL for task queue and caching")
    redis_enabled: bool = Field(default=True, description="Enable Redis queue for indexing")
    redis_queue_name: str = Field(default="laravel-rag-indexing", description="Redis queue name")
    redis_queue_timeout: int = Field(default=600, ge=60, description="Queue job timeout in seconds")
    redis_result_ttl: int = Field(default=3600, ge=60, description="Queue result TTL in seconds")
    
    # Ollama Configuration
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama API host")
    llm_model: str = Field(default="gemma:2b", description="LLM model name")
    embedding_model: str = Field(default="nomic-embed-text", description="Embedding model name")

    # ChromaDB Configuration
    chroma_persist_dir: Path = Field(default=Path("./chromadb"), description="ChromaDB persistence directory")
    chroma_collection_name: str = Field(default="laravel_docs", description="ChromaDB collection name")

    # Laravel Documentation
    laravel_docs_repo: str = Field(
        default="https://github.com/laravel/docs.git",
        description="Laravel docs Git repository URL"
    )
    laravel_version: str = Field(default="12", description="Laravel version to extract")
    docs_cache_dir: Path = Field(default=Path("./sources"), description="Laravel documentation sources cache directory")

    # RAG Configuration
    top_k: int = Field(default=5, ge=1, le=20, description="Number of top results to retrieve")
    min_similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum similarity score to generate answer")

    # Chunk Size Optimization Parameters
    chunk_strategy: str = Field(default="adaptive", description="Chunking strategy: 'anchor' (H2-based only) or 'adaptive' (smart splitting)")
    max_chunk_size: int = Field(default=2000, ge=500, le=10000, description="Maximum characters per chunk (for adaptive strategy)")
    min_chunk_size: int = Field(default=200, ge=50, le=2000, description="Minimum characters per chunk (for adaptive strategy)")
    chunk_overlap: int = Field(default=200, ge=0, le=1000, description="Overlap between split chunks (for adaptive strategy)")
    preserve_code_blocks: bool = Field(default=True, description="Try to keep code blocks intact when splitting")

    response_timeout: int = Field(default=30, ge=5, le=120, description="Response timeout in seconds")

    # Indexing Configuration
    parallel_indexing: bool = Field(default=True, description="Enable parallel processing for indexing")
    max_workers: int = Field(default=8, ge=1, le=16, description="Maximum parallel workers for embeddings")
    batch_size: int = Field(default=50, ge=1, le=200, description="Batch size for indexing")
    queue_indexing: bool = Field(default=True, description="Use Redis queue for indexing (async processing)")
    queue_batch_size: int = Field(default=50, ge=10, le=100, description="Sections per queue job")
    
    # Cache Configuration
    cache_enabled: bool = Field(default=True, description="Enable caching")
    cache_ttl: int = Field(default=3600, ge=60, description="Cache TTL in seconds")
    cache_max_size: int = Field(default=1000, ge=100, description="Maximum cache size")
    embedding_cache_enabled: bool = Field(default=True, description="Enable embedding cache")
    retrieval_cache_enabled: bool = Field(default=True, description="Enable retrieval result cache")
    
    # ChromaDB Performance Settings
    chroma_hnsw_M: int = Field(default=16, ge=4, le=64, description="HNSW M parameter")
    chroma_hnsw_ef_construction: int = Field(default=200, ge=50, le=500, description="HNSW ef_construction parameter")
    chroma_hnsw_ef_search: int = Field(default=50, ge=10, le=200, description="HNSW ef_search parameter")
    chroma_metadata_indexing: bool = Field(default=True, description="Enable metadata indexing")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Path = Field(default=Path("./logs/laravel-rag.log"), description="Log file path")

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, ge=1024, le=65535, description="API port")
    api_workers: int = Field(default=1, ge=1, le=8, description="Number of API workers")

    def __init__(self, **kwargs):
        """Initialize settings and create necessary directories."""
        super().__init__(**kwargs)
        self.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
        self.docs_cache_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    @property
    def docs_version_dir(self) -> Path:
        """Get the directory for the specific Laravel version."""
        return self.docs_cache_dir / f"v{self.laravel_version}"

    @property
    def branch_name(self) -> str:
        """Get the Git branch name for the Laravel version."""
        return f"{self.laravel_version}.x"


# Global settings instance
settings = Settings()
