"""ChromaDB vector store integration."""

import os
from typing import Dict, List, Optional

# Disable ChromaDB telemetry to prevent Posthog errors
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.config import settings
from src.extraction.markdown_parser import DocSection
from src.indexing.embeddings import OllamaEmbeddings
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

        # Initialize ChromaDB client with telemetry disabled
        chroma_settings = ChromaSettings(
            persist_directory=self.persist_dir,
            anonymized_telemetry=False,
            allow_reset=True,
        )
        self.client = chromadb.Client(chroma_settings)

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Laravel documentation embeddings"},
        )

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

        added_count = 0

        for i in range(0, len(sections), batch_size):
            batch = sections[i:i + batch_size]

            # Prepare data for batch
            documents = []
            metadatas = []
            ids = []

            for section in batch:
                # Create document text
                doc_text = f"# {section.section}\n\n{section.content}"

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

                # Create unique ID
                doc_id = f"{section.version}_{section.file}_{section.chunk_index}"

                documents.append(doc_text)
                metadatas.append(metadata)
                ids.append(doc_id)

            try:
                # Generate embeddings with parallel processing
                embeddings = self.embeddings.embed_documents(
                    documents,
                    parallel=parallel,
                    max_workers=max_workers
                )

                # Add to collection
                self.collection.add(
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids,
                )

                added_count += len(batch)
                logger.info(f"Added batch {i // batch_size + 1}: {added_count}/{len(sections)} sections")

            except Exception as e:
                logger.error(f"Error adding batch: {e}")
                continue

        logger.info(f"Successfully added {added_count} sections to vector store")
        return added_count

    def search(
        self,
        query: str,
        top_k: int = None,
        version_filter: Optional[str] = None,
    ) -> List[Dict]:
        """Search for relevant documentation sections.

        Args:
            query: Search query
            top_k: Number of results to return
            version_filter: Filter by Laravel version

        Returns:
            List of search results with metadata
        """
        top_k = top_k or settings.top_k

        logger.debug(f"Searching for: '{query}' (top_k={top_k})")

        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)

        # Prepare where clause for filtering
        where = {}
        if version_filter:
            where["version"] = version_filter

        # Query the collection
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where if where else None,
            )

            # Format results
            formatted_results = []
            for i in range(len(results["ids"][0])):
                result = {
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                }
                formatted_results.append(result)

            logger.debug(f"Found {len(formatted_results)} results")
            return formatted_results

        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            return []

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
