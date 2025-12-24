"""
File management utilities.
Handles temporary file creation, cleanup, and orphaned file removal.
"""
import os
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from config.settings import settings
from config.constants import TEMP_FILE_PREFIX, VIDEO_EXTENSION
from utils.logger import log


class FileManager:
    """Manages temporary file operations."""
    
    def __init__(self):
        """Initialize file manager and create download directory."""
        self.download_dir = Path(settings.download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_temp_file(self, link_hash: str) -> Path:
        """
        Create a unique temporary file path for download.
        
        Args:
            link_hash: SHA256 hash of the TeraBox link
            
        Returns:
            Path object for the temporary file
        """
        filename = f"{TEMP_FILE_PREFIX}{link_hash}{VIDEO_EXTENSION}"
        file_path = self.download_dir / filename
        
        log.debug(f"Created temp file path: {file_path}")
        return file_path
    
    async def cleanup_file(self, file_path: Path | str) -> bool:
        """
        Delete a file after upload.
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            file_path = Path(file_path)
            if file_path.exists():
                file_path.unlink()
                log.info(f"Deleted file: {file_path}")
                return True
            else:
                log.warning(f"File not found for cleanup: {file_path}")
                return False
        except Exception as e:
            log.error(f"Error deleting file {file_path}: {e}")
            return False
    
    async def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up orphaned files older than specified hours.
        
        Args:
            max_age_hours: Maximum age of files to keep (default: 24 hours)
            
        Returns:
            Number of files deleted
        """
        try:
            deleted_count = 0
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            for file_path in self.download_dir.glob(f"{TEMP_FILE_PREFIX}*{VIDEO_EXTENSION}"):
                try:
                    # Get file modification time
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if file_mtime < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
                        log.info(f"Deleted orphaned file: {file_path}")
                except Exception as e:
                    log.error(f"Error deleting orphaned file {file_path}: {e}")
            
            if deleted_count > 0:
                log.info(f"Cleanup completed: {deleted_count} orphaned files deleted")
            
            return deleted_count
            
        except Exception as e:
            log.error(f"Error during cleanup: {e}")
            return 0
    
    async def get_file_size(self, file_path: Path | str) -> int:
        """
        Get file size in bytes.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File size in bytes, or 0 if file doesn't exist
        """
        try:
            file_path = Path(file_path)
            if file_path.exists():
                return file_path.stat().st_size
            return 0
        except Exception as e:
            log.error(f"Error getting file size for {file_path}: {e}")
            return 0


# Global file manager instance
file_manager = FileManager()
