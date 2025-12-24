"""
TeraBox link validator.
Validates TeraBox URLs and extracts share IDs.
"""
import re
from urllib.parse import urlparse, parse_qs
from config.constants import VALID_TERABOX_PATTERNS
from utils.logger import log


def is_valid_terabox_link(url: str) -> bool:
    """
    Validate if the URL is a valid TeraBox link.
    
    A link is valid ONLY IF:
    - URL contains "/s/"
    - OR URL contains "?surl="
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid TeraBox link, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    url = url.strip()
    
    # Check if URL contains any of the valid patterns
    for pattern in VALID_TERABOX_PATTERNS:
        if pattern in url:
            log.debug(f"Valid TeraBox link detected: {url}")
            return True
    
    log.debug(f"Invalid TeraBox link: {url}")
    return False


def extract_share_id(url: str) -> str | None:
    """
    Extract share ID from TeraBox URL.
    
    Args:
        url: TeraBox URL
        
    Returns:
        Share ID if found, None otherwise
    """
    try:
        # Pattern 1: /s/xxxxx
        if '/s/' in url:
            match = re.search(r'/s/([a-zA-Z0-9_-]+)', url)
            if match:
                share_id = match.group(1)
                log.debug(f"Extracted share ID from /s/ pattern: {share_id}")
                return share_id
        
        # Pattern 2: ?surl=xxxxx
        if '?surl=' in url or '&surl=' in url:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            if 'surl' in params:
                share_id = params['surl'][0]
                log.debug(f"Extracted share ID from ?surl= pattern: {share_id}")
                return share_id
        
        log.warning(f"Could not extract share ID from URL: {url}")
        return None
        
    except Exception as e:
        log.error(f"Error extracting share ID from {url}: {e}")
        return None


def normalize_terabox_url(url: str) -> str:
    """
    Normalize TeraBox URL for consistent hashing.
    
    Args:
        url: TeraBox URL
        
    Returns:
        Normalized URL
    """
    # Remove trailing slashes and whitespace
    url = url.strip().rstrip('/')
    
    # Convert to lowercase for consistency
    url = url.lower()
    
    return url
