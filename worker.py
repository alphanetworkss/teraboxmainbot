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
from queue import init_redis, close_redis, job_queue
from downloader import m3u8_parser, ffmpeg_helper
from uploader import multi_bot_manager, telegram_uploader
from utils import log, setup_logger, file_manager
from aiogram import Bot


# Worker state
stop_event = asyncio.Event()
worker_bot: Bot = None


async def fetch_m3u8_from_api(link: str) -> str | None:
    """
    Fetch M3U8 URL from external TeraBox API.
    
    Args:
        link: TeraBox link
        
    Returns:
        M3U8 URL if successful, None otherwise
    """
    try:
        log.info(f"Fetching M3U8 URL from API: {link}")
        
        # Call external API
        async with aiohttp.ClientSession() as session:
            # Adjust this based on your actual API format
            params = {'url': link}
            
            async with session.get(
                settings.terabox_api_url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract M3U8 URL from response
                    # Adjust this based on your API response structure
                    m3u8_url = data.get('m3u8_url') or data.get('url') or data.get('video_url')
                    
                    if m3u8_url:
                        log.info(f"Got M3U8 URL from API: {m3u8_url}")
                        return m3u8_url
                    else:
                        log.error(f"No M3U8 URL in API response: {data}")
                        return None
                else:
                    log.error(f"API request failed: status={response.status}")
                    return None
                    
    except Exception as e:
        log.error(f"Error fetching M3U8 from API: {e}")
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
        
        # Step 3: Create temp file path
        file_path = await file_manager.create_temp_file(link_hash)
        
        # Step 4: Download video with ffmpeg
        log.info(f"Downloading video: {best_quality_url}")
        
        # Progress callback for download
        last_progress = [0]
        
        async def download_progress(progress: int):
            if progress - last_progress[0] >= 10:  # Update every 10%
                last_progress[0] = progress
                await send_progress_message(
                    chat_id,
                    message_id,
                    MSG_DOWNLOADING.format(progress=progress)
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
        
        # Progress callback for upload
        last_upload_progress = [0]
        
        async def upload_progress(current: int, total: int):
            progress = int((current / total) * 100)
            if progress - last_upload_progress[0] >= 10:  # Update every 10%
                last_upload_progress[0] = progress
                await send_progress_message(
                    chat_id,
                    message_id,
                    MSG_UPLOADING.format(progress=progress)
                )
        
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
