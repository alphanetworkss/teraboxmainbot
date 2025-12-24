"""
FFmpeg download helper.
Downloads M3U8 streams using ffmpeg with stream copy (no re-encode).
"""
import asyncio
import re
from pathlib import Path
from typing import Optional, Callable
from config.settings import settings
from config.constants import FFMPEG_TIMEOUT
from utils.logger import log


class FFmpegHelper:
    """FFmpeg download manager."""
    
    def __init__(self, max_concurrent: int = None):
        """
        Initialize FFmpeg helper.
        
        Args:
            max_concurrent: Maximum concurrent ffmpeg processes
        """
        self.max_concurrent = max_concurrent or settings.max_concurrent_downloads
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
    
    async def download_m3u8(
        self,
        m3u8_url: str,
        output_path: Path | str,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> Optional[Path]:
        """
        Download M3U8 stream using ffmpeg.
        
        Uses stream copy (no re-encoding) for maximum speed and quality.
        Command: ffmpeg -i {m3u8_url} -c copy -bsf:a aac_adtstoasc {output_path}
        
        Args:
            m3u8_url: M3U8 stream URL
            output_path: Output file path
            progress_callback: Optional callback for progress updates (0-100)
            
        Returns:
            Path to downloaded file if successful, None otherwise
        """
        async with self.semaphore:
            try:
                output_path = Path(output_path)
                
                log.info(f"Starting ffmpeg download: {m3u8_url} -> {output_path}")
                
                # FFmpeg command with optimized settings
                cmd = [
                    'ffmpeg',
                    '-y',  # Overwrite output file
                    '-threads', '2',  # Reduced threads for stability
                    '-user_agent', 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36',
                    '-i', m3u8_url,
                    '-c', 'copy',  # Stream copy (no re-encode)
                    '-bsf:a', 'aac_adtstoasc',  # Fix AAC bitstream
                    '-movflags', '+faststart',  # Enable fast start for streaming
                    '-progress', 'pipe:1',  # Output progress to stdout
                    '-loglevel', 'error',  # Only show errors
                    '-timeout', '30000000',  # Increase timeout (30 seconds in microseconds)
                    str(output_path)
                ]
                
                # Start ffmpeg process
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # Monitor progress from stderr
                duration = None
                
                async def read_stderr():
                    nonlocal duration
                    while True:
                        line = await process.stderr.readline()
                        if not line:
                            break
                        
                        line = line.decode('utf-8', errors='ignore').strip()
                        
                        # Extract duration
                        if duration is None and 'Duration:' in line:
                            duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})', line)
                            if duration_match:
                                h, m, s = map(int, duration_match.groups())
                                duration = h * 3600 + m * 60 + s
                                log.debug(f"Video duration: {duration}s")
                        
                        # Extract progress
                        if duration and 'time=' in line:
                            time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})', line)
                            if time_match:
                                h, m, s = map(int, time_match.groups())
                                current_time = h * 3600 + m * 60 + s
                                progress = int((current_time / duration) * 100)
                                
                                if progress_callback:
                                    try:
                                        await progress_callback(min(progress, 100))
                                    except Exception as e:
                                        log.error(f"Error in progress callback: {e}")
                
                # Read stderr in background
                stderr_task = asyncio.create_task(read_stderr())
                
                # Wait for process to complete with timeout
                try:
                    await asyncio.wait_for(process.wait(), timeout=FFMPEG_TIMEOUT)
                except asyncio.TimeoutError:
                    log.error(f"FFmpeg timeout after {FFMPEG_TIMEOUT}s")
                    process.kill()
                    await process.wait()
                    return None
                
                # Wait for stderr reading to complete
                await stderr_task
                
                # Check exit code
                if process.returncode == 0:
                    log.info(f"FFmpeg download completed: {output_path}")
                    
                    # Verify file exists
                    if output_path.exists():
                        file_size = output_path.stat().st_size
                        log.info(f"Downloaded file size: {file_size / (1024*1024):.2f} MB")
                        return output_path
                    else:
                        log.error("FFmpeg completed but output file not found")
                        return None
                else:
                    log.error(f"FFmpeg failed with exit code: {process.returncode}")
                    return None
                    
            except Exception as e:
                log.error(f"Error downloading M3U8 with ffmpeg: {e}")
                return None


# Global FFmpeg helper instance
ffmpeg_helper = FFmpegHelper()
