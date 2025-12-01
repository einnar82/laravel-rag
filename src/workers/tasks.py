"""Background tasks for indexing operations."""

from typing import List

from src.extraction.markdown_parser import DocSection
from src.indexing.embeddings import OllamaEmbeddings
from src.indexing.vector_store import VectorStore
from src.utils.logger import app_logger as logger


def process_indexing_batch(sections: List[DocSection]) -> dict:
    """Process a batch of sections for indexing.

    This function runs in the background worker and indexes
    a batch of document sections into the vector store.

    Args:
        sections: List of DocSection objects to index

    Returns:
        Dictionary with processing statistics
    """
    logger.info(f"Worker processing batch of {len(sections)} sections")
    
    try:
        # Initialize embeddings and vector store
        embeddings = OllamaEmbeddings()
        vector_store = VectorStore(embeddings=embeddings)
        
        # Add sections to vector store (without further queueing)
        added_count = vector_store.add_sections(
            sections,
            batch_size=len(sections),  # Process entire batch at once
            parallel=True,  # Use concurrent embedding generation
            max_workers=4  # Limit workers per job
        )
        
        logger.info(f"Worker successfully indexed {added_count} sections")
        
        return {
            'success': True,
            'processed': added_count,
            'total': len(sections),
            'version': sections[0].version if sections else 'unknown'
        }
        
    except Exception as e:
        logger.error(f"Worker failed to process batch: {e}", exc_info=True)
        return {
            'success': False,
            'processed': 0,
            'total': len(sections),
            'error': str(e)
        }

