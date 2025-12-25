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
    """FFmpeg download manager with real-time progress tracking."""
    
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
        progress_callback: Optional[Callable] = None
    ) -> Optional[Path]:
        """
        Download M3U8 stream using ffmpeg with real-time progress tracking.
        
        Uses stream copy (no re-encoding) for maximum speed and quality.
        Parses ffmpeg -progress pipe:1 output for accurate progress tracking.
        
        Args:
            m3u8_url: M3U8 stream URL
            output_path: Output file path
            progress_callback: Optional async callback(progress_data: dict)
                              progress_data contains: percentage, speed, eta, current_time, total_duration
            
        Returns:
            Path to downloaded file if successful, None otherwise
        """
        async with self.semaphore:
            try:
                output_path = Path(output_path)
                
                log.info(f"Starting ffmpeg download: {m3u8_url} -> {output_path}")
                
                # FFmpeg command with progress output to stdout
                cmd = [
                    'ffmpeg',
                    '-y',  # Overwrite output file
                    '-threads', '2',  # Reduced threads for stability
                    '-user_agent', 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36',
                    '-i', m3u8_url,
                    '-c', 'copy',  # Stream copy (no re-encode)
                    '-bsf:a', 'aac_adtstoasc',  # Fix AAC bitstream
                    '-movflags', '+faststart',  # Enable fast start for streaming
                    '-progress', 'pipe:1',  # Output progress to stdout (CRITICAL)
                    '-nostats',  # Disable stats output
                    '-loglevel', 'info',  # Changed from 'error' to get duration info
                    str(output_path)
                ]
                
                # Start ffmpeg process
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # Track duration and progress
                duration = None
                last_progress_data = {}
                download_start_time = None
                last_bytes = 0
                
                async def read_stderr():
                    """Read stderr to extract duration."""
                    nonlocal duration
                    while True:
                        line = await process.stderr.readline()
                        if not line:
                            break
                        
                        line = line.decode('utf-8', errors='ignore').strip()
                        
                        # Extract duration from initial ffmpeg output
                        if duration is None and 'Duration:' in line:
                            from utils.progress_tracker import ffmpeg_parser
                            parsed_duration = ffmpeg_parser.parse_duration(line)
                            if parsed_duration:
                                duration = parsed_duration
                                log.info(f"[FFMPEG] Detected duration: {duration:.2f}s")
                
                async def read_stdout():
                    """Read stdout to parse progress output."""
                    nonlocal last_progress_data, download_start_time, last_bytes
                    
                    from utils.progress_tracker import ffmpeg_parser
                    import time
                    
                    progress_data = {}
                    
                    while True:
                        line = await process.stdout.readline()
                        if not line:
                            break
                        
                        line = line.decode('utf-8', errors='ignore').strip()
                        
                        if not line:
                            continue
                        
                        # Parse key=value format from -progress pipe:1
                        parsed = ffmpeg_parser.parse_progress_line(line)
                        progress_data.update(parsed)
                        
                        # When we get 'progress=continue' or 'progress=end', we have a complete frame
                        if 'progress' in parsed:
                            if duration and 'out_time_ms' in progress_data:
                                try:
                                    out_time_ms = int(progress_data.get('out_time_ms', 0))
                                    speed = progress_data.get('speed', '1.0x')
                                    total_size = int(progress_data.get('total_size', 0))
                                    
                                    # Initialize start time on first progress
                                    if download_start_time is None:
                                        download_start_time = time.time()
                                    
                                    # Calculate download speed in MB/s
                                    elapsed = time.time() - download_start_time
                                    download_speed_mbps = "Calculating..."
                                    if elapsed > 0 and total_size > 0:
                                        bytes_diff = total_size - last_bytes
                                        if bytes_diff > 0:
                                            speed_bps = total_size / elapsed
                                            download_speed_mbps = f"{speed_bps / (1024 * 1024):.1f} MB/s"
                                        last_bytes = total_size
                                    
                                    # Calculate progress using utility
                                    calc_progress = ffmpeg_parser.calculate_progress(
                                        out_time_ms=out_time_ms,
                                        total_duration=duration,
                                        speed=speed
                                    )
                                    
                                    # Store for callback
                                    last_progress_data = {
                                        'percentage': calc_progress.percentage,
                                        'speed': calc_progress.speed,
                                        'download_speed': download_speed_mbps,
                                        'eta': calc_progress.eta,
                                        'current_time': calc_progress.current_time,
                                        'total_duration': calc_progress.total_duration
                                    }
                                    
                                    # Call progress callback
                                    if progress_callback:
                                        try:
                                            await progress_callback(last_progress_data)
                                        except Exception as e:
                                            log.error(f"Error in progress callback: {e}")
                                
                                except (ValueError, TypeError) as e:
                                    log.debug(f"Error parsing progress data: {e}")
                            
                            # Reset for next frame
                            progress_data = {}
                
                # Read both streams concurrently
                stderr_task = asyncio.create_task(read_stderr())
                stdout_task = asyncio.create_task(read_stdout())
                
                # Wait for process to complete with timeout
                try:
                    await asyncio.wait_for(process.wait(), timeout=FFMPEG_TIMEOUT)
                except asyncio.TimeoutError:
                    log.error(f"FFmpeg timeout after {FFMPEG_TIMEOUT}s")
                    process.kill()
                    await process.wait()
                    return None
                
                # Wait for stream reading to complete
                await asyncio.gather(stderr_task, stdout_task, return_exceptions=True)
                
                # Check exit code
                if process.returncode == 0:
                    log.info(f"FFmpeg download completed: {output_path}")
                    
                    # Verify file exists
                    if output_path.exists():
                        file_size = output_path.stat().st_size
                        log.info(f"Downloaded file size: {file_size / (1024*1024):.2f} MB")
                        
                        # Send final 100% progress
                        if progress_callback and duration:
                            try:
                                await progress_callback({
                                    'percentage': 100.0,
                                    'speed': last_progress_data.get('speed', '1.0x'),
                                    'download_speed': last_progress_data.get('download_speed', 'N/A'),
                                    'eta': '00:00',
                                    'current_time': duration,
                                    'total_duration': duration
                                })
                            except Exception as e:
                                log.error(f"Error in final progress callback: {e}")
                        
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
