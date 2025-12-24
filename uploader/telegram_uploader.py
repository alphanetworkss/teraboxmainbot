"""
Telegram uploader.
Handles video upload to log channel and forwarding to users.
"""
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from pyrogram import Client
from pyrogram.errors import FloodWait
from pyrogram.types import Message
from uploader.multi_bot_manager import multi_bot_manager
from database.models import video_record
from config.settings import settings
from utils.logger import log


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
                
                log.info(f"Uploading video using bot {bot_index}: {file_path.name}")
                
                # Upload to log channel
                message: Message = await client.send_video(
                    chat_id=settings.log_channel_id,
                    video=str(file_path),
                    caption=f"🔗 Link: {job_data['link']}\n📦 Hash: {job_data['link_hash'][:16]}...",
                    progress=progress_callback
                )
                
                log.info(f"Video uploaded to log channel: message_id={message.id}")
                
                # Get file size
                file_size = file_path.stat().st_size
                
                # Save to MongoDB
                await video_record.save_video(
                    link=job_data['link'],
                    link_hash=job_data['link_hash'],
                    channel_message_id=message.id,
                    file_id=message.video.file_id,
                    file_size=file_size
                )
                
                # Forward to user
                try:
                    await client.forward_messages(
                        chat_id=job_data['chat_id'],
                        from_chat_id=settings.log_channel_id,
                        message_ids=message.id
                    )
                    log.info(f"Video forwarded to user: user_id={job_data['user_id']}")
                except Exception as e:
                    log.error(f"Error forwarding to user: {e}")
                    # Still consider upload successful if saved to channel
                
                return True
                
            except FloodWait as e:
                log.warning(f"FloodWait error on bot {bot_index}: wait {e.value}s")
                
                # Mark bot as unavailable
                await multi_bot_manager.mark_unavailable(bot_index, e.value)
                
                # Retry with next bot
                retry_count += 1
                log.info(f"Retrying upload with next bot (attempt {retry_count}/{max_retries})")
                
            except Exception as e:
                log.error(f"Error uploading video: {e}")
                retry_count += 1
        
        log.error(f"Failed to upload video after {max_retries} retries")
        return False
    
    async def forward_existing_video(
        self,
        chat_id: int,
        channel_message_id: int
    ) -> bool:
        """
        Forward existing video from log channel to user.
        
        Args:
            chat_id: User's chat ID
            channel_message_id: Message ID in log channel
            
        Returns:
            True if forwarded successfully, False otherwise
        """
        try:
            # Get any available bot
            bot_result = await multi_bot_manager.get_next_bot()
            
            if bot_result is None:
                log.error("No upload bots available for forwarding")
                return False
            
            client, bot_index = bot_result
            
            # Forward message
            await client.forward_messages(
                chat_id=chat_id,
                from_chat_id=settings.log_channel_id,
                message_ids=channel_message_id
            )
            
            log.info(f"Forwarded existing video to chat_id={chat_id}, msg_id={channel_message_id}")
            return True
            
        except FloodWait as e:
            log.warning(f"FloodWait on forward: {e.value}s")
            # Could implement retry here, but for simplicity just fail
            return False
        except Exception as e:
            log.error(f"Error forwarding existing video: {e}")
            return False


# Global uploader instance
telegram_uploader = TelegramUploader()
