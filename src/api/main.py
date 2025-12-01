"""FastAPI application for Laravel RAG system."""

# Must be first import to patch ChromaDB telemetry
from src.utils.chromadb_fix import disable_chromadb_telemetry

from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.config import settings
from src.indexing.validator import IndexValidator
from src.indexing.vector_store import VectorStore
from src.retrieval.rag_chain import RAGChain
from src.utils.cache import get_cache_stats
from src.utils.logger import app_logger as logger

# Global instances
rag_chain: Optional[RAGChain] = None
vector_store: Optional[VectorStore] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global rag_chain, vector_store

    logger.info("Starting Laravel RAG API...")

    # Initialize components
    vector_store = VectorStore()
    rag_chain = RAGChain(vector_store=vector_store)

    # Check model availability
    if not rag_chain.check_llm_availability():
        logger.warning(f"LLM model {settings.llm_model} not available")

    logger.info("API ready!")

    yield

    # Cleanup
    logger.info("Shutting down API...")


# Create FastAPI app
app = FastAPI(
    title="Laravel Documentation RAG API",
    description="Query Laravel documentation using RAG (Retrieval-Augmented Generation)",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class QueryRequest(BaseModel):
    """Request model for query endpoint."""

    question: str = Field(..., description="Question about Laravel", min_length=1)
    version: Optional[str] = Field(None, description="Filter by Laravel version")
    top_k: Optional[int] = Field(None, description="Number of results to retrieve", ge=1, le=20)
    temperature: Optional[float] = Field(0.7, description="LLM temperature", ge=0.0, le=1.0)
    include_sources: bool = Field(False, description="Include source documents in response")
    min_similarity: Optional[float] = Field(None, description="Minimum similarity threshold", ge=0.0, le=1.0)
    verify_answer: bool = Field(True, description="Verify answer against context")


class SourceDocument(BaseModel):
    """Source document metadata."""

    file: str
    section: str
    version: str
    anchor: str
    heading_path: str
    distance: Optional[float] = None
    similarity: Optional[float] = None


class QueryResponse(BaseModel):
    """Response model for query endpoint."""

    question: str
    answer: str
    version_filter: Optional[str]
    sources: Optional[List[SourceDocument]] = None
    verified: Optional[bool] = None
    verification_status: Optional[str] = None
    similarity_scores: Optional[List[float]] = None
    cache_hit: Optional[bool] = None


class StatsResponse(BaseModel):
    """Response model for stats endpoint."""

    total_documents: int
    versions: dict
    collection_name: str
    persist_dir: str
    cache_stats: Optional[dict] = None


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    version: str
    ollama_host: str
    llm_model: str
    embedding_model: str
    vector_store_documents: int


# API Endpoints
@app.get("/", tags=["General"])
async def root():
    """Root endpoint."""
    return {
        "message": "Laravel Documentation RAG API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """Health check endpoint."""
    try:
        stats = vector_store.get_stats()

        return HealthResponse(
            status="healthy",
            version="1.0.0",
            ollama_host=settings.ollama_host,
            llm_model=settings.llm_model,
            embedding_model=settings.embedding_model,
            vector_store_documents=stats.get("total_documents", 0),
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.post("/query", response_model=QueryResponse, tags=["Query"])
async def query_documentation(request: QueryRequest):
    """Query Laravel documentation with verification.

    Args:
        request: Query request with question and parameters

    Returns:
        QueryResponse with answer, verification status, and optional sources
    """
    try:
        logger.info(f"Received query: {request.question}")

        # Execute query with verification
        response = rag_chain.query(
            question=request.question,
            version_filter=request.version,
            include_sources=request.include_sources,
            temperature=request.temperature,
            min_similarity=request.min_similarity,
            verify_answer=request.verify_answer,
        )

        # Convert to response model
        return QueryResponse(**response)

    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.get("/stats", response_model=StatsResponse, tags=["Statistics"])
async def get_stats():
    """Get vector store statistics.

    Returns:
        Statistics about the vector store
    """
    try:
        stats = vector_store.get_stats()
        # Add cache stats to response
        cache_stats = get_cache_stats()
        stats["cache_stats"] = cache_stats
        return StatsResponse(**stats)

    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@app.get("/search", tags=["Query"])
async def search_documentation(
    q: str = Query(..., description="Search query", min_length=1),
    version: Optional[str] = Query(None, description="Filter by version"),
    top_k: int = Query(5, description="Number of results", ge=1, le=20),
):
    """Search documentation without LLM generation.

    Args:
        q: Search query
        version: Optional version filter
        top_k: Number of results to return

    Returns:
        List of relevant document sections
    """
    try:
        logger.info(f"Search query: {q}")

        # Search vector store
        results = vector_store.search(
            query=q,
            top_k=top_k,
            version_filter=version,
        )

        # Format results
        formatted_results = [
            {
                "file": r["metadata"]["file"],
                "section": r["metadata"]["section"],
                "version": r["metadata"]["version"],
                "anchor": r["metadata"]["anchor"],
                "heading_path": r["metadata"]["heading_path"],
                "content": r["document"],
                "distance": r["distance"],
            }
            for r in results
        ]

        return {
            "query": q,
            "results": formatted_results,
            "count": len(formatted_results),
        }

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/versions", tags=["Statistics"])
async def get_versions():
    """Get available Laravel versions in the vector store.

    Returns:
        List of available versions with document counts
    """
    try:
        stats = vector_store.get_stats()
        versions = stats.get("versions", {})

        return {
            "versions": [
                {"version": ver, "document_count": count}
                for ver, count in versions.items()
            ],
            "total_versions": len(versions),
        }

    except Exception as e:
        logger.error(f"Version retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get versions: {str(e)}")


@app.get("/validate-index", tags=["Statistics"])
async def validate_index(version: Optional[str] = Query(None, description="Filter by version")):
    """Validate index health and quality.

    Args:
        version: Optional version to validate

    Returns:
        Index validation results
    """
    try:
        validator = IndexValidator(vector_store=vector_store)
        health = validator.check_index_health(version=version)
        return health

    except Exception as e:
        logger.error(f"Index validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@app.get("/cache-stats", tags=["Statistics"])
async def get_cache_stats():
    """Get cache statistics.

    Returns:
        Cache statistics for embeddings and retrieval
    """
    try:
        stats = get_cache_stats()
        return stats

    except Exception as e:
        logger.error(f"Cache stats retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )
