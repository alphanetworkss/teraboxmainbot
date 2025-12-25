"""
Telegram uploader.
Handles video upload to log channel and forwarding to users.
"""
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from pyrogram import Client, enums
from pyrogram.errors import FloodWait, PeerIdInvalid, ChannelPrivate, ChatWriteForbidden
from pyrogram.types import Message
from uploader.multi_bot_manager import multi_bot_manager
from database.models import video_record
from config.settings import settings
from utils.logger import log
from utils.progress_tracker import progress_logger
from uploader.chat_validator import validate_chat_access, format_validation_error
import asyncio



def schedule_user_video_delete(bot, chat_id: int, message_id: int, delay: int = 3600):
    """
    Schedule deletion of user video after delay (bot chat only, NOT channel).
    
    Args:
        bot: Bot instance
        chat_id: User chat ID (NOT channel)
        message_id: Message ID to delete
        delay: Delay in seconds (default 3600 = 1 hour)
    """
    async def delete_after_delay():
        try:
            # CRITICAL SAFETY CHECK - never delete from channel
            if chat_id == settings.log_channel_id:
                log.error(
                    f"CRITICAL: Attempted to delete channel message {message_id}! "
                    f"This should NEVER happen. Aborting deletion."
                )
                return
            
            log.info(
                f"[USER] AUTO_DELETE_SCHEDULED | "
                f"chat_id={chat_id} | "
                f"msg_id={message_id} | "
                f"delete_in={delay}s"
            )
            
            # Wait for delay (non-blocking)
            await asyncio.sleep(delay)
            
            # Delete message from user chat
            await bot.delete_message(chat_id, message_id)
            
            log.info(
                f"[USER] AUTO_DELETE_DONE | "
                f"chat_id={chat_id} | "
                f"msg_id={message_id}"
            )
        except Exception as e:
            # Silent failure - user may have deleted manually
            log.debug(f"Could not auto-delete user message {message_id}: {e}")
    
    # Create background task (non-blocking)
    asyncio.create_task(delete_after_delay())


class TelegramUploader:
    """Telegram video uploader."""
    
    async def upload_video(
        self,
        file_path: Path | str,
        job_data: Dict[str, Any],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """
        Upload video to Telegram.
        
        Process:
        1. Select bot from multi-bot manager
        2. Upload to log channel
        3. Save message_id to MongoDB
        4. Forward to user
        5. Handle FloodWait errors with retry
        
        Args:
            file_path: Path to video file
            job_data: Job data with user_id, chat_id, link, link_hash
            progress_callback: Optional callback(current, total) for upload progress
            
        Returns:
            True if uploaded successfully, False otherwise
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            log.error(f"File not found: {file_path}")
            return False
        
        max_retries = len(multi_bot_manager.clients)
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Get next available bot
                bot_result = await multi_bot_manager.get_next_bot()
                
                if bot_result is None:
                    log.error("No upload bots available")
                    return False
                
                client, bot_index = bot_result
                
                # Get file size for logging
                file_size = file_path.stat().st_size
                
                # Log upload start
                progress_logger.log_upload_start(
                    job_data['link_hash'],
                    bot_index,
                    file_size
                )
                
                log.info(f"Uploading video using bot {bot_index} ({multi_bot_manager.bot_usernames[bot_index]}): {file_path.name}")
                
                # CRITICAL: Validate bot has access to channel BEFORE upload
                is_valid, error_reason, chat_info = await validate_chat_access(
                    client,
                    settings.log_channel_id,
                    bot_index
                )
                
                if not is_valid:
                    # Bot doesn't have access - mark as invalid and try next bot
                    bot_username = multi_bot_manager.bot_usernames[bot_index]
                    error_msg = format_validation_error(
                        bot_index=bot_index,
                        bot_username=bot_username,
                        chat_id=settings.log_channel_id,
                        error_type="PEER_VALIDATION_FAILED",
                        error_message=error_reason,
                        job_id=job_data['link_hash']
                    )
                    log.error(error_msg)
                    
                    # Mark bot as invalid for channel
                    await multi_bot_manager.mark_invalid_for_channel(bot_index)
                    
                    # Try next bot
                    retry_count += 1
                    continue
                
                # Bot has access - proceed with upload
                log.info(f"Bot {bot_index} validated for channel access, proceeding with upload")
                
                # Get file metadata for caption
                file_metadata = job_data.get('file_metadata', {})
                file_name = file_metadata.get('file_name', 'Unknown')
                duration = file_metadata.get('duration', 'N/A')
                file_size_readable = file_metadata.get('size_readable', 'N/A')
                
                # Create caption with file info and deletion notice
                caption = (
                    f"🎬 <b>{file_name}</b>\n\n"
                    f"⏱ Duration: {duration}\n"
                    f"📦 Size: {file_size_readable}\n\n"
                    f"⚠️ <b>Note:</b> Video will be auto-deleted after 1 hour"
                )
                
                # Upload to log channel
                # Note: Thumbnail is now embedded in video file, no need to pass thumb parameter
                message: Message = await client.send_video(
                    chat_id=settings.log_channel_id,
                    video=str(file_path),
                    caption=caption,
                    parse_mode=enums.ParseMode.HTML,  # Enable HTML formatting for bold text
                    supports_streaming=True,  # Enable streaming for better playback
                    progress=progress_callback
                )
                
                log.info(f"Video uploaded to log channel: message_id={message.id}")
                
                # Get file size and calculate upload duration
                import time
                file_size = file_path.stat().st_size
                
                # Save to MongoDB
                await video_record.save_video(
                    link=job_data['link'],
                    link_hash=job_data['link_hash'],
                    channel_message_id=message.id,
                    file_id=message.video.file_id,
                    file_size=file_size
                )
                
                # Send to user from MAIN BOT (not worker bot) without forward attribution
                try:
                    # Import main bot
                    from aiogram import Bot
                    main_bot = Bot(token=settings.main_bot_token)
                    
                    # Copy message instead of forwarding to remove "Forwarded from" attribution
                    user_message = await main_bot.copy_message(
                        chat_id=job_data['chat_id'],
                        from_chat_id=settings.log_channel_id,
                        message_id=message.id
                    )
                    
                    await main_bot.session.close()
                    
                    log.info(
                        f"[USER] VIDEO_SENT | "
                        f"chat_id={job_data['chat_id']} | "
                        f"msg_id={user_message.message_id} | "
                        f"source=fresh"
                    )
                    
                    # Schedule auto-delete (1 hour) - BOT CHAT ONLY
                    async def delete_after_delay():
                        try:
                            log.info(
                                f"[USER] AUTO_DELETE_SCHEDULED | "
                                f"chat_id={job_data['chat_id']} | "
                                f"msg_id={user_message.message_id} | "
                                f"in=3600s"
                            )
                            
                            await asyncio.sleep(3600)  # 1 hour
                            
                            # Recreate bot instance for deletion
                            from aiogram import Bot
                            delete_bot = Bot(token=settings.main_bot_token)
                            await delete_bot.delete_message(job_data['chat_id'], user_message.message_id)
                            await delete_bot.session.close()
                            
                            log.info(
                                f"[USER] AUTO_DELETE_DONE | "
                                f"chat_id={job_data['chat_id']} | "
                                f"msg_id={user_message.message_id}"
                            )
                        except Exception as e:
                            log.debug(f"Could not auto-delete fresh video {user_message.message_id}: {e}")
                    
                    # Create background task (non-blocking)
                    asyncio.create_task(delete_after_delay())
                    
                    # Log upload completion (note: duration calculation would require tracking start time)
                    # For now, we log completion without duration
                    progress_logger.log_upload_complete(
                        job_data['link_hash'],
                        0,  # Duration not tracked here, logged in worker
                        bot_index,
                        file_size
                    )
                except Exception as e:
                    log.error(f"Error sending to user: {e}")
                    # Still consider upload successful if saved to channel
                
                return True
                
            except FloodWait as e:
                log.warning(f"FloodWait error on bot {bot_index}: wait {e.value}s")
                
                # Mark bot as unavailable temporarily
                await multi_bot_manager.mark_unavailable(bot_index, e.value)
                
                # Retry with next bot
                retry_count += 1
                log.info(f"Retrying upload with next bot (attempt {retry_count}/{max_retries})")
            
            except (PeerIdInvalid, ChannelPrivate, ChatWriteForbidden) as e:
                # Peer errors - bot doesn't have access to channel
                bot_username = multi_bot_manager.bot_usernames[bot_index] if bot_index < len(multi_bot_manager.bot_usernames) else f"Bot_{bot_index}"
                
                error_msg = format_validation_error(
                    bot_index=bot_index,
                    bot_username=bot_username,
                    chat_id=settings.log_channel_id,
                    error_type=type(e).__name__.upper(),
                    error_message=str(e),
                    job_id=job_data['link_hash']
                )
                log.error(error_msg)
                
                # Mark bot as permanently invalid for this channel
                await multi_bot_manager.mark_invalid_for_channel(bot_index)
                
                # Log to progress tracker
                progress_logger.log_upload_error(
                    job_data['link_hash'],
                    f"{type(e).__name__}: {str(e)}",
                    bot_index
                )
                
                # Retry with next bot
                retry_count += 1
                log.info(f"Retrying upload with next bot (attempt {retry_count}/{max_retries})")
                
            
            except Exception as e:
                # Generic error - log and retry
                bot_username = multi_bot_manager.bot_usernames[bot_index] if bot_index < len(multi_bot_manager.bot_usernames) else f"Bot_{bot_index}"
                
                log.error(
                    f"[UPLOAD] ERROR | "
                    f"bot_index={bot_index} | "
                    f"bot_username={bot_username} | "
                    f"error={type(e).__name__} | "
                    f"message={str(e)} | "
                    f"job_id={job_data['link_hash'][:16]}"
                )
                
                progress_logger.log_upload_error(
                    job_data['link_hash'],
                    str(e),
                    bot_index
                )
                
                retry_count += 1
        
        log.error(f"Failed to upload video after {max_retries} retries")
        return False
    
    async def forward_existing_video(
        self,
        chat_id: int,
        channel_message_id: int
    ) -> bool:
        """
        Send existing video from log channel to user (without forward attribution).
        
        Args:
            chat_id: User's chat ID
            channel_message_id: Message ID in log channel
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Use MAIN BOT to send (not worker bot)
            from aiogram import Bot
            main_bot = Bot(token=settings.main_bot_token)
            
            log.info(f"Attempting to copy message {channel_message_id} from channel {settings.log_channel_id} to chat {chat_id}")
            
            # Copy message instead of forwarding to remove "Forwarded from" attribution
            await main_bot.copy_message(
                chat_id=chat_id,
                from_chat_id=settings.log_channel_id,
                message_id=channel_message_id
            )
            
            await main_bot.session.close()
            log.info(f"✅ Sent existing video to chat_id={chat_id}, msg_id={channel_message_id}")
            return True
            
        except Exception as e:
            log.error(f"❌ Error sending existing video: {e}")
            log.error(f"   Channel ID: {settings.log_channel_id}")
            log.error(f"   Message ID: {channel_message_id}")
            log.error(f"   User Chat ID: {chat_id}")
            return False


# Global uploader instance
telegram_uploader = TelegramUploader()
