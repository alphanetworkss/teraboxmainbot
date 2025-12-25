"""
Multi-bot upload manager.
Manages multiple Telegram bot clients for upload with round-robin selection.
"""
import asyncio
from typing import List, Optional
from pyrogram import Client
from pyrogram.errors import FloodWait
from config.settings import settings
from utils.logger import log


class MultiBotManager:
    """Multi-bot upload manager with round-robin selection."""
    
    def __init__(self):
        """Initialize multi-bot manager."""
        self.clients: List[Client] = []
        self.bot_usernames: List[str] = []  # Store @username for each bot
        self.bot_ids: List[int] = []  # Store bot user IDs
        self.bot_valid_for_channel: List[bool] = []  # Track which bots have channel access
        self.current_index = 0
        self.unavailable_until: List[float] = []  # Timestamp when bot becomes available again
        self.lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize all bot clients."""
        try:
            upload_tokens = settings.upload_tokens_list
            
            if not upload_tokens:
                raise ValueError("No upload bot tokens configured")
            
            log.info(f"Initializing {len(upload_tokens)} upload bot clients")
            
            # Create sessions directory if it doesn't exist
            import os
            os.makedirs("sessions", exist_ok=True)
            
            for i, token in enumerate(upload_tokens):
                try:
                    # Create Pyrogram client with in-memory session
                    client = Client(
                        name=f"upload_bot_{i}",
                        api_id=settings.api_id,
                        api_hash=settings.api_hash,
                        bot_token=token,
                        workdir="sessions",  # Store sessions in sessions/ directory
                        in_memory=True  # Use in-memory session to avoid file permission issues
                    )
                    
                    # Start client
                    await client.start()
                    
                    # Get bot info
                    me = await client.get_me()
                    bot_username = f"@{me.username}" if me.username else f"Bot_{me.id}"
                    log.info(f"Bot {i} initialized: {bot_username} (ID: {me.id})")
                    
                    self.clients.append(client)
                    self.bot_usernames.append(bot_username)
                    self.bot_ids.append(me.id)
                    self.bot_valid_for_channel.append(True)  # Assume valid initially, will validate later
                    self.unavailable_until.append(0)
                    
                except Exception as e:
                    log.error(f"Failed to initialize bot {i}: {e}")
                    # Continue to next bot instead of failing completely
            
            if not self.clients:
                raise RuntimeError("No upload bots initialized successfully")
            
            log.info(f"Successfully initialized {len(self.clients)} upload bots")
            
        except Exception as e:
            log.error(f"Error initializing multi-bot manager: {e}")
            raise
    
    async def close(self):
        """Close all bot clients."""
        for i, client in enumerate(self.clients):
            try:
                await client.stop()
                log.info(f"Stopped upload bot {i}")
            except Exception as e:
                log.error(f"Error stopping bot {i}: {e}")
    
    async def get_next_bot(self) -> Optional[tuple[Client, int]]:
        """
        Get next available bot using round-robin selection.
        Skips bots that are invalid for channel or temporarily unavailable.
        
        Returns:
            Tuple of (Client, index) if available, None if all bots are unavailable
        """
        async with self.lock:
            import time
            current_time = time.time()
            
            # Try to find an available bot
            attempts = 0
            while attempts < len(self.clients):
                bot_index = self.current_index
                self.current_index = (self.current_index + 1) % len(self.clients)
                
                # Skip bots that are invalid for channel
                if not self.bot_valid_for_channel[bot_index]:
                    log.debug(f"Skipping bot {bot_index} - marked as invalid for channel")
                    attempts += 1
                    continue
                
                # Check if bot is available (not in FloodWait)
                if self.unavailable_until[bot_index] <= current_time:
                    log.debug(f"Selected upload bot {bot_index} ({self.bot_usernames[bot_index]})")
                    return self.clients[bot_index], bot_index
                
                attempts += 1
            
            # All bots are unavailable or invalid
            log.warning("All upload bots are currently unavailable or invalid")
            return None
    
    async def mark_unavailable(self, bot_index: int, wait_seconds: int):
        """
        Mark a bot as unavailable for specified duration.
        
        Args:
            bot_index: Index of the bot
            wait_seconds: Seconds to wait before bot becomes available
        """
        import time
        async with self.lock:
            self.unavailable_until[bot_index] = time.time() + wait_seconds
            log.warning(f"Bot {bot_index} marked unavailable for {wait_seconds}s (FloodWait)")
    
    async def mark_invalid_for_channel(self, bot_index: int):
        """
        Permanently mark a bot as invalid for the channel.
        Used when bot has no access or was removed from channel.
        
        Args:
            bot_index: Index of the bot to mark as invalid
        """
        async with self.lock:
            self.bot_valid_for_channel[bot_index] = False
            bot_username = self.bot_usernames[bot_index] if bot_index < len(self.bot_usernames) else f"Bot_{bot_index}"
            log.error(f"Bot {bot_index} ({bot_username}) marked as INVALID for channel (peer error)")
    
    async def validate_channel_access(self, channel_id: int | str):
        """
        Validate all bots have access to the specified channel.
        Updates bot_valid_for_channel list based on validation results.
        
        Args:
            channel_id: Channel ID or username to validate
        """
        from uploader.chat_validator import validate_chat_access
        
        log.info(f"Validating {len(self.clients)} upload bots for channel access...")
        
        validation_results = []
        
        for i, client in enumerate(self.clients):
            bot_username = self.bot_usernames[i] if i < len(self.bot_usernames) else f"Bot_{i}"
            
            is_valid, error_reason, chat_info = await validate_chat_access(client, channel_id, i)
            
            self.bot_valid_for_channel[i] = is_valid
            validation_results.append((i, bot_username, is_valid, error_reason))
            
            if is_valid:
                channel_title = chat_info.get('title', 'Unknown') if chat_info else 'Unknown'
                log.info(f"  ✅ Bot {i} ({bot_username}): Has access to '{channel_title}'")
            else:
                log.warning(f"  ❌ Bot {i} ({bot_username}): NO ACCESS - {error_reason}")
        
        # Summary
        valid_count = sum(self.bot_valid_for_channel)
        total_count = len(self.clients)
        
        log.info(f"\n[VALIDATION SUMMARY] {valid_count}/{total_count} bots have channel access")
        
        if valid_count == 0:
            log.error("❌ CRITICAL: NO upload bots have access to the channel!")
            log.error(f"   Channel ID: {channel_id}")
            log.error("   Action required: Add all upload bots to the channel as admins")
        elif valid_count < total_count:
            log.warning(f"⚠️  WARNING: Only {valid_count}/{total_count} bots have channel access")
            log.warning("   Some bots will not be used for uploads")
        else:
            log.info(f"✅ SUCCESS: All {valid_count} bots validated for channel access")
        
        return valid_count
    
    async def handle_flood_wait(self, bot_index: int, wait_time: int) -> Optional[tuple[Client, int]]:
        """
        Handle FloodWait error by marking bot unavailable and getting next bot.
        
        Args:
            bot_index: Index of the bot that got FloodWait
            wait_time: Wait time in seconds
            
        Returns:
            Next available bot, or None if all unavailable
        """
        await self.mark_unavailable(bot_index, wait_time)
        return await self.get_next_bot()


# Global multi-bot manager instance
multi_bot_manager = MultiBotManager()
