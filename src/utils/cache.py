"""Caching utilities for embeddings and retrieval results."""

import hashlib
import time
from typing import Any, Dict, List, Optional

from src.config import settings
from src.utils.logger import app_logger as logger


class CacheEntry:
    """Represents a cache entry with TTL."""

    def __init__(self, value: Any, ttl: int):
        """Initialize cache entry.

        Args:
            value: Cached value
            ttl: Time to live in seconds
        """
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl

    def is_expired(self) -> bool:
        """Check if cache entry is expired.

        Returns:
            True if expired, False otherwise
        """
        return time.time() - self.created_at > self.ttl

    def is_valid(self) -> bool:
        """Check if cache entry is still valid.

        Returns:
            True if valid, False otherwise
        """
        return not self.is_expired()


class EmbeddingCache:
    """Cache for query embeddings."""

    def __init__(self, max_size: int = None, ttl: int = None):
        """Initialize embedding cache.

        Args:
            max_size: Maximum number of cached items
            ttl: Time to live in seconds
        """
        self.max_size = max_size or settings.cache_max_size
        self.ttl = ttl or settings.cache_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []
        self.hits = 0
        self.misses = 0

    def _generate_key(self, text: str) -> str:
        """Generate cache key from text.

        Args:
            text: Input text

        Returns:
            Cache key
        """
        return hashlib.sha256(text.encode()).hexdigest()

    def get(self, text: str) -> Optional[List[float]]:
        """Get cached embedding.

        Args:
            text: Input text

        Returns:
            Cached embedding or None if not found/expired
        """
        if not settings.embedding_cache_enabled:
            return None

        key = self._generate_key(text)

        if key in self._cache:
            entry = self._cache[key]
            if entry.is_valid():
                # Update access order
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)
                self.hits += 1
                logger.debug(f"Embedding cache hit for key: {key[:8]}...")
                return entry.value
            else:
                # Remove expired entry
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)

        self.misses += 1
        return None

    def set(self, text: str, embedding: List[float]) -> None:
        """Cache embedding.

        Args:
            text: Input text
            embedding: Embedding vector
        """
        if not settings.embedding_cache_enabled:
            return

        key = self._generate_key(text)

        # Evict if cache is full (LRU)
        if len(self._cache) >= self.max_size and key not in self._cache:
            # Remove least recently used
            if self._access_order:
                lru_key = self._access_order.pop(0)
                if lru_key in self._cache:
                    del self._cache[lru_key]

        self._cache[key] = CacheEntry(embedding, self.ttl)
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

        logger.debug(f"Cached embedding for key: {key[:8]}...")

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self._access_order.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Embedding cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0.0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2),
            "ttl": self.ttl,
        }


class RetrievalCache:
    """Cache for retrieval results."""

    def __init__(self, max_size: int = None, ttl: int = None):
        """Initialize retrieval cache.

        Args:
            max_size: Maximum number of cached items
            ttl: Time to live in seconds
        """
        self.max_size = max_size or settings.cache_max_size
        self.ttl = ttl or settings.cache_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []
        self.hits = 0
        self.misses = 0

    def _generate_key(self, query: str, version_filter: Optional[str], top_k: int) -> str:
        """Generate cache key from query parameters.

        Args:
            query: Search query
            version_filter: Optional version filter
            top_k: Number of results

        Returns:
            Cache key
        """
        key_data = f"{query}|{version_filter or ''}|{top_k}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get(self, query: str, version_filter: Optional[str] = None, top_k: int = 5) -> Optional[List[Dict]]:
        """Get cached retrieval results.

        Args:
            query: Search query
            version_filter: Optional version filter
            top_k: Number of results

        Returns:
            Cached results or None if not found/expired
        """
        if not settings.retrieval_cache_enabled:
            return None

        key = self._generate_key(query, version_filter, top_k)

        if key in self._cache:
            entry = self._cache[key]
            if entry.is_valid():
                # Update access order
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)
                self.hits += 1
                logger.debug(f"Retrieval cache hit for query: {query[:50]}...")
                return entry.value
            else:
                # Remove expired entry
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)

        self.misses += 1
        return None

    def set(self, query: str, results: List[Dict], version_filter: Optional[str] = None, top_k: int = 5) -> None:
        """Cache retrieval results.

        Args:
            query: Search query
            results: Retrieval results
            version_filter: Optional version filter
            top_k: Number of results
        """
        if not settings.retrieval_cache_enabled:
            return

        key = self._generate_key(query, version_filter, top_k)

        # Evict if cache is full (LRU)
        if len(self._cache) >= self.max_size and key not in self._cache:
            # Remove least recently used
            if self._access_order:
                lru_key = self._access_order.pop(0)
                if lru_key in self._cache:
                    del self._cache[lru_key]

        self._cache[key] = CacheEntry(results, self.ttl)
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

        logger.debug(f"Cached retrieval results for query: {query[:50]}...")

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self._access_order.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Retrieval cache cleared")

    def invalidate(self) -> None:
        """Invalidate all cache entries (mark for refresh)."""
        self.clear()
        logger.info("Retrieval cache invalidated")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0.0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2),
            "ttl": self.ttl,
        }


# Global cache instances
_embedding_cache: Optional[EmbeddingCache] = None
_retrieval_cache: Optional[RetrievalCache] = None


def get_embedding_cache() -> EmbeddingCache:
    """Get global embedding cache instance.

    Returns:
        EmbeddingCache instance
    """
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache()
    return _embedding_cache


def get_retrieval_cache() -> RetrievalCache:
    """Get global retrieval cache instance.

    Returns:
        RetrievalCache instance
    """
    global _retrieval_cache
    if _retrieval_cache is None:
        _retrieval_cache = RetrievalCache()
    return _retrieval_cache


def clear_all_caches() -> None:
    """Clear all caches."""
    if _embedding_cache:
        _embedding_cache.clear()
    if _retrieval_cache:
        _retrieval_cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics for all caches.

    Returns:
        Dictionary with cache statistics
    """
    stats = {}
    if _embedding_cache:
        stats["embedding"] = _embedding_cache.get_stats()
    if _retrieval_cache:
        stats["retrieval"] = _retrieval_cache.get_stats()
    return stats

