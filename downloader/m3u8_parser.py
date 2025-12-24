"""
M3U8 playlist parser.
Parses M3U8 playlists and selects best quality stream.
"""
import re
import aiohttp
from typing import Optional, List, Dict
from utils.logger import log


class M3U8Parser:
    """M3U8 playlist parser."""
    
    async def fetch_m3u8(self, url: str) -> Optional[str]:
        """
        Fetch M3U8 playlist content.
        
        Args:
            url: M3U8 URL
            
        Returns:
            M3U8 content as string, None if failed
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        content = await response.text()
                        log.debug(f"Fetched M3U8 playlist: {url}")
                        return content
                    else:
                        log.error(f"Failed to fetch M3U8: {url}, status={response.status}")
                        return None
        except Exception as e:
            log.error(f"Error fetching M3U8 from {url}: {e}")
            return None
    
    def is_master_playlist(self, content: str) -> bool:
        """
        Check if M3U8 is a master playlist (contains multiple quality streams).
        
        Args:
            content: M3U8 content
            
        Returns:
            True if master playlist, False otherwise
        """
        return '#EXT-X-STREAM-INF' in content
    
    def parse_master_playlist(self, content: str, base_url: str) -> List[Dict[str, any]]:
        """
        Parse master playlist and extract stream variants.
        
        Args:
            content: M3U8 master playlist content
            base_url: Base URL for resolving relative URLs
            
        Returns:
            List of stream variants with bandwidth, resolution, and URL
        """
        variants = []
        lines = content.strip().split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith('#EXT-X-STREAM-INF'):
                # Parse stream info
                bandwidth = None
                resolution = None
                
                # Extract bandwidth
                bandwidth_match = re.search(r'BANDWIDTH=(\d+)', line)
                if bandwidth_match:
                    bandwidth = int(bandwidth_match.group(1))
                
                # Extract resolution
                resolution_match = re.search(r'RESOLUTION=(\d+x\d+)', line)
                if resolution_match:
                    resolution = resolution_match.group(1)
                
                # Next line should be the stream URL
                if i + 1 < len(lines):
                    stream_url = lines[i + 1].strip()
                    
                    # Resolve relative URL
                    if not stream_url.startswith('http'):
                        # Get base URL without filename
                        base = base_url.rsplit('/', 1)[0]
                        stream_url = f"{base}/{stream_url}"
                    
                    variants.append({
                        'bandwidth': bandwidth,
                        'resolution': resolution,
                        'url': stream_url
                    })
                
                i += 2
            else:
                i += 1
        
        log.debug(f"Parsed {len(variants)} stream variants from master playlist")
        return variants
    
    async def get_best_quality(self, m3u8_url: str) -> Optional[str]:
        """
        Get best quality stream URL from M3U8.
        
        Args:
            m3u8_url: M3U8 URL (can be master or single stream)
            
        Returns:
            Best quality stream URL, or original URL if single stream
        """
        try:
            # Fetch M3U8 content
            content = await self.fetch_m3u8(m3u8_url)
            if not content:
                return None
            
            # Check if master playlist
            if self.is_master_playlist(content):
                log.info("Master playlist detected, selecting best quality")
                
                # Parse variants
                variants = self.parse_master_playlist(content, m3u8_url)
                
                if not variants:
                    log.warning("No variants found in master playlist")
                    return m3u8_url
                
                # Sort by bandwidth (highest first)
                variants.sort(key=lambda x: x['bandwidth'] or 0, reverse=True)
                
                best_variant = variants[0]
                log.info(f"Selected best quality: bandwidth={best_variant['bandwidth']}, resolution={best_variant['resolution']}")
                
                return best_variant['url']
            else:
                # Single stream playlist
                log.info("Single stream playlist detected")
                return m3u8_url
                
        except Exception as e:
            log.error(f"Error getting best quality from {m3u8_url}: {e}")
            return None


# Global M3U8 parser instance
m3u8_parser = M3U8Parser()
