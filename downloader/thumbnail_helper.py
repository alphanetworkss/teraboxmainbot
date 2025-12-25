"""
Thumbnail helper for downloading and processing video thumbnails.
Downloads thumbnails from URLs and converts them to JPG format for embedding.
"""
import aiohttp
import asyncio
from pathlib import Path
from typing import Optional
from PIL import Image
from io import BytesIO
from utils.logger import log


async def download_thumbnail(thumb_url: str, output_path: Path) -> Optional[Path]:
    """
    Download thumbnail from URL and save as JPG.
    
    Handles various image formats (WebP, PNG, JPG) and converts to JPG
    for maximum compatibility with ffmpeg and Telegram.
    
    Args:
        thumb_url: Thumbnail image URL from API
        output_path: Path to save thumbnail (e.g., /tmp/thumb_abc123.jpg)
        
    Returns:
        Path to downloaded thumbnail if successful, None otherwise
    """
    try:
        log.info(f"[THUMB] DOWNLOADING | url={thumb_url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                thumb_url,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    # Read image data
                    image_data = await response.read()
                    
                    # Convert to JPG using PIL in thread pool (blocking operation)
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        _convert_to_jpg,
                        image_data,
                        output_path
                    )
                    
                    log.info(f"[THUMB] DOWNLOADED | file={output_path.name} | size={len(image_data)} bytes")
                    return output_path
                else:
                    log.error(f"[THUMB] DOWNLOAD_FAILED | status={response.status} | url={thumb_url}")
                    return None
                    
    except asyncio.TimeoutError:
        log.error(f"[THUMB] DOWNLOAD_TIMEOUT | url={thumb_url}")
        return None
    except Exception as e:
        log.error(f"[THUMB] DOWNLOAD_ERROR | error={type(e).__name__}: {e} | url={thumb_url}")
        return None


def _convert_to_jpg(image_data: bytes, output_path: Path) -> None:
    """
    Convert image data to JPG format (blocking operation).
    
    Args:
        image_data: Raw image bytes
        output_path: Path to save JPG file
    """
    try:
        # Open image from bytes
        image = Image.open(BytesIO(image_data))
        
        # Convert RGBA/LA/P to RGB if needed (for transparency)
        if image.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Save as JPG with good quality
        image.save(output_path, 'JPEG', quality=85, optimize=True)
        
    except Exception as e:
        log.error(f"[THUMB] CONVERT_ERROR | error={type(e).__name__}: {e}")
        raise
