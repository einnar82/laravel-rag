"""Redis Queue task management for indexing jobs."""

import os
from typing import List, Optional

import redis
from rq import Queue
from rq.job import Job

from src.config import settings
from src.extraction.markdown_parser import DocSection
from src.utils.logger import app_logger as logger


class IndexingQueue:
    """Manage Redis queue for indexing operations."""

    def __init__(self):
        """Initialize Redis connection and queue."""
        # Get Redis URL from environment or settings
        redis_url = os.getenv("REDIS_URL", settings.redis_url)
        
        try:
            self.redis_conn = redis.from_url(redis_url, decode_responses=False)
            self.queue = Queue(
                name=settings.redis_queue_name,
                connection=self.redis_conn,
                default_timeout=settings.redis_queue_timeout
            )
            logger.info(f"Connected to Redis queue: {settings.redis_queue_name}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def enqueue_indexing_batch(
        self,
        sections: List[DocSection],
        batch_size: int = None,
        priority: str = "high"
    ) -> List[Job]:
        """Enqueue sections for indexing in batches.

        Args:
            sections: List of DocSection objects to index
            batch_size: Number of sections per job
            priority: Job priority ('low', 'normal', 'high')

        Returns:
            List of RQ Job objects
        """
        batch_size = batch_size or settings.queue_batch_size
        jobs = []

        # Split sections into batches
        for i in range(0, len(sections), batch_size):
            batch = sections[i:i + batch_size]
            
            try:
                # Enqueue the batch
                job = self.queue.enqueue(
                    'src.workers.tasks.process_indexing_batch',
                    batch,
                    job_timeout=settings.redis_queue_timeout,
                    result_ttl=settings.redis_result_ttl,
                    failure_ttl=86400,  # Keep failures for 24 hours
                    meta={
                        'batch_number': i // batch_size + 1,
                        'batch_size': len(batch),
                        'version': batch[0].version if batch else 'unknown'
                    }
                )
                jobs.append(job)
                logger.debug(f"Enqueued batch {i // batch_size + 1} with {len(batch)} sections (Job ID: {job.id})")
            except Exception as e:
                logger.error(f"Failed to enqueue batch {i // batch_size + 1}: {e}")
                continue

        logger.info(f"Enqueued {len(jobs)} indexing jobs for {len(sections)} sections")
        return jobs

    def get_job_status(self, job_id: str) -> Optional[dict]:
        """Get status of a specific job.

        Args:
            job_id: Job ID to check

        Returns:
            Dictionary with job status information
        """
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            return {
                'id': job.id,
                'status': job.get_status(),
                'created_at': job.created_at,
                'started_at': job.started_at,
                'ended_at': job.ended_at,
                'result': job.result if job.is_finished else None,
                'exc_info': job.exc_info if job.is_failed else None,
                'meta': job.meta
            }
        except Exception as e:
            logger.error(f"Failed to fetch job {job_id}: {e}")
            return None

    def get_queue_info(self) -> dict:
        """Get information about the queue.

        Returns:
            Dictionary with queue statistics
        """
        try:
            return {
                'name': self.queue.name,
                'count': len(self.queue),
                'started_jobs': self.queue.started_job_registry.count,
                'finished_jobs': self.queue.finished_job_registry.count,
                'failed_jobs': self.queue.failed_job_registry.count,
                'scheduled_jobs': self.queue.scheduled_job_registry.count,
                'workers': len(self.queue.workers)
            }
        except Exception as e:
            logger.error(f"Failed to get queue info: {e}")
            return {}

    def wait_for_jobs(self, jobs: List[Job], poll_interval: float = 1.0) -> dict:
        """Wait for all jobs to complete.

        Args:
            jobs: List of Job objects to wait for
            poll_interval: Polling interval in seconds

        Returns:
            Dictionary with summary statistics
        """
        import time

        logger.info(f"Waiting for {len(jobs)} jobs to complete...")
        
        completed = 0
        failed = 0
        total_processed = 0

        while jobs:
            time.sleep(poll_interval)
            
            # Check each job
            remaining_jobs = []
            for job in jobs:
                try:
                    job.refresh()
                    
                    if job.is_finished:
                        completed += 1
                        result = job.result or {}
                        total_processed += result.get('processed', 0)
                        logger.debug(f"Job {job.id} completed: {result}")
                    elif job.is_failed:
                        failed += 1
                        logger.error(f"Job {job.id} failed: {job.exc_info}")
                    else:
                        remaining_jobs.append(job)
                except Exception as e:
                    logger.error(f"Error checking job status: {e}")
                    remaining_jobs.append(job)
            
            jobs = remaining_jobs
            
            if completed + failed > 0:
                progress = (completed + failed) / (completed + failed + len(jobs)) * 100
                logger.info(
                    f"Progress: {progress:.1f}% "
                    f"(Completed: {completed}, Failed: {failed}, Pending: {len(jobs)})"
                )

        logger.info(f"All jobs finished. Completed: {completed}, Failed: {failed}, Processed: {total_processed}")
        
        return {
            'completed': completed,
            'failed': failed,
            'total_processed': total_processed
        }

    def clear_failed_jobs(self):
        """Clear all failed jobs from the queue."""
        try:
            count = self.queue.failed_job_registry.count
            for job_id in self.queue.failed_job_registry.get_job_ids():
                job = Job.fetch(job_id, connection=self.redis_conn)
                job.delete()
            logger.info(f"Cleared {count} failed jobs")
        except Exception as e:
            logger.error(f"Failed to clear failed jobs: {e}")

    def clear_finished_jobs(self):
        """Clear all finished jobs from the queue."""
        try:
            count = self.queue.finished_job_registry.count
            for job_id in self.queue.finished_job_registry.get_job_ids():
                job = Job.fetch(job_id, connection=self.redis_conn)
                job.delete()
            logger.info(f"Cleared {count} finished jobs")
        except Exception as e:
            logger.error(f"Failed to clear finished jobs: {e}")

    def is_healthy(self) -> bool:
        """Check if Redis connection is healthy.

        Returns:
            True if connected and responsive
        """
        try:
            self.redis_conn.ping()
            return True
        except Exception:
            return False

