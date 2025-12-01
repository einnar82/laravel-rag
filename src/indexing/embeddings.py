"""Embedding generation using Ollama with parallel processing support."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import ollama

from src.config import settings
from src.utils.cache import get_embedding_cache
from src.utils.logger import app_logger as logger


class OllamaEmbeddings:
    """Generate embeddings using Ollama's nomic-embed-text model."""

    def __init__(
        self,
        model: str = None,
        base_url: str = None,
    ):
        """Initialize the embeddings generator.

        Args:
            model: Embedding model name
            base_url: Ollama API base URL
        """
        self.model = model or settings.embedding_model
        self.base_url = base_url or settings.ollama_host
        self.client = ollama.Client(host=self.base_url)
        self._cached_model = None  # Track model for cache invalidation
        self.embedding_cache = get_embedding_cache()

        logger.info(f"Initialized Ollama embeddings with model: {self.model}")

    def _embed_single(self, text: str, index: int) -> tuple[int, List[float]]:
        """Generate embedding for a single document (internal method for parallel processing).

        Args:
            text: Text document to embed
            index: Original index in the batch

        Returns:
            Tuple of (index, embedding vector)
        """
        try:
            response = self.client.embeddings(
                model=self.model,
                prompt=text,
            )
            return (index, response["embedding"])
        except Exception as e:
            logger.error(f"Error generating embedding at index {index}: {e}")
            return (index, [0.0] * 768)  # Return zero vector on error

    def embed_documents(self, texts: List[str], parallel: bool = True, max_workers: int = None) -> List[List[float]]:
        """Generate embeddings for a list of documents with parallel processing support.

        Args:
            texts: List of text documents to embed
            parallel: Whether to use parallel processing (default: True)
            max_workers: Maximum number of parallel workers (default: min(8, len(texts)))

        Returns:
            List of embedding vectors in the same order as input texts

        Note:
            Parallel processing significantly speeds up embedding generation for large batches.
            You may see warnings from Ollama about token handling - these are harmless.
        """
        if not texts:
            return []

        logger.debug(f"Generating embeddings for {len(texts)} documents (parallel={parallel})...")

        if not parallel or len(texts) == 1:
            # Sequential processing for small batches or when parallel is disabled
            embeddings = []
            for text in texts:
                try:
                    response = self.client.embeddings(
                        model=self.model,
                        prompt=text,
                    )
                    embeddings.append(response["embedding"])
                except Exception as e:
                    logger.error(f"Error generating embedding: {e}")
                    embeddings.append([0.0] * 768)
            logger.debug(f"Generated {len(embeddings)} embeddings (sequential)")
            return embeddings

        # Parallel processing
        if max_workers is None:
            max_workers = min(8, len(texts))  # Limit to 8 workers by default

        logger.debug(f"Using {max_workers} parallel workers for embedding generation")

        # Create indexed results dict
        results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_index = {
                executor.submit(self._embed_single, text, i): i
                for i, text in enumerate(texts)
            }

            # Collect results as they complete
            for future in as_completed(future_to_index):
                index, embedding = future.result()
                results[index] = embedding

        # Return embeddings in original order
        embeddings = [results[i] for i in range(len(texts))]
        logger.debug(f"Generated {len(embeddings)} embeddings (parallel)")
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single query with caching.

        Args:
            text: Query text to embed

        Returns:
            Embedding vector

        Note:
            You may see warnings from Ollama about token handling. These are
            harmless and can be ignored.
        """
        # Check if model changed (invalidate cache)
        if self._cached_model != self.model:
            self.embedding_cache.clear()
            self._cached_model = self.model
            logger.info(f"Model changed to {self.model}, embedding cache cleared")

        # Check cache first
        cached_embedding = self.embedding_cache.get(text)
        if cached_embedding is not None:
            return cached_embedding

        # Generate embedding
        try:
            # Note: Ollama may emit harmless warnings about token handling
            response = self.client.embeddings(
                model=self.model,
                prompt=text,
            )
            embedding = response["embedding"]

            # Cache the embedding
            self.embedding_cache.set(text, embedding)

            return embedding
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            return [0.0] * 768  # Return zero vector on error

    def check_model_availability(self) -> bool:
        """Check if the embedding model is available.

        Returns:
            True if model is available, False otherwise
        """
        try:
            models = self.client.list()
            available_models = [m["name"] for m in models.get("models", [])]

            # Check for exact match or with :latest tag
            model_found = False
            if self.model in available_models:
                model_found = True
            elif f"{self.model}:latest" in available_models:
                model_found = True
                logger.info(f"Model {self.model} found as {self.model}:latest")
            elif any(m.startswith(f"{self.model}:") for m in available_models):
                # Check if model exists with any tag
                model_found = True
                matching = [m for m in available_models if m.startswith(f"{self.model}:")]
                logger.info(f"Model {self.model} found as {matching[0]}")

            if model_found:
                logger.info(f"Model {self.model} is available")
                return True
            else:
                logger.warning(f"Model {self.model} not found. Available models: {available_models}")
                return False

        except Exception as e:
            logger.error(f"Error checking model availability: {e}")
            return False

    def pull_model(self) -> bool:
        """Pull the embedding model if not available.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Pulling model {self.model}...")
            self.client.pull(self.model)
            logger.info(f"Successfully pulled {self.model}")
            return True
        except Exception as e:
            logger.error(f"Error pulling model: {e}")
            return False
