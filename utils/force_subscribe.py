"""
Force subscribe middleware and helper functions.
Checks if user is subscribed to required channel before allowing bot usage.
"""
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config.settings import settings
from config.constants import ERROR_NOT_SUBSCRIBED
from utils.logger import log


async def check_user_subscription(bot: Bot, user_id: int) -> bool:
    """
    Check if user is subscribed to the force subscribe channel.
    
    Args:
        bot: Bot instance
        user_id: Telegram user ID
        
    Returns:
        True if subscribed or force subscribe disabled, False otherwise
    """
    # If force subscribe is disabled (channel_id = 0 or '0'), allow all users
    if settings.force_subscribe_channel_id in [0, '0', '', None]:
        return True
    
    try:
        # Get user's membership status in the channel
        member = await bot.get_chat_member(
            chat_id=settings.force_subscribe_channel_id,  # Can be @username or -100xxx
            user_id=user_id
        )
        
        # Check if user is a member (member, administrator, or creator)
        if member.status in ['member', 'administrator', 'creator']:
            log.debug(f"User {user_id} is subscribed to force channel")
            return True
        else:
            log.info(f"User {user_id} is not subscribed: status={member.status}")
            return False
            
    except Exception as e:
        log.error(f"Error checking subscription for user {user_id}: {e}")
        # On error, allow user to proceed (fail open)
        return True


async def get_force_subscribe_keyboard() -> InlineKeyboardMarkup:
    """
    Get inline keyboard with join channel button.
    
    Returns:
        InlineKeyboardMarkup with join button
    """
    try:
        channel_id = settings.force_subscribe_channel_id
        
        # If channel_id is a username (starts with @), use it directly
        if isinstance(channel_id, str) and channel_id.startswith('@'):
            channel_link = f"https://t.me/{channel_id[1:]}"  # Remove @ prefix
        else:
            # It's a numeric ID, get channel info
            bot = Bot(token=settings.main_bot_token)
            chat = await bot.get_chat(channel_id)
            
            if chat.username:
                channel_link = f"https://t.me/{chat.username}"
            else:
                # For private channels, use invite link
                channel_link = f"https://t.me/c/{str(channel_id)[4:]}"
            
            await bot.session.close()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Join Channel", url=channel_link)],
            [InlineKeyboardButton(text="✅ I Joined", callback_data="check_subscription")]
        ])
        
        return keyboard
        
    except Exception as e:
        log.error(f"Error creating force subscribe keyboard: {e}")
        # Return simple keyboard without link
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Check Again", callback_data="check_subscription")]
        ])
        return keyboard


def get_force_subscribe_message() -> str:
    """
    Get force subscribe error message.
    
    Returns:
        Error message string
    """
    return ERROR_NOT_SUBSCRIBED.format(channel_link="the channel below")
