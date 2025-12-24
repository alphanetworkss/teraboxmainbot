"""
Job queue manager using Redis.
Handles job push/consume operations for download tasks.
"""
import json
import asyncio
from typing import Callable, Optional, Dict, Any
from queue.redis_client import get_redis
from config.constants import QUEUE_DOWNLOAD_JOBS, WORKER_POLL_INTERVAL
from utils.logger import log


class JobQueue:
    """Job queue manager for download tasks."""
    
    def __init__(self, queue_name: str = QUEUE_DOWNLOAD_JOBS):
        """
        Initialize job queue.
        
        Args:
            queue_name: Name of the Redis queue
        """
        self.queue_name = queue_name
    
    async def push_job(self, job_data: Dict[str, Any]) -> bool:
        """
        Push a download job to the queue.
        
        Job data structure:
        {
            "link": str,           # Original TeraBox link
            "user_id": int,        # Telegram user ID
            "chat_id": int,        # Telegram chat ID
            "message_id": int,     # Message ID to reply to
            "link_hash": str       # SHA256 hash of the link
        }
        
        Args:
            job_data: Job data dictionary
            
        Returns:
            True if pushed successfully, False otherwise
        """
        try:
            redis = get_redis()
            
            # Serialize job data to JSON
            job_json = json.dumps(job_data)
            
            # Push to Redis list (LPUSH for FIFO with BRPOP)
            await redis.lpush(self.queue_name, job_json)
            
            log.info(f"Pushed job to queue: user_id={job_data.get('user_id')}, hash={job_data.get('link_hash')}")
            return True
            
        except Exception as e:
            log.error(f"Error pushing job to queue: {e}")
            return False
    
    async def consume_jobs(self, callback: Callable, stop_event: Optional[asyncio.Event] = None):
        """
        Consume jobs from the queue and process them.
        
        This is a blocking operation that runs until stop_event is set.
        
        Args:
            callback: Async function to call with job data
            stop_event: Event to signal when to stop consuming
        """
        redis = get_redis()
        log.info(f"Starting job consumer for queue: {self.queue_name}")
        
        while stop_event is None or not stop_event.is_set():
            try:
                # BRPOP with timeout (blocking pop from right)
                result = await redis.brpop(self.queue_name, timeout=WORKER_POLL_INTERVAL)
                
                if result:
                    queue_name, job_json = result
                    
                    # Deserialize job data
                    job_data = json.loads(job_json)
                    
                    log.info(f"Consumed job: user_id={job_data.get('user_id')}, hash={job_data.get('link_hash')}")
                    
                    # Process job with callback
                    try:
                        await callback(job_data)
                    except Exception as e:
                        log.error(f"Error processing job: {e}")
                        # Job is lost if processing fails (consider dead letter queue for production)
                
            except asyncio.CancelledError:
                log.info("Job consumer cancelled")
                break
            except Exception as e:
                log.error(f"Error in job consumer: {e}")
                await asyncio.sleep(1)  # Avoid tight loop on errors
        
        log.info("Job consumer stopped")
    
    async def get_queue_size(self) -> int:
        """
        Get current queue size.
        
        Returns:
            Number of jobs in queue
        """
        try:
            redis = get_redis()
            size = await redis.llen(self.queue_name)
            return size
        except Exception as e:
            log.error(f"Error getting queue size: {e}")
            return 0
    
    async def clear_queue(self) -> bool:
        """
        Clear all jobs from queue (admin/debug use).
        
        Returns:
            True if cleared successfully
        """
        try:
            redis = get_redis()
            await redis.delete(self.queue_name)
            log.warning(f"Cleared queue: {self.queue_name}")
            return True
        except Exception as e:
            log.error(f"Error clearing queue: {e}")
            return False


# Global job queue instance
job_queue = JobQueue()
