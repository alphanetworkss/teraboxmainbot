"""
Check the number of jobs queued in Redis.
Run this script to see how many download jobs are waiting to be processed.
"""
import asyncio
from redis_queue.job_queue import job_queue
from redis_queue.redis_client import init_redis
from utils.logger import log, setup_logger


async def check_queue_status():
    """Check and display the current queue status."""
    try:
        setup_logger("check_queue")
        
        print("=" * 60)
        print("Redis Queue Status Checker")
        print("=" * 60)
        
        # Initialize Redis connection
        log.info("Connecting to Redis...")
        await init_redis()
        log.info("Connected to Redis successfully")
        
        # Get queue size
        queue_size = await job_queue.get_queue_size()
        
        print(f"\n📊 Queue Status:")
        print("-" * 60)
        print(f"  Queued Jobs: {queue_size}")
        print("-" * 60)
        
        if queue_size == 0:
            print("\n✅ Queue is empty - no jobs waiting!")
        elif queue_size < 5:
            print(f"\n✅ Queue is healthy - {queue_size} job(s) waiting")
        elif queue_size < 20:
            print(f"\n⚠️  Queue is getting busy - {queue_size} jobs waiting")
        else:
            print(f"\n🔴 Queue is very busy - {queue_size} jobs waiting!")
            print("   Consider adding more workers or upload bots")
        
        print()
        
    except Exception as e:
        log.error(f"Error checking queue: {e}")
        print(f"❌ Error: {e}")
    finally:
        # Properly close Redis connection
        from redis_queue.redis_client import close_redis
        await close_redis()


if __name__ == "__main__":
    asyncio.run(check_queue_status())
