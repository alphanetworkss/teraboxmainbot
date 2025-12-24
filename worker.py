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
from aiogram import Bot


# Worker state
stop_event = asyncio.Event()
worker_bot: Bot = None


async def fetch_m3u8_from_api(link: str) -> str | None:
    """
    Fetch M3U8 URL from Starbots TeraBox API.
    
    API Response Format:
    {
        "errno": 0,
        "data": {
            "file": {
                "file_name": "...",
                "stream_url": "http://api.starbots.in/play/i/...",  # This is the M3U8 URL
                "size": 123456,
                ...
            }
        }
    }
    
    Args:
        link: TeraBox link
        
    Returns:
        M3U8 URL (stream_url) if successful, None otherwise
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
                        # Extract stream_url from response
                        stream_url = data.get('data', {}).get('file', {}).get('stream_url')
                        
                        if stream_url:
                            log.info(f"Got M3U8 URL from Starbots API: {stream_url}")
                            return stream_url
                        else:
                            log.error(f"No stream_url in API response: {data}")
                            return None
                    else:
                        log.error(f"API returned error: errno={data.get('errno')}, data={data}")
                        return None
                else:
                    log.error(f"API request failed: status={response.status}")
                    return None
                    
    except Exception as e:
        log.error(f"Error fetching M3U8 from Starbots API: {e}")
        return None


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


def progress_bar(done, total, length=10):
    """Create a visual progress bar."""
    if not total or total <= 0:
        import time
        from math import floor
        dots = int((time.time() * 2) % (length + 1))
        return "⬢" * dots + "⬡" * (length - dots)
    from math import floor
    filled = min(length, floor(length * done / total))
    return "⬢" * filled + "⬡" * (length - filled)


def format_bytes(bytes_val):
    """Format bytes to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} TB"


def format_time(seconds):
    """Format seconds to human readable time."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


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
        # Step 1: Fetch M3U8 URL from API
        m3u8_url = await fetch_m3u8_from_api(link)
        
        if not m3u8_url:
            await worker_bot.send_message(chat_id, ERROR_DOWNLOAD_FAILED)
            return
        
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
        
        # Progress tracking for download
        import time
        download_start_time = time.time()
        last_update_time = [download_start_time]
        last_downloaded = [0]
        
        async def download_progress(progress: int):
            """Enhanced download progress with speed and ETA."""
            current_time = time.time()
            
            # Update every 3 seconds to avoid rate limits
            if current_time - last_update_time[0] < 3:
                return
            
            last_update_time[0] = current_time
            
            # Create progress bar
            bar = progress_bar(progress, 100, length=10)
            
            # Calculate elapsed time and ETA
            elapsed = current_time - download_start_time
            if progress > 0 and progress < 100:
                total_time = (elapsed / progress) * 100
                remaining = total_time - elapsed
                eta = format_time(remaining)
            else:
                eta = "Calculating..."
            
            # Format message
            progress_text = (
                "📥 **Downloading (Stream → MP4)**\n\n"
                "╭━━━━❰Progress❱━➣\n"
                f"┣⪼ [{bar}]\n"
                f"┣⪼ ✅ Done: {progress}%\n"
                f"┣⪼ ⏱️ Elapsed: {format_time(elapsed)}\n"
                f"┣⪼ ⏳ ETA: {eta if progress < 100 else 'Finishing...'}\n"
                "╰━━━━━━━━━━━━━━━➣"
            )
            
            await send_progress_message(chat_id, progress_message_id, progress_text)
        
        # Send initial download message
        await send_progress_message(
            chat_id,
            progress_message_id,
            "📥 **Downloading (Stream → MP4)**\n\n"
            "╭━━━━❰Progress❱━➣\n"
            "┣⪼ [⬡⬡⬡⬡⬡⬡⬡⬡⬡⬡]\n"
            "┣⪼ ✅ Done: 0%\n"
            "┣⪼ ⏱️ Starting download...\n"
            "╰━━━━━━━━━━━━━━━➣"
        )
        
        downloaded_file = await ffmpeg_helper.download_m3u8(
            m3u8_url=best_quality_url,
            output_path=file_path,
            progress_callback=download_progress
        )
        
        if not downloaded_file:
            await worker_bot.send_message(chat_id, ERROR_DOWNLOAD_FAILED)
            return
        
        log.info(f"Download completed: {downloaded_file}")
        
        # Step 5: Upload to Telegram
        log.info(f"Uploading video to Telegram")
        
        # Progress tracking for upload
        upload_start_time = time.time()
        last_upload_time = [upload_start_time]
        
        async def upload_progress(current: int, total: int):
            """Enhanced upload progress with speed and ETA."""
            current_time = time.time()
            
            # Update every 3 seconds to avoid rate limits
            if current_time - last_upload_time[0] < 3:
                return
            
            last_upload_time[0] = current_time
            
            # Calculate progress
            percent = (current / total * 100) if total > 0 else 0
            bar = progress_bar(current, total, length=10)
            
            # Calculate speed
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
            
            # Get file size
            file_size_mb = total / 1024 / 1024
            
            # Format message
            progress_text = (
                f"📤 **Uploading to Telegram**\n\n"
                "╭━━━━❰Progress❱━➣\n"
                f"┣⪼ [{bar}]\n"
                f"┣⪼ ✅ Uploaded: {percent:.2f}%\n"
                f"┣⪼ 📦 Size: {file_size_mb:.2f} MB\n"
                f"┣⪼ ⚡ Speed: {speed}\n"
                f"┣⪼ ⏳ ETA: {eta if percent < 100 else 'Finishing...'}\n"
                "╰━━━━━━━━━━━━━━━➣"
            )
            
            await send_progress_message(chat_id, progress_message_id, progress_text)
        
        upload_success = await telegram_uploader.upload_video(
            file_path=downloaded_file,
            job_data=job_data,
            progress_callback=upload_progress
        )
        
        if not upload_success:
            await worker_bot.send_message(chat_id, ERROR_UPLOAD_FAILED)
            return
        
        log.info(f"Upload completed for user {user_id}")
        
        # Success message already sent via forward
        
    except Exception as e:
        log.error(f"Error processing job: {e}")
        try:
            await worker_bot.send_message(chat_id, ERROR_PROCESSING)
        except:
            pass
    
    finally:
        # Step 6: Cleanup - delete file
        if file_path:
            await file_manager.cleanup_file(file_path)


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
