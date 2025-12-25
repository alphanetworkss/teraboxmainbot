"""
Progress tracking utilities for download and upload operations.
Provides ffmpeg progress parsing, progress bars, rate limiting, and structured logging.
"""
import asyncio
import time
import re
from typing import Dict, Optional, Callable
from dataclasses import dataclass
from utils.logger import log


@dataclass
class ProgressData:
    """Progress data structure."""
    percentage: float
    speed: str
    eta: str
    current_time: float
    total_duration: float
    out_time_ms: int = 0


class FFmpegProgressParser:
    """Parser for ffmpeg -progress pipe:1 output."""
    
    @staticmethod
    def parse_duration(line: str) -> Optional[float]:
        """
        Parse duration from ffmpeg stderr output.
        
        Format: Duration: HH:MM:SS.ms
        
        Args:
            line: Line from ffmpeg stderr
            
        Returns:
            Duration in seconds, or None if not found
        """
        duration_match = re.search(r'Duration:\s*(\d{2}):(\d{2}):(\d{2})\.(\d{2})', line)
        if duration_match:
            h, m, s, ms = map(int, duration_match.groups())
            total_seconds = h * 3600 + m * 60 + s + ms / 100.0
            return total_seconds
        return None
    
    @staticmethod
    def parse_progress_line(line: str) -> Dict[str, str]:
        """
        Parse a single line from ffmpeg progress output.
        
        Format: key=value
        
        Args:
            line: Single line from progress output
            
        Returns:
            Dictionary with key-value pair
        """
        if '=' in line:
            key, value = line.split('=', 1)
            return {key.strip(): value.strip()}
        return {}
    
    @staticmethod
    def calculate_progress(
        out_time_ms: int,
        total_duration: float,
        speed: str = "1.0x"
    ) -> ProgressData:
        """
        Calculate progress data from ffmpeg output.
        
        Args:
            out_time_ms: Current time in microseconds from ffmpeg
            total_duration: Total video duration in seconds
            speed: Processing speed (e.g., "2.3x")
            
        Returns:
            ProgressData object with calculated values
        """
        # Convert microseconds to seconds
        current_time = out_time_ms / 1_000_000.0
        
        # Calculate percentage
        if total_duration > 0:
            percentage = min(100.0, (current_time / total_duration) * 100.0)
        else:
            percentage = 0.0
        
        # Calculate ETA
        eta_str = "Calculating..."
        if total_duration > 0 and current_time > 0:
            remaining_time = total_duration - current_time
            
            # Extract speed multiplier
            speed_match = re.search(r'([\d.]+)x?', speed)
            if speed_match:
                speed_multiplier = float(speed_match.group(1))
                if speed_multiplier > 0:
                    eta_seconds = remaining_time / speed_multiplier
                    eta_str = format_time(eta_seconds)
        
        return ProgressData(
            percentage=percentage,
            speed=speed,
            eta=eta_str,
            current_time=current_time,
            total_duration=total_duration,
            out_time_ms=out_time_ms
        )


class ProgressBarGenerator:
    """Generate visual progress bars."""
    
    @staticmethod
    def generate(percentage: float, length: int = 15) -> str:
        """
        Generate a progress bar using ⬢ and ⬡ characters.
        
        Args:
            percentage: Progress percentage (0-100)
            length: Total length of progress bar
            
        Returns:
            Progress bar string
        """
        # Clamp percentage to 0-100
        percentage = max(0.0, min(100.0, percentage))
        
        # Calculate filled blocks
        filled = int((percentage / 100.0) * length)
        empty = length - filled
        
        return "⬢" * filled + "⬡" * empty


class MessageRateLimiter:
    """Rate limiter for Telegram message updates."""
    
    def __init__(self, min_interval: float = 3.0):
        """
        Initialize rate limiter.
        
        Args:
            min_interval: Minimum seconds between updates
        """
        self.min_interval = min_interval
        self.last_update: Dict[str, float] = {}
        self.lock = asyncio.Lock()
    
    async def should_update(self, job_id: str) -> bool:
        """
        Check if enough time has passed to update message.
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            True if update should proceed, False otherwise
        """
        async with self.lock:
            current_time = time.time()
            last_time = self.last_update.get(job_id, 0)
            
            if current_time - last_time >= self.min_interval:
                self.last_update[job_id] = current_time
                return True
            return False
    
    async def force_update(self, job_id: str):
        """
        Force update timestamp (for completion messages).
        
        Args:
            job_id: Unique job identifier
        """
        async with self.lock:
            self.last_update[job_id] = time.time()
    
    def reset(self, job_id: str):
        """
        Reset rate limiter for a job.
        
        Args:
            job_id: Unique job identifier
        """
        if job_id in self.last_update:
            del self.last_update[job_id]


class ProgressLogger:
    """Structured logger for progress tracking."""
    
    @staticmethod
    def log_download_start(job_id: str, m3u8_url: str):
        """Log download start."""
        log.info(f"[DOWNLOAD] START | job_id={job_id[:16]} | url={m3u8_url[:50]}...")
    
    @staticmethod
    def log_download_progress(job_id: str, percentage: float, speed: str, eta: str):
        """Log download progress."""
        log.info(f"[DOWNLOAD] {percentage:.1f}% | speed={speed} | eta={eta} | job_id={job_id[:16]}")
    
    @staticmethod
    def log_download_complete(job_id: str, duration: float, file_size: int):
        """Log download completion."""
        size_mb = file_size / (1024 * 1024)
        log.info(f"[DOWNLOAD] COMPLETE | {duration:.1f}s | {size_mb:.2f}MB | job_id={job_id[:16]}")
    
    @staticmethod
    def log_download_error(job_id: str, error: str):
        """Log download error."""
        log.error(f"[DOWNLOAD] ERROR | {error} | job_id={job_id[:16]}")
    
    @staticmethod
    def log_upload_start(job_id: str, bot_index: int, file_size: int):
        """Log upload start."""
        size_mb = file_size / (1024 * 1024)
        log.info(f"[UPLOAD] START | {size_mb:.2f}MB | bot={bot_index} | job_id={job_id[:16]}")
    
    @staticmethod
    def log_upload_progress(job_id: str, percentage: float, current_mb: float, total_mb: float, bot_index: int):
        """Log upload progress."""
        log.info(f"[UPLOAD] {percentage:.1f}% | {current_mb:.1f}MB/{total_mb:.1f}MB | bot={bot_index} | job_id={job_id[:16]}")
    
    @staticmethod
    def log_upload_complete(job_id: str, duration: float, bot_index: int, file_size: int):
        """Log upload completion."""
        size_mb = file_size / (1024 * 1024)
        avg_speed = (file_size / duration) / (1024 * 1024) if duration > 0 else 0
        log.info(f"[UPLOAD] COMPLETE | {duration:.1f}s | {avg_speed:.2f}MB/s | bot={bot_index} | job_id={job_id[:16]}")
    
    @staticmethod
    def log_upload_error(job_id: str, error: str, bot_index: int):
        """Log upload error."""
        log.error(f"[UPLOAD] ERROR | {error} | bot={bot_index} | job_id={job_id[:16]}")


def format_time(seconds: float) -> str:
    """
    Format seconds to human readable time.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted time string (HH:MM:SS or MM:SS)
    """
    if seconds < 0:
        return "00:00"
    
    seconds = int(seconds)
    
    if seconds < 60:
        return f"00:{seconds:02d}"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_bytes(bytes_val: int) -> str:
    """
    Format bytes to human readable format.
    
    Args:
        bytes_val: Size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"


# Global instances
rate_limiter = MessageRateLimiter(min_interval=3.0)
progress_logger = ProgressLogger()
ffmpeg_parser = FFmpegProgressParser()
progress_bar = ProgressBarGenerator()
