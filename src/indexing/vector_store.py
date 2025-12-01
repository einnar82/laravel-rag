"""ChromaDB vector store integration."""

import os
import time
from typing import Dict, List, Optional, Set

# Disable ChromaDB telemetry to prevent Posthog errors
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.config import settings
from src.extraction.markdown_parser import DocSection
from src.indexing.embeddings import OllamaEmbeddings
from src.utils.cache import get_retrieval_cache
from src.utils.logger import app_logger as logger


class VectorStore:
    """Manage document storage and retrieval with ChromaDB."""

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        collection_name: Optional[str] = None,
        embeddings: Optional[OllamaEmbeddings] = None,
    ):
        """Initialize the vector store.

        Args:
            persist_dir: Directory for ChromaDB persistence
            collection_name: Name of the ChromaDB collection
            embeddings: Embeddings generator instance
        """
        self.persist_dir = persist_dir or str(settings.chroma_persist_dir)
        self.collection_name = collection_name or settings.chroma_collection_name
        self.embeddings = embeddings or OllamaEmbeddings()

        # Initialize ChromaDB client with persistence
        # Use PersistentClient for automatic persistence in ChromaDB 0.4.x
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            )
        )

        # Get or create collection with optimized configuration
        # Configure HNSW index for faster approximate nearest neighbor search
        collection_metadata = {
            "description": "Laravel documentation embeddings",
            "hnsw:space": "cosine",  # Distance metric (cosine similarity)
        }

        try:
            # Try to get existing collection
            self.collection = self.client.get_collection(
                name=self.collection_name,
            )
            # Check if collection is using cosine distance
            existing_metadata = self.collection.metadata
            if existing_metadata.get("hnsw:space") != "cosine":
                logger.warning(
                    f"Existing collection uses {existing_metadata.get('hnsw:space', 'l2')} distance. "
                    "Consider recreating with cosine for better similarity scores."
                )
            logger.info(f"Using existing collection: {self.collection_name}")
        except Exception:
            # Create new collection with optimized settings
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata=collection_metadata,
                # HNSW index parameters for performance
                # Note: ChromaDB may not expose all HNSW parameters directly
                # These are set via metadata or collection configuration
            )
            logger.info(f"Created new collection: {self.collection_name} with cosine distance metric")

        # Initialize retrieval cache
        self.retrieval_cache = get_retrieval_cache()

        logger.info(f"Initialized vector store: {self.collection_name}")
        logger.info(f"Persistence directory: {self.persist_dir}")
        logger.info(f"Current document count: {self.collection.count()}")

    def add_sections(self, sections: List[DocSection], batch_size: int = 50,
                     parallel: bool = True, max_workers: int = None) -> int:
        """Add documentation sections to the vector store with parallel embedding generation.

        Args:
            sections: List of DocSection objects to add
            batch_size: Number of sections to process in each batch
            parallel: Whether to use parallel processing for embeddings (default: True)
            max_workers: Maximum number of parallel workers for embeddings (default: auto)

        Returns:
            Number of sections added
        """
        logger.info(f"Adding {len(sections)} sections to vector store (parallel={parallel})...")
        start_time = time.time()

        # Pre-check for existing IDs to avoid duplicate work
        existing_ids: Set[str] = set()
        try:
            existing_docs = self.collection.get()
            existing_ids = set(existing_docs.get("ids", []))
            logger.debug(f"Found {len(existing_ids)} existing documents")
        except Exception as e:
            logger.warning(f"Could not check existing documents: {e}")

        added_count = 0
        skipped_count = 0
        failed_count = 0
        total_batches = (len(sections) + batch_size - 1) // batch_size

        for i in range(0, len(sections), batch_size):
            batch = sections[i:i + batch_size]
            batch_num = i // batch_size + 1

            # Prepare data for batch with deduplication
            documents = []
            metadatas = []
            ids = []
            batch_ids_to_add = []

            for section in batch:
                # Create unique ID
                doc_id = f"{section.version}_{section.file}_{section.chunk_index}"

                # Skip if already exists
                if doc_id in existing_ids:
                    skipped_count += 1
                    continue

                # Create document text
                doc_text = f"# {section.section}\n\n{section.content}"

                # Skip empty documents
                if not doc_text.strip():
                    skipped_count += 1
                    continue

                # Create metadata
                metadata = {
                    "version": section.version,
                    "file": section.file,
                    "section": section.section,
                    "heading_path": section.heading_path,
                    "anchor": section.anchor,
                    "chunk_index": section.chunk_index,
                    "h1_title": section.h1_title or "",
                }

                documents.append(doc_text)
                metadatas.append(metadata)
                ids.append(doc_id)
                batch_ids_to_add.append(doc_id)

            # Skip batch if all documents were duplicates
            if not documents:
                logger.debug(f"Batch {batch_num}/{total_batches}: All documents skipped (duplicates)")
                continue

            try:
                # Generate embeddings with parallel processing
                embeddings = self.embeddings.embed_documents(
                    documents,
                    parallel=parallel,
                    max_workers=max_workers
                )

                # Verify embeddings were generated
                if len(embeddings) != len(documents):
                    logger.error(f"Embedding count mismatch: {len(embeddings)} != {len(documents)}")
                    failed_count += len(documents)
                    continue

                # Add to collection (bulk operation)
                self.collection.add(
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids,
                )

                # Update existing IDs set
                existing_ids.update(batch_ids_to_add)
                added_count += len(documents)

                # Calculate progress and ETA
                elapsed = time.time() - start_time
                rate = added_count / elapsed if elapsed > 0 else 0
                remaining = len(sections) - (added_count + skipped_count + failed_count)
                eta = remaining / rate if rate > 0 else 0

                logger.info(
                    f"Batch {batch_num}/{total_batches}: Added {len(documents)} sections "
                    f"({added_count}/{len(sections)} total, {skipped_count} skipped, "
                    f"{failed_count} failed, ETA: {eta:.1f}s)"
                )

            except Exception as e:
                logger.error(f"Error adding batch {batch_num}: {e}")
                failed_count += len(documents)
                continue

        # Invalidate retrieval cache after adding new documents
        if added_count > 0:
            self.retrieval_cache.invalidate()
            logger.info("Retrieval cache invalidated after indexing")

        elapsed = time.time() - start_time
        rate = added_count / elapsed if elapsed > 0 else 0

        logger.info(
            f"Successfully added {added_count} sections to vector store "
            f"({skipped_count} skipped, {failed_count} failed) in {elapsed:.1f}s "
            f"({rate:.1f} sections/sec)"
        )

        return added_count

    def search(
        self,
        query: str,
        top_k: int = None,
        version_filter: Optional[str] = None,
    ) -> List[Dict]:
        """Search for relevant documentation sections with caching and performance optimization.

        Args:
            query: Search query
            top_k: Number of results to return
            version_filter: Filter by Laravel version

        Returns:
            List of search results with metadata and similarity scores
        """
        top_k = top_k or settings.top_k
        search_start = time.time()

        logger.debug(f"Searching for: '{query}' (top_k={top_k})")

        # Check cache first
        cached_results = self.retrieval_cache.get(query, version_filter, top_k)
        if cached_results is not None:
            logger.debug("Retrieval cache hit")
            return cached_results

        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)

        # Prepare where clause for filtering
        where = {}
        if version_filter:
            where["version"] = version_filter

        # Query the collection with optimized parameters
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, 100),  # Limit to reasonable max
                where=where if where else None,
                include=["documents", "metadatas", "distances"],  # Only fetch needed fields
            )

            # Format results and convert distance to similarity
            formatted_results = []
            if results["ids"] and len(results["ids"][0]) > 0:
                for i in range(len(results["ids"][0])):
                    distance = results["distances"][0][i]
                    
                    # Convert distance to similarity based on metric
                    # ChromaDB cosine distance is 0-2, where 0=identical, 2=opposite
                    # ChromaDB L2 (Euclidean squared) distance is 0-infinity
                    if distance < 3.0:  # Likely cosine distance (0-2 range)
                        similarity = 1.0 - (distance / 2.0)  # Normalize to 0-1
                    else:  # Likely L2/Euclidean squared distance
                        # For L2: convert to similarity using inverse
                        # Lower distance = higher similarity
                        similarity = 1.0 / (1.0 + (distance / 100.0))
                        logger.debug(f"Using L2 distance conversion: distance={distance:.2f}, similarity={similarity:.4f}")

                    result = {
                        "id": results["ids"][0][i],
                        "document": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": distance,
                        "similarity": similarity,  # Add similarity score
                    }
                    formatted_results.append(result)

            # Cache results
            self.retrieval_cache.set(query, formatted_results, version_filter, top_k)

            search_time = time.time() - search_start
            logger.debug(f"Found {len(formatted_results)} results in {search_time*1000:.1f}ms")
            return formatted_results

        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            return []

    def recreate_collection(self) -> bool:
        """Delete and recreate the collection with optimized settings.

        Returns:
            True if successful
        """
        try:
            logger.warning(f"Recreating collection: {self.collection_name}")

            # Delete existing collection
            try:
                self.client.delete_collection(name=self.collection_name)
                logger.info("Deleted existing collection")
            except Exception as e:
                logger.debug(f"Collection didn't exist or couldn't be deleted: {e}")

            # Create new collection with optimized settings
            collection_metadata = {
                "description": "Laravel documentation embeddings",
                "hnsw:space": "cosine",  # Distance metric (cosine similarity)
            }

            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata=collection_metadata,
            )
            logger.info(f"Created new collection with cosine distance metric")

            # Invalidate retrieval cache
            self.retrieval_cache.clear()

            return True

        except Exception as e:
            logger.error(f"Error recreating collection: {e}")
            return False

    def clear_version(self, version: str) -> bool:
        """Clear all documents for a specific version.

        Args:
            version: Laravel version to clear

        Returns:
            True if successful
        """
        try:
            logger.warning(f"Clearing all documents for version {version}...")

            # Get all IDs for the version
            results = self.collection.get(
                where={"version": version},
            )

            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                logger.info(f"Cleared {len(results['ids'])} documents for version {version}")

            return True

        except Exception as e:
            logger.error(f"Error clearing version: {e}")
            return False

    def get_stats(self) -> Dict:
        """Get statistics about the vector store.

        Returns:
            Dictionary with statistics
        """
        try:
            total_count = self.collection.count()

            # Get version distribution
            all_docs = self.collection.get()
            versions = {}
            for metadata in all_docs.get("metadatas", []):
                version = metadata.get("version", "unknown")
                versions[version] = versions.get(version, 0) + 1

            return {
                "total_documents": total_count,
                "versions": versions,
                "collection_name": self.collection_name,
                "persist_dir": self.persist_dir,
            }

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
