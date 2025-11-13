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
