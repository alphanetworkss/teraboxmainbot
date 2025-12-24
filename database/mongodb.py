"""
MongoDB connection manager.
Handles async MongoDB connection using motor.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config.settings import settings
from utils.logger import log


class MongoDB:
    """MongoDB connection manager."""
    
    def __init__(self):
        """Initialize MongoDB manager."""
        self.client: AsyncIOMotorClient | None = None
        self.db: AsyncIOMotorDatabase | None = None
    
    async def connect(self):
        """Initialize MongoDB connection."""
        try:
            log.info(f"Connecting to MongoDB: {settings.mongodb_uri}")
            self.client = AsyncIOMotorClient(settings.mongodb_uri)
            self.db = self.client[settings.mongodb_db_name]
            
            # Test connection
            await self.client.admin.command('ping')
            log.info(f"Successfully connected to MongoDB database: {settings.mongodb_db_name}")
            
        except Exception as e:
            log.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            log.info("MongoDB connection closed")
    
    def get_database(self) -> AsyncIOMotorDatabase:
        """
        Get database instance.
        
        Returns:
            AsyncIOMotorDatabase instance
            
        Raises:
            RuntimeError: If database is not initialized
        """
        if self.db is None:
            raise RuntimeError("Database not initialized. Call connect() first.")
        return self.db


# Global MongoDB instance
mongodb = MongoDB()


async def init_db():
    """Initialize database connection."""
    await mongodb.connect()


async def close_db():
    """Close database connection."""
    await mongodb.close()


def get_database() -> AsyncIOMotorDatabase:
    """Get database instance."""
    return mongodb.get_database()
