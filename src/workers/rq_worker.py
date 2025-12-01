"""RQ Worker process for background task execution."""

import os
import sys

import redis
from rq import Worker

from src.config import settings
from src.utils.logger import app_logger as logger

# Must be first import to patch ChromaDB telemetry
from src.utils.chromadb_fix import disable_chromadb_telemetry


def main():
    """Start RQ worker to process indexing tasks."""
    logger.info("Starting RQ worker for indexing tasks...")
    
    # Get Redis URL from environment or settings
    redis_url = os.getenv("REDIS_URL", settings.redis_url)
    
    try:
        # Connect to Redis
        redis_conn = redis.from_url(redis_url, decode_responses=False)
        redis_conn.ping()
        logger.info(f"Connected to Redis: {redis_url}")
        
        # Create worker
        worker = Worker(
            queues=[settings.redis_queue_name],
            connection=redis_conn,
            name=f"indexing-worker-{os.getpid()}"
        )
        
        logger.info(f"Worker '{worker.name}' listening on queue '{settings.redis_queue_name}'")
        logger.info("Worker ready to process jobs. Press Ctrl+C to stop.")
        
        # Start worker (blocking)
        worker.work(
            with_scheduler=False,  # Don't run scheduler in worker
            burst=False,  # Continuous mode
            logging_level='INFO'
        )
        
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Worker failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

