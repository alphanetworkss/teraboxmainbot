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
from redis_queue import init_redis, close_redis, job_queue
from validators import is_valid_terabox_link, normalize_terabox_url
from uploader import multi_bot_manager, telegram_uploader
from utils import log, setup_logger, check_user_subscription, get_force_subscribe_keyboard, get_force_subscribe_message


# Initialize bot and dispatcher
bot = Bot(token=settings.main_bot_token)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command with premium welcome message and photo."""
    # Check force subscribe
    if not await check_user_subscription(bot, message.from_user.id):
        keyboard = await get_force_subscribe_keyboard()
        await message.answer(
            get_force_subscribe_message(),
            reply_markup=keyboard
        )
        return
    
    # Premium welcome message
    welcome_caption = (
        "✨ **Welcome to TeraBox Downloader Bot** ✨\n\n"
        "📥 Send me a **TeraBox link** and I'll download & upload the video for you.\n\n"
        "✅ **Supported link formats**\n"
        "• Links containing `/s/`\n"
        "• Links containing `?surl=`\n\n"
        "⚡ Fast • Reliable • Free\n"
        "🚀 Powered by **@Thestarbots**"
    )
    
    try:
        # Try to send with photo/GIF
        # You can configure this path in settings or use a URL
        welcome_photo = getattr(settings, 'welcome_photo_url', None)
        
        if welcome_photo:
            # Send photo with caption
            await message.answer_photo(
                photo=welcome_photo,
                caption=welcome_caption,
                parse_mode="Markdown"
            )
        else:
            # Fallback to text-only if no photo configured
            await message.answer(welcome_caption, parse_mode="Markdown")
            
    except Exception as e:
        # Fallback to text-only if photo fails
        log.debug(f"Could not send welcome photo: {e}")
        await message.answer(welcome_caption, parse_mode="Markdown")


@dp.callback_query(F.data == "check_subscription")
async def callback_check_subscription(callback: CallbackQuery):
    """Handle subscription check callback."""
    if await check_user_subscription(bot, callback.from_user.id):
        welcome_text = (
            "✨ **Welcome to TeraBox Downloader Bot** ✨\n\n"
            "📥 Send me a **TeraBox link** and I'll handle the rest.\n\n"
            "🎬 You'll get:\n"
            "• High quality videos\n"
            "• Fast download & upload\n"
            "• Clean progress updates\n\n"
            "⚡ Powered by **@Thestarbots**"
        )
        await callback.message.edit_text(welcome_text, parse_mode="Markdown")
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
            # Send cached video info message
            cache_msg = await message.answer(MSG_DUPLICATE_FOUND)
            
            # Forward existing video from log channel
            channel_message_id = existing_video.get('channel_message_id')
            
            if channel_message_id:
                success = await telegram_uploader.forward_existing_video(
                    chat_id=message.chat.id,
                    channel_message_id=channel_message_id
                )
                
                if success:
                    # Clean up cache info message after video is sent
                    try:
                        await cache_msg.delete()
                        log.info(f"[USER] CACHE_MSG_DELETED | chat_id={message.chat.id} | msg_id={cache_msg.message_id}")
                    except Exception as e:
                        log.debug(f"Could not delete cache message: {e}")
                    
                    # Schedule auto-delete for the video (1 hour)
                    # Note: forward_existing_video should return the sent message for this to work
                    # For now, we'll add this in telegram_uploader.py
                else:
                    await message.answer(ERROR_PROCESSING)
            else:
                log.error(f"No channel_message_id found for hash: {link_hash}")
                await message.answer(ERROR_PROCESSING)
            
            return
        
        # Send processing message first
        processing_msg = await message.answer(MSG_PROCESSING)
        
        # New video - push job to queue with processing message ID
        job_data = {
            'link': link,
            'user_id': message.from_user.id,
            'chat_id': message.chat.id,
            'message_id': message.message_id,
            'processing_message_id': processing_msg.message_id,  # So worker can edit this message
            'link_hash': link_hash
        }
        
        success = await job_queue.push_job(job_data)
        
        if success:
            log.info(f"Job queued for user {message.from_user.id}: hash={link_hash}")
        else:
            await processing_msg.edit_text(ERROR_PROCESSING)
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
        
        # Verify main bot can access log channel
        try:
            chat = await bot.get_chat(settings.log_channel_id)
            log.info(f"✅ Main bot can access log channel: {chat.title}")
        except Exception as e:
            log.error(f"❌ Main bot CANNOT access log channel: {e}")
            log.error(f"   Make sure main bot is admin of channel ID: {settings.log_channel_id}")
            raise RuntimeError(f"Main bot cannot access log channel: {e}")
        
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
