"""
Worker server.
Consumes download jobs from Redis queue and processes them.
"""
import asyncio
import signal
import aiohttp
from typing import Dict, Any
from pathlib import Path
from config.settings import settings
from config.constants import (
    ERROR_DOWNLOAD_FAILED,
    ERROR_UPLOAD_FAILED,
    MSG_DOWNLOADING,
    MSG_UPLOADING,
    MSG_SUCCESS
)
from database import init_db, close_db
from database.models import video_record
from redis_queue import init_redis, close_redis, job_queue
from downloader import m3u8_parser, ffmpeg_helper
from uploader import multi_bot_manager, telegram_uploader
from utils import log, setup_logger, file_manager
from utils.progress_tracker import (
    rate_limiter,
    progress_logger,
    progress_bar,
    format_time,
    format_bytes
)
from aiogram import Bot


# Worker state
stop_event = asyncio.Event()
worker_bot: Bot = None


async def fetch_m3u8_from_api(link: str) -> tuple[str, dict] | tuple[None, None]:
    """
    Fetch M3U8 URL and file metadata from Starbots TeraBox API.
    
    API Response Format:
    {
        "errno": 0,
        "data": {
            "file": {
                "file_name": "...",
                "stream_url": "http://api.starbots.in/play/i/...",
                "thumb": "https://...",
                "duration": "01:09:15",
                "quality": "720p",
                "size": 123456,
                "size_readable": "393.83 MB"
            }
        }
    }
    
    Args:
        link: TeraBox link
        
    Returns:
        Tuple of (stream_url, file_metadata) if successful, (None, None) otherwise
        file_metadata contains: file_name, duration, quality, thumb, size_readable
    """
    try:
        log.info(f"Fetching M3U8 URL from Starbots API: {link}")
        
        # Call Starbots API
        async with aiohttp.ClientSession() as session:
            params = {'url': link}
            
            async with session.get(
                settings.terabox_api_url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Check if API returned success
                    if data.get('errno') == 0:
                        # Extract file data
                        file_data = data.get('data', {}).get('file', {})
                        stream_url = file_data.get('stream_url')
                        
                        if stream_url:
                            log.info(f"Got M3U8 URL from Starbots API: {stream_url}")
                            
                            # Extract file metadata
                            file_metadata = {
                                'file_name': file_data.get('file_name', 'Unknown'),
                                'duration': file_data.get('duration', 'N/A'),
                                'quality': file_data.get('quality', 'N/A'),
                                'thumb': file_data.get('thumb', ''),
                                'size_readable': file_data.get('size_readable', 'N/A')
                            }
                            
                            log.info(f"File metadata: {file_metadata['file_name']} | {file_metadata['duration']} | {file_metadata['quality']}")
                            
                            return stream_url, file_metadata
                        else:
                            log.error(f"No stream_url in API response: {data}")
                            return None, None
                    else:
                        log.error(f"API returned error: errno={data.get('errno')}, data={data}")
                        return None, None
                else:
                    log.error(f"API request failed: status={response.status}")
                    return None, None
                    
    except Exception as e:
        log.error(f"Error fetching M3U8 from Starbots API: {e}")
        return None, None


async def send_progress_message(chat_id: int, message_id: int, text: str):
    """Send progress update to user."""
    try:
        await worker_bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text
        )
    except Exception as e:
        log.debug(f"Could not update progress message: {e}")



async def delete_progress_message(chat_id: int, message_id: int):
    """
    Delete progress message from user chat.
    
    Args:
        chat_id: User chat ID
        message_id: Progress message ID to delete
    """
    try:
        await worker_bot.delete_message(chat_id, message_id)
        log.info(f"[USER] PROGRESS_MSG_DELETED | chat_id={chat_id} | msg_id={message_id}")
    except Exception as e:
        # Message may already be deleted by user - this is OK
        log.debug(f"Could not delete progress message {message_id}: {e}")


async def cleanup_user_messages(chat_id: int, progress_msg_id: int = None, cache_msg_id: int = None):
    """
    Clean up temporary messages from user chat.
    
    Args:
        chat_id: User chat ID
        progress_msg_id: Progress message ID (optional)
        cache_msg_id: Cached video info message ID (optional)
    """
    if progress_msg_id:
        await delete_progress_message(chat_id, progress_msg_id)
    
    if cache_msg_id:
        try:
            await worker_bot.delete_message(chat_id, cache_msg_id)
            log.info(f"[USER] CACHE_MSG_DELETED | chat_id={chat_id} | msg_id={cache_msg_id}")
        except Exception as e:
            log.debug(f"Could not delete cache message {cache_msg_id}: {e}")


def schedule_video_auto_delete(chat_id: int, message_id: int, delay: int = 3600):
    """
    Schedule auto-deletion of video message from user chat (NOT channel).
    
    Args:
        chat_id: User chat ID
        message_id: Video message ID to delete
        delay: Delay in seconds (default 3600 = 1 hour)
    """
    async def delete_after_delay():
        try:
            log.info(
                f"[USER] AUTO_DELETE_SCHEDULED | "
                f"chat_id={chat_id} | "
                f"msg_id={message_id} | "
                f"in={delay}s"
            )
            
            await asyncio.sleep(delay)
            
            await worker_bot.delete_message(chat_id, message_id)
            
            log.info(f"[USER] AUTO_DELETE_DONE | chat_id={chat_id} | msg_id={message_id}")
        except Exception as e:
            # Silent failure - user may have deleted manually
            log.debug(f"Could not auto-delete video {message_id}: {e}")
    
    # Create background task (non-blocking)
    asyncio.create_task(delete_after_delay())


# Removed: progress_bar, format_bytes, format_time now imported from utils.progress_tracker


async def process_job(job_data: Dict[str, Any]):
    """
    Process a download job.
    
    Args:
        job_data: Job data from queue
    """
    link = job_data['link']
    user_id = job_data['user_id']
    chat_id = job_data['chat_id']
    message_id = job_data['message_id']
    link_hash = job_data['link_hash']
    
    log.info(f"Processing job: user_id={user_id}, hash={link_hash}")
    
    file_path = None
    
    try:
        # Step 1: Fetch M3U8 URL and file metadata from API
        m3u8_url, file_metadata = await fetch_m3u8_from_api(link)
        
        if not m3u8_url:
            await worker_bot.send_message(chat_id, ERROR_DOWNLOAD_FAILED)
            return
        
        # Store file metadata in job_data for use in progress messages and upload
        job_data['file_metadata'] = file_metadata
        
        # Step 2: Parse M3U8 and get best quality
        best_quality_url = await m3u8_parser.get_best_quality(m3u8_url)
        
        if not best_quality_url:
            await worker_bot.send_message(chat_id, ERROR_DOWNLOAD_FAILED)
            return
        
        # Use processing message ID from main bot
        progress_message_id = job_data.get('processing_message_id', message_id)
        
        # Step 3: Create temp file path
        file_path = await file_manager.create_temp_file(link_hash)
        
        # Step 4: Download video with ffmpeg
        log.info(f"Downloading video: {best_quality_url}")
        
        # Log download start
        progress_logger.log_download_start(link_hash, best_quality_url)
        
        # Progress tracking for download
        import time
        download_start_time = time.time()
        last_logged_milestone = [0]  # Track logging milestones (25%, 50%, 75%)
        
        async def download_progress(progress_data: dict):
            """Enhanced download progress with real ffmpeg data."""
            percentage = progress_data.get('percentage', 0)
            download_speed = progress_data.get('download_speed', 'Calculating...')
            eta = progress_data.get('eta', 'Calculating...')
            
            # Rate limiting for Telegram message updates
            if not await rate_limiter.should_update(link_hash):
                return
            
            # Create progress bar (10 chars as shown in example)
            bar = progress_bar.generate(percentage, length=10)
            
            # Get file metadata
            file_name = file_metadata.get('file_name', 'Unknown')
            duration = file_metadata.get('duration', 'N/A')
            quality = file_metadata.get('quality', 'N/A')
            size_readable = file_metadata.get('size_readable', 'N/A')
            
            # Format message with file metadata and download speed in MB/s
            progress_text = (
                "📥 **Download Progress**\n\n"
                f"🎬 File: {file_name}\n"
                f"⏱ Duration: {duration}\n"
                f"🎞 Quality: {quality}\n\n"
                "━━━━━━━━━━━━━━\n"
                f"{bar} {percentage:.1f}%\n"
                "━━━━━━━━━━━━━━\n\n"
                f"📦 Size: {size_readable}\n"
                f"🚀 Speed: {download_speed}\n"
                f"⏱️ ETA: {eta}"
            )
            
            await send_progress_message(chat_id, progress_message_id, progress_text)
            
            # Structured logging at milestones
            current_milestone = int(percentage // 25) * 25
            if current_milestone > last_logged_milestone[0] and current_milestone > 0:
                progress_logger.log_download_progress(link_hash, percentage, download_speed, eta)
                last_logged_milestone[0] = current_milestone
        
        # Send initial download message
        await send_progress_message(
            chat_id,
            progress_message_id,
            "📥 **Downloading (Stream → MP4)**\n\n"
            "╭━━━━❰Progress❱━━━━➣\n"
            f"┣⪼ [{progress_bar.generate(0, 10)}] 0%\n"
            "┣⪼ 🚀 Speed: Initializing...\n"
            "┣⪼ ⏱️ ETA: Calculating...\n"
            "╰━━━━━━━━━━━━━━━➣"
        )
        
        downloaded_file = await ffmpeg_helper.download_m3u8(
            m3u8_url=best_quality_url,
            output_path=file_path,
            progress_callback=download_progress
        )
        
        if not downloaded_file:
            progress_logger.log_download_error(link_hash, "Download failed")
            await worker_bot.send_message(chat_id, ERROR_DOWNLOAD_FAILED)
            return
        
        # Log download completion
        download_duration = time.time() - download_start_time
        file_size = downloaded_file.stat().st_size
        progress_logger.log_download_complete(link_hash, download_duration, file_size)
        
        log.info(f"Download completed: {downloaded_file}")
        
        # Step 4.5: Embed thumbnail into video (if available)
        thumb_url = file_metadata.get('thumb', '')
        thumb_path = None
        original_video = downloaded_file
        
        if thumb_url:
            try:
                # Import thumbnail helper
                from downloader.thumbnail_helper import download_thumbnail
                
                # Create temp paths
                thumb_path = file_path.parent / f"thumb_{link_hash}.jpg"
                video_with_thumb = file_path.parent / f"final_{link_hash}{downloaded_file.suffix}"
                
                # Download thumbnail
                log.info(f"[THUMB] Starting thumbnail download")
                downloaded_thumb = await download_thumbnail(thumb_url, thumb_path)
                
                if downloaded_thumb:
                    # Embed thumbnail into video
                    log.info(f"[THUMB] Starting thumbnail embedding")
                    final_video = await ffmpeg_helper.embed_thumbnail(
                        video_path=downloaded_file,
                        thumb_path=downloaded_thumb,
                        output_path=video_with_thumb
                    )
                    
                    if final_video and final_video.exists():
                        # Success - use video with embedded thumbnail
                        downloaded_file = final_video
                        log.info(f"[THUMB] SUCCESS | Using video with embedded thumbnail")
                    else:
                        log.warning(f"[THUMB] FALLBACK | Embedding failed, using original video")
                else:
                    log.warning(f"[THUMB] FALLBACK | Thumbnail download failed, using original video")
                    
            except Exception as e:
                log.error(f"[THUMB] ERROR | {type(e).__name__}: {e} | Using original video")
        else:
            log.info(f"[THUMB] SKIP | No thumbnail URL provided")
        
        # Step 5: Upload to Telegram
        log.info(f"Uploading video to Telegram")
        
        # Progress tracking for upload
        upload_start_time = time.time()
        last_upload_milestone = [0]
        upload_job_id = f"{link_hash}_upload"
        
        async def upload_progress(current: int, total: int):
            """Enhanced upload progress with speed and ETA."""
            # Rate limiting for Telegram message updates
            if not await rate_limiter.should_update(upload_job_id):
                return
            
            # Calculate progress
            percent = (current / total * 100) if total > 0 else 0
            bar = progress_bar.generate(percent, length=10)
            
            # Calculate speed
            current_time = time.time()
            time_diff = current_time - upload_start_time
            if time_diff > 0:
                speed_bps = current / time_diff
                speed = f"{format_bytes(speed_bps)}/s"
                
                # Calculate ETA
                if speed_bps > 0 and total > current:
                    remaining_bytes = total - current
                    eta_seconds = remaining_bytes / speed_bps
                    eta = format_time(eta_seconds)
                else:
                    eta = "Finishing..."
            else:
                speed = "Calculating..."
                eta = "Calculating..."
            
            # Format bytes
            current_mb = current / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            
            # Get file metadata
            file_name = file_metadata.get('file_name', 'Unknown')
            duration = file_metadata.get('duration', 'N/A')
            quality = file_metadata.get('quality', 'N/A')
            
            # Format message with file metadata
            progress_text = (
                "📤 **Upload Progress**\n\n"
                f"🎬 File: {file_name}\n"
                f"⏱ Duration: {duration}\n"
                f"🎞 Quality: {quality}\n\n"
                "━━━━━━━━━━━━━━\n"
                f"{bar} {percent:.1f}%\n"
                "━━━━━━━━━━━━━━\n\n"
                f"📦 Uploaded: {current_mb:.1f} MB / {total_mb:.1f} MB\n"
                f"🚀 Speed: {speed}\n"
                f"⏱️ ETA: {eta}"
            )
            
            await send_progress_message(chat_id, progress_message_id, progress_text)
            
            # Structured logging at milestones
            current_milestone = int(percent // 25) * 25
            if current_milestone > last_upload_milestone[0] and current_milestone > 0:
                # Note: bot_index will be logged in telegram_uploader
                last_upload_milestone[0] = current_milestone
        
        upload_success = await telegram_uploader.upload_video(
            file_path=downloaded_file,
            job_data=job_data,
            progress_callback=upload_progress
        )
        
        if not upload_success:
            progress_logger.log_upload_error(link_hash, "Upload failed", bot_index=0)
            await worker_bot.send_message(chat_id, ERROR_UPLOAD_FAILED)
            return
        
        # Delete progress message from user chat
        await delete_progress_message(chat_id, progress_message_id)
        
        # Cleanup temporary files
        try:
            # Delete thumbnail file if it exists
            if thumb_path and thumb_path.exists():
                thumb_path.unlink()
                log.info(f"[THUMB] CLEANUP_DONE | Deleted thumbnail: {thumb_path.name}")
            
            # If we created a new video with embedded thumb, delete original
            if downloaded_file != original_video and original_video.exists():
                original_video.unlink()
                log.info(f"[THUMB] CLEANUP_DONE | Deleted original video: {original_video.name}")
        except Exception as e:
            log.warning(f"[THUMB] CLEANUP_ERROR | {type(e).__name__}: {e}")
        
        # Cleanup rate limiter
        rate_limiter.reset(link_hash)
        rate_limiter.reset(upload_job_id)
        
        log.info(f"Upload completed for user {user_id}")
        
        # Success message already sent via forward
        
    except Exception as e:
        log.error(f"Error processing job: {e}")
        try:
            await worker_bot.send_message(chat_id, ERROR_PROCESSING)
        except:
            pass
    
    finally:
        # Step 6: Cleanup - delete ALL temporary files
        # This includes the final video file that was uploaded
        try:
            # Track which file was actually uploaded
            file_to_cleanup = None
            
            # Check if we have downloaded_file (the final video with thumbnail)
            if 'downloaded_file' in locals() and downloaded_file:
                file_to_cleanup = downloaded_file
            elif 'file_path' in locals() and file_path:
                # Fallback to original file_path
                file_to_cleanup = file_path
            
            # Delete the uploaded file
            if file_to_cleanup:
                await file_manager.cleanup_file(file_to_cleanup)
                
        except Exception as e:
            log.error(f"Error during final cleanup: {e}")


async def job_consumer():
    """Job consumer loop."""
    log.info("Starting job consumer")
    await job_queue.consume_jobs(process_job, stop_event)


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    log.info(f"Received signal {signum}, shutting down...")
    stop_event.set()


async def on_startup():
    """Initialize services on startup."""
    global worker_bot
    
    log.info("Starting worker server...")
    
    try:
        # Initialize database
        await init_db()
        
        # Initialize Redis
        await init_redis()
        
        # Initialize multi-bot manager for uploads
        await multi_bot_manager.initialize()
        
        # CRITICAL: Validate all upload bots have access to log channel
        log.info("=" * 60)
        log.info("Validating upload bots access to log channel...")
        log.info("=" * 60)
        
        valid_bot_count = await multi_bot_manager.validate_channel_access(settings.log_channel_id)
        
        if valid_bot_count == 0:
            log.error("❌ CRITICAL ERROR: NO upload bots have access to log channel!")
            log.error(f"   Channel ID: {settings.log_channel_id}")
            log.error("   Action required:")
            log.error("   1. Add all upload bots to the channel")
            log.error("   2. Grant them admin permissions (or at least 'Post Messages')")
            log.error("   3. Restart the worker")
            raise RuntimeError("No valid upload bots - cannot start worker")
        
        log.info("=" * 60)
        log.info(f"✅ Upload bot validation complete: {valid_bot_count} bot(s) ready")
        log.info("=" * 60)
        
        # Initialize worker bot for sending messages
        worker_bot = Bot(token=settings.main_bot_token)
        
        log.info("Worker server started successfully")
        
    except Exception as e:
        log.error(f"Error during startup: {e}")
        raise


async def on_shutdown():
    """Cleanup on shutdown."""
    log.info("Shutting down worker server...")
    
    try:
        # Close database
        await close_db()
        
        # Close Redis
        await close_redis()
        
        # Close multi-bot manager
        await multi_bot_manager.close()
        
        # Close worker bot
        if worker_bot:
            await worker_bot.session.close()
        
        log.info("Worker server shutdown complete")
        
    except Exception as e:
        log.error(f"Error during shutdown: {e}")


async def main():
    """Main entry point."""
    # Setup logger
    setup_logger("worker")
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Startup
        await on_startup()
        
        # Start job consumer
        await job_consumer()
        
    except KeyboardInterrupt:
        log.info("Received keyboard interrupt")
    except Exception as e:
        log.error(f"Fatal error: {e}")
    finally:
        # Shutdown
        await on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
