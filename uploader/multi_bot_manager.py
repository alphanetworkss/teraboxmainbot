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
            
            for i, token in enumerate(upload_tokens):
                try:
                    # Create Pyrogram client
                    client = Client(
                        name=f"upload_bot_{i}",
                        api_id=settings.api_id,
                        api_hash=settings.api_hash,
                        bot_token=token,
                        workdir="sessions"  # Store sessions in sessions/ directory
                    )
                    
                    # Start client
                    await client.start()
                    
                    # Get bot info
                    me = await client.get_me()
                    log.info(f"Bot {i} initialized: @{me.username}")
                    
                    self.clients.append(client)
                    self.unavailable_until.append(0)
                    
                except Exception as e:
                    log.error(f"Failed to initialize bot {i}: {e}")
            
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
                
                # Check if bot is available
                if self.unavailable_until[bot_index] <= current_time:
                    log.debug(f"Selected upload bot {bot_index}")
                    return self.clients[bot_index], bot_index
                
                attempts += 1
            
            # All bots are unavailable
            log.warning("All upload bots are currently unavailable")
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
