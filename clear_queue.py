"""
Clear all queued jobs from Redis.
Run this script to remove all pending download jobs from the queue.
"""
import asyncio
from redis_queue.job_queue import job_queue
from redis_queue.redis_client import init_redis
from utils.logger import log


async def clear_all_jobs():
    """Clear all jobs from the download queue."""
    try:
        # Initialize Redis connection
        log.info("Connecting to Redis...")
        await init_redis()
        log.info("Connected to Redis successfully")
        
        # Get current queue size
        queue_size = await job_queue.get_queue_size()
        log.info(f"Current queue size: {queue_size} jobs")
        
        if queue_size == 0:
            log.info("Queue is already empty!")
            print("✅ Queue is already empty!")
            return
        
        # Confirm before clearing
        print(f"\n⚠️  WARNING: About to delete {queue_size} queued jobs!")
        print("This action cannot be undone.")
        response = input("Are you sure you want to continue? (yes/no): ")
        
        if response.lower() != 'yes':
            log.info("Operation cancelled by user")
            print("❌ Cancelled - no jobs were deleted")
            return
        
        # Clear the queue
        success = await job_queue.clear_queue()
        
        if success:
            log.info(f"✅ Successfully cleared {queue_size} jobs from queue")
            print(f"✅ Successfully cleared {queue_size} jobs from the queue!")
        else:
            log.error("Failed to clear queue")
            print("❌ Failed to clear queue - check logs for details")
            
    except Exception as e:
        log.error(f"Error clearing queue: {e}")
        print(f"❌ Error: {e}")
    finally:
        # Properly close Redis connection
        from redis_queue.redis_client import close_redis
        await close_redis()


if __name__ == "__main__":
    print("=" * 60)
    print("Redis Queue Cleaner")
    print("=" * 60)
    asyncio.run(clear_all_jobs())
