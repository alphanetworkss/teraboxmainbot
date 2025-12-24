"""
Main Telegram bot server.
Handles user interactions, link validation, and job queue management.
"""
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from config.settings import settings
from config.constants import (
    ERROR_INVALID_LINK,
    ERROR_PROCESSING,
    MSG_PROCESSING,
    MSG_DUPLICATE_FOUND
)
from database import init_db, close_db, video_record
from database.models import VideoRecord
from queue import init_redis, close_redis, job_queue
from validators import is_valid_terabox_link, normalize_terabox_url
from uploader import multi_bot_manager, telegram_uploader
from utils import log, setup_logger, check_user_subscription, get_force_subscribe_keyboard, get_force_subscribe_message


# Initialize bot and dispatcher
bot = Bot(token=settings.main_bot_token)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command."""
    # Check force subscribe
    if not await check_user_subscription(bot, message.from_user.id):
        keyboard = await get_force_subscribe_keyboard()
        await message.answer(
            get_force_subscribe_message(),
            reply_markup=keyboard
        )
        return
    
    welcome_text = """
👋 Welcome to TeraBox Downloader Bot!

📥 Send me a TeraBox link and I'll download and upload the video for you.

✅ Valid link formats:
• Links containing /s/
• Links containing ?surl=

⚡️ Fast, reliable, and free!
"""
    await message.answer(welcome_text)


@dp.callback_query(F.data == "check_subscription")
async def callback_check_subscription(callback: CallbackQuery):
    """Handle subscription check callback."""
    if await check_user_subscription(bot, callback.from_user.id):
        await callback.message.edit_text("✅ Thank you for joining! You can now use the bot.\n\nSend me a TeraBox link to get started.")
    else:
        await callback.answer("❌ You haven't joined the channel yet!", show_alert=True)
    await callback.answer()


@dp.message(F.text)
async def handle_message(message: Message):
    """Handle text messages (TeraBox links)."""
    try:
        # Check force subscribe
        if not await check_user_subscription(bot, message.from_user.id):
            keyboard = await get_force_subscribe_keyboard()
            await message.answer(
                get_force_subscribe_message(),
                reply_markup=keyboard
            )
            return
        
        link = message.text.strip()
        
        # Validate TeraBox link
        if not is_valid_terabox_link(link):
            await message.answer(ERROR_INVALID_LINK)
            return
        
        log.info(f"Received valid TeraBox link from user {message.from_user.id}: {link}")
        
        # Normalize link for consistent hashing
        normalized_link = normalize_terabox_url(link)
        
        # Calculate SHA256 hash
        link_hash = VideoRecord.hash_link(normalized_link)
        
        # Check if video already exists in database
        existing_video = await video_record.find_by_hash(link_hash)
        
        if existing_video:
            log.info(f"Duplicate link detected: hash={link_hash}")
            
            # Send duplicate message
            await message.answer(MSG_DUPLICATE_FOUND)
            
            # Forward existing video from log channel
            channel_message_id = existing_video.get('channel_message_id')
            
            if channel_message_id:
                success = await telegram_uploader.forward_existing_video(
                    chat_id=message.chat.id,
                    channel_message_id=channel_message_id
                )
                
                if not success:
                    await message.answer(ERROR_PROCESSING)
            else:
                log.error(f"No channel_message_id found for hash: {link_hash}")
                await message.answer(ERROR_PROCESSING)
            
            return
        
        # New video - push job to queue
        job_data = {
            'link': link,
            'user_id': message.from_user.id,
            'chat_id': message.chat.id,
            'message_id': message.message_id,
            'link_hash': link_hash
        }
        
        success = await job_queue.push_job(job_data)
        
        if success:
            await message.answer(MSG_PROCESSING)
            log.info(f"Job queued for user {message.from_user.id}: hash={link_hash}")
        else:
            await message.answer(ERROR_PROCESSING)
            log.error(f"Failed to queue job for user {message.from_user.id}")
        
    except Exception as e:
        log.error(f"Error handling message: {e}")
        await message.answer(ERROR_PROCESSING)


async def on_startup():
    """Initialize services on startup."""
    log.info("Starting main bot server...")
    
    try:
        # Initialize database
        await init_db()
        
        # Create indexes
        await video_record.create_indexes()
        
        # Initialize Redis
        await init_redis()
        
        # Initialize multi-bot manager for forwarding
        await multi_bot_manager.initialize()
        
        log.info("Main bot server started successfully")
        
    except Exception as e:
        log.error(f"Error during startup: {e}")
        raise


async def on_shutdown():
    """Cleanup on shutdown."""
    log.info("Shutting down main bot server...")
    
    try:
        # Close database
        await close_db()
        
        # Close Redis
        await close_redis()
        
        # Close multi-bot manager
        await multi_bot_manager.close()
        
        # Close bot session
        await bot.session.close()
        
        log.info("Main bot server shutdown complete")
        
    except Exception as e:
        log.error(f"Error during shutdown: {e}")


async def main():
    """Main entry point."""
    # Setup logger
    setup_logger("main_bot")
    
    try:
        # Startup
        await on_startup()
        
        # Start polling
        log.info("Starting bot polling...")
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        log.info("Received keyboard interrupt")
    except Exception as e:
        log.error(f"Fatal error: {e}")
    finally:
        # Shutdown
        await on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
