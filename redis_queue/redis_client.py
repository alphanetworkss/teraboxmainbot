"""
Redis client manager.
Handles async Redis connection.
"""
import redis.asyncio as redis
from typing import Optional
from config.settings import settings
from utils.logger import log


class RedisClient:
    """Redis connection manager."""
    
    def __init__(self):
        """Initialize Redis manager."""
        self.client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Initialize Redis connection."""
        try:
            log.info(f"Connecting to Redis: {settings.redis_host}:{settings.redis_port}")
            
            self.client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password if settings.redis_password else None,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True
            )
            
            # Test connection
            await self.client.ping()
            log.info("Successfully connected to Redis")
            
        except Exception as e:
            log.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def close(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            log.info("Redis connection closed")
    
    def get_client(self) -> redis.Redis:
        """
        Get Redis client instance.
        
        Returns:
            Redis client instance
            
        Raises:
            RuntimeError: If Redis is not initialized
        """
        if self.client is None:
            raise RuntimeError("Redis not initialized. Call connect() first.")
        return self.client


# Global Redis instance
redis_client = RedisClient()


async def init_redis():
    """Initialize Redis connection."""
    await redis_client.connect()


async def close_redis():
    """Close Redis connection."""
    await redis_client.close()


def get_redis() -> redis.Redis:
    """Get Redis client instance."""
    return redis_client.get_client()
