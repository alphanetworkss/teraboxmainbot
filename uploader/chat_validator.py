"""
Chat validation utility for Telegram bots.
Validates bot access to channels and detects permission issues before upload.
"""
from typing import Tuple, Optional, Dict, Any
from pyrogram import Client
from pyrogram.errors import (
    PeerIdInvalid,
    ChannelPrivate,
    ChatWriteForbidden,
    UsernameInvalid,
    UsernameNotOccupied,
    RPCError
)
from utils.logger import log


async def validate_chat_access(
    client: Client,
    chat_id: int | str,
    bot_index: int
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Validate bot has access to a chat/channel.
    
    Args:
        client: Pyrogram client instance
        chat_id: Chat ID or username
        bot_index: Bot index for logging
        
    Returns:
        Tuple of (is_valid, error_reason, chat_info)
        - is_valid: True if bot has access
        - error_reason: Error description if invalid
        - chat_info: Chat information dict if valid
    """
    try:
        # Try to get chat information
        chat = await client.get_chat(chat_id)
        
        # Successfully got chat info
        chat_info = {
            'id': chat.id,
            'title': chat.title if hasattr(chat, 'title') else 'Unknown',
            'type': str(chat.type) if hasattr(chat, 'type') else 'unknown',
            'username': chat.username if hasattr(chat, 'username') else None
        }
        
        log.debug(f"[VALIDATION] Bot {bot_index} has access to chat {chat_id} ({chat_info['title']})")
        return True, "", chat_info
        
    except PeerIdInvalid as e:
        error_reason = "Bot not member of channel or invalid peer ID"
        log.warning(f"[VALIDATION] Bot {bot_index} - PeerIdInvalid for chat {chat_id}: {error_reason}")
        return False, error_reason, None
        
    except ChannelPrivate as e:
        error_reason = "Channel is private or bot was removed/kicked"
        log.warning(f"[VALIDATION] Bot {bot_index} - ChannelPrivate for chat {chat_id}: {error_reason}")
        return False, error_reason, None
        
    except ChatWriteForbidden as e:
        error_reason = "Bot has no permission to write in this chat"
        log.warning(f"[VALIDATION] Bot {bot_index} - ChatWriteForbidden for chat {chat_id}: {error_reason}")
        return False, error_reason, None
        
    except UsernameInvalid as e:
        error_reason = "Invalid channel username"
        log.warning(f"[VALIDATION] Bot {bot_index} - UsernameInvalid for chat {chat_id}: {error_reason}")
        return False, error_reason, None
        
    except UsernameNotOccupied as e:
        error_reason = "Channel username does not exist"
        log.warning(f"[VALIDATION] Bot {bot_index} - UsernameNotOccupied for chat {chat_id}: {error_reason}")
        return False, error_reason, None
        
    except RPCError as e:
        error_reason = f"Telegram API error: {str(e)}"
        log.error(f"[VALIDATION] Bot {bot_index} - RPCError for chat {chat_id}: {error_reason}")
        return False, error_reason, None
        
    except Exception as e:
        error_reason = f"Unexpected error: {str(e)}"
        log.error(f"[VALIDATION] Bot {bot_index} - Unexpected error for chat {chat_id}: {error_reason}")
        return False, error_reason, None


async def get_bot_permissions(
    client: Client,
    chat_id: int | str,
    bot_index: int
) -> Optional[Dict[str, bool]]:
    """
    Get bot's permissions in a chat/channel.
    
    Args:
        client: Pyrogram client instance
        chat_id: Chat ID or username
        bot_index: Bot index for logging
        
    Returns:
        Dictionary of permissions or None if error
    """
    try:
        # Get bot's member info in the chat
        me = await client.get_me()
        member = await client.get_chat_member(chat_id, me.id)
        
        # Extract permissions
        permissions = {
            'can_send_messages': getattr(member.privileges, 'can_post_messages', False) if member.privileges else False,
            'can_send_media': getattr(member.privileges, 'can_post_messages', False) if member.privileges else False,
            'is_admin': member.status in ['administrator', 'creator'],
            'status': member.status
        }
        
        log.debug(f"[VALIDATION] Bot {bot_index} permissions in {chat_id}: {permissions}")
        return permissions
        
    except Exception as e:
        log.error(f"[VALIDATION] Bot {bot_index} - Error getting permissions for {chat_id}: {e}")
        return None


async def validate_all_bots_access(
    clients: list,
    chat_id: int | str
) -> list[int]:
    """
    Validate all bots have access to a chat/channel.
    
    Args:
        clients: List of Pyrogram client instances
        chat_id: Chat ID or username to validate
        
    Returns:
        List of bot indices that have valid access
    """
    valid_bot_indices = []
    
    for i, client in enumerate(clients):
        is_valid, error_reason, chat_info = await validate_chat_access(client, chat_id, i)
        
        if is_valid:
            valid_bot_indices.append(i)
            log.info(f"[VALIDATION] ✅ Bot {i} has access to chat {chat_id}")
        else:
            log.warning(f"[VALIDATION] ❌ Bot {i} NO access to chat {chat_id}: {error_reason}")
    
    return valid_bot_indices


async def validate_bot_can_send_videos(
    client: Client,
    chat_id: int | str,
    bot_index: int
) -> Tuple[bool, str]:
    """
    Validate bot can send videos to a chat/channel.
    
    Args:
        client: Pyrogram client instance
        chat_id: Chat ID or username
        bot_index: Bot index for logging
        
    Returns:
        Tuple of (can_send, error_reason)
    """
    # First check basic access
    is_valid, error_reason, chat_info = await validate_chat_access(client, chat_id, bot_index)
    
    if not is_valid:
        return False, error_reason
    
    # Check permissions
    permissions = await get_bot_permissions(client, chat_id, bot_index)
    
    if permissions is None:
        return False, "Could not retrieve bot permissions"
    
    if not permissions.get('can_send_media', False):
        return False, "Bot does not have permission to send media"
    
    return True, ""


def format_validation_error(
    bot_index: int,
    bot_username: str,
    chat_id: int | str,
    error_type: str,
    error_message: str,
    job_id: str = None
) -> str:
    """
    Format a structured validation error message.
    
    Args:
        bot_index: Bot index
        bot_username: Bot username (with @)
        chat_id: Chat ID that failed
        error_type: Type of error (e.g., 'PEER_ERROR', 'PERMISSION_ERROR')
        error_message: Detailed error message
        job_id: Optional job ID
        
    Returns:
        Formatted error string
    """
    parts = [
        f"[UPLOAD] {error_type}",
        f"channel_id={chat_id}",
        f"bot_index={bot_index}",
        f"bot_username={bot_username}",
        f"reason={error_message}"
    ]
    
    if job_id:
        parts.append(f"job_id={job_id[:16]}")
    
    return " | ".join(parts)
