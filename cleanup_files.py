"""
MongoDB models for video records.
Handles duplicate detection and message ID storage.
"""
import hashlib
from datetime import datetime
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorCollection
from database.mongodb import get_database
from utils.logger import log


class VideoRecord:
    """Video record model for MongoDB."""
    
    COLLECTION_NAME = "videos"
    
    def __init__(self):
        """Initialize video record model."""
        self._collection: Optional[AsyncIOMotorCollection] = None
    
    @property
    def collection(self) -> AsyncIOMotorCollection:
        """Get videos collection."""
        if self._collection is None:
            db = get_database()
            self._collection = db[self.COLLECTION_NAME]
        return self._collection
    
    async def create_indexes(self):
        """Create database indexes for optimization."""
        try:
            # Create unique index on link_hash
            await self.collection.create_index("link_hash", unique=True)
            
            # Create index on created_at for cleanup queries
            await self.collection.create_index("created_at")
            
            log.info("Database indexes created successfully")
        except Exception as e:
            log.error(f"Error creating indexes: {e}")
    
    @staticmethod
    def hash_link(link: str) -> str:
        """
        Generate SHA256 hash of the link.
        
        Args:
            link: TeraBox link
            
        Returns:
            SHA256 hash string
        """
        return hashlib.sha256(link.encode()).hexdigest()
    
    async def find_by_hash(self, link_hash: str) -> Optional[dict]:
        """
        Find video record by link hash.
        
        Args:
            link_hash: SHA256 hash of the link
            
        Returns:
            Video record dict if found, None otherwise
        """
        try:
            record = await self.collection.find_one({"link_hash": link_hash})
            if record:
                log.debug(f"Found existing video record for hash: {link_hash}")
            return record
        except Exception as e:
            log.error(f"Error finding video by hash {link_hash}: {e}")
            return None
    
    async def save_video(
        self,
        link: str,
        link_hash: str,
        channel_message_id: int,
        file_id: str,
        file_size: int
    ) -> bool:
        """
        Save new video record to database.
        
        Args:
            link: Original TeraBox link
            link_hash: SHA256 hash of the link
            channel_message_id: Message ID in log channel
            file_id: Telegram file ID
            file_size: File size in bytes
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            document = {
                "link_hash": link_hash,
                "original_link": link,
                "channel_message_id": channel_message_id,
                "file_id": file_id,
                "file_size": file_size,
                "created_at": datetime.utcnow()
            }
            
            await self.collection.insert_one(document)
            log.info(f"Saved video record: hash={link_hash}, msg_id={channel_message_id}")
            return True
            
        except Exception as e:
            # Check if it's a duplicate key error (E11000)
            error_str = str(e)
            if 'E11000' in error_str or 'duplicate key' in error_str.lower():
                # This is expected when same link is processed simultaneously
                log.warning(f"Duplicate video record (race condition): hash={link_hash}")
                return True  # Still return True since video is already saved
            else:
                # Actual error
                log.error(f"Error saving video record: {e}")
                return False
    
    async def get_message_id(self, link_hash: str) -> Optional[int]:
        """
        Get channel message ID for a link hash.
        
        Args:
            link_hash: SHA256 hash of the link
            
        Returns:
            Channel message ID if found, None otherwise
        """
        try:
            record = await self.find_by_hash(link_hash)
            if record:
                return record.get("channel_message_id")
            return None
        except Exception as e:
            log.error(f"Error getting message ID for hash {link_hash}: {e}")
            return None
    
    async def get_file_id(self, link_hash: str) -> Optional[str]:
        """
        Get Telegram file ID for a link hash.
        
        Args:
            link_hash: SHA256 hash of the link
            
        Returns:
            Telegram file ID if found, None otherwise
        """
        try:
            record = await self.find_by_hash(link_hash)
            if record:
                return record.get("file_id")
            return None
        except Exception as e:
            log.error(f"Error getting file ID for hash {link_hash}: {e}")
            return None
    
    async def delete_by_hash(self, link_hash: str) -> bool:
        """
        Delete video record by hash (for cleanup/admin).
        
        Args:
            link_hash: SHA256 hash of the link
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            result = await self.collection.delete_one({"link_hash": link_hash})
            if result.deleted_count > 0:
                log.info(f"Deleted video record: hash={link_hash}")
                return True
            return False
        except Exception as e:
            log.error(f"Error deleting video record: {e}")
            return False


# Global video record instance
video_record = VideoRecord()
