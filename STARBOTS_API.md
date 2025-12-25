# Starbots API Integration Guide

## API Endpoint

Your Starbots API: `https://api.starbots.in/api/terabox`

## API Request Format

```
GET https://api.starbots.in/api/terabox?url=<terabox_link>
```

**Example:**
```
https://api.starbots.in/api/terabox?url=https://1024terabox.com/s/1bUYgChWi7CKQ9mlzZi3-Jg
```

## API Response Format

```json
{
  "errno": 0,
  "data": {
    "file": {
      "file_name": "GOOD.BOY.S01E03.720p.HIN-KOR.x265.ESub.mkv",
      "size": 412955837,
      "size_readable": "393.83 MB",
      "stream_url": "http://api.starbots.in/play/i/eyJhbGciOi...",
      "download_url": "https://api.iteraplay.workers.dev/download?token=...",
      "direct_link": "https://api.iteraplay.workers.dev/download?token=...",
      "thumb": "https://api.iteraplay.workers.dev/thumbnail?token=...",
      "duration": "01:09:15",
      "quality": "720p",
      "fs_id": 527078072181966,
      "md5": null,
      "emd5": null
    }
  }
}
```

## Key Fields

- **`errno`**: Status code (0 = success)
- **`data.file.stream_url`**: **M3U8 playlist URL** (this is what we need!)
- **`data.file.file_name`**: Original filename
- **`data.file.size`**: File size in bytes
- **`data.file.quality`**: Video quality (360p, 480p, 720p, etc.)
- **`data.file.duration`**: Video duration

## How Worker Uses This

1. **Worker receives job** from Redis queue with TeraBox link
2. **Calls Starbots API**: `GET /api/terabox?url={link}`
3. **Extracts `stream_url`** from response: `data.file.stream_url`
4. **`stream_url` IS the M3U8 URL** - ready to download with ffmpeg
5. **Downloads video** using ffmpeg with stream copy
6. **Uploads to Telegram** via multi-bot manager

## Configuration

Update your `.env` file:

```env
# Starbots TeraBox API
TERABOX_API_URL=https://api.starbots.in/api/terabox
```

## Worker Code Changes

The worker has been updated to:
- Call Starbots API with TeraBox link
- Extract `stream_url` from `data.file.stream_url`
- Use `stream_url` directly as M3U8 URL (no additional parsing needed)
- Handle API errors gracefully

## Error Handling

Worker handles:
- ✅ API timeout (30 seconds)
- ✅ Invalid response (errno != 0)
- ✅ Missing stream_url in response
- ✅ Network errors
- ✅ Invalid M3U8 format

## Testing

Test the API manually:

```bash
curl "https://api.starbots.in/api/terabox?url=https://1024terabox.com/s/1bUYgChWi7CKQ9mlzZi3-Jg"
```

Should return JSON with `stream_url` field.

## Notes

- The `stream_url` is a **JWT-encoded M3U8 URL** from your Starbots backend
- It contains the actual M3U8 playlist with multiple quality options
- FFmpeg will automatically select the best quality from the M3U8
- The URL is time-limited (expires after ~1 hour based on JWT)
- Worker should download immediately after getting the URL

## Complete Flow

```
User sends link
    ↓
Main bot validates link
    ↓
Main bot pushes job to Redis
    ↓
Worker consumes job
    ↓
Worker calls: GET /api/terabox?url={link}
    ↓
API returns: {"errno": 0, "data": {"file": {"stream_url": "..."}}}
    ↓
Worker extracts: stream_url
    ↓
Worker downloads: ffmpeg -i {stream_url} -c copy output.mp4
    ↓
Worker uploads to Telegram
    ↓
Worker deletes local file
    ↓
Done! ✅
```
