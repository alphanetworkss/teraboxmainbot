"""Application constants."""

# TeraBox URL validation patterns
VALID_TERABOX_PATTERNS = ['/s/', '?surl=']

# Error messages
ERROR_INVALID_LINK = "❌ Invalid TeraBox link!\n\nPlease send a valid TeraBox link containing:\n• /s/ OR\n• ?surl="
ERROR_PROCESSING = "❌ Error processing your request. Please try again later."
ERROR_DOWNLOAD_FAILED = "❌ Download failed. The video may be unavailable or the link is expired."
ERROR_UPLOAD_FAILED = "❌ Upload failed. Please try again."
ERROR_NOT_SUBSCRIBED = "❌ You must join our channel to use this bot!\n\n👉 Join: {channel_link}\n\nAfter joining, send /start again."

# Success messages
MSG_PROCESSING = "⏳ Processing your request...\nPlease wait while we download and upload your video."
MSG_DUPLICATE_FOUND = "✅ This video was already downloaded!\nSending you the cached version..."
MSG_DOWNLOADING = "📥 Downloading video... {progress}%"
MSG_UPLOADING = "📤 Uploading video... {progress}%"
MSG_SUCCESS = "✅ Video uploaded successfully!"

# Redis queue names
QUEUE_DOWNLOAD_JOBS = 'terabox:download_jobs'

# File settings
MAX_FILE_SIZE_MB = 2000  # 2GB limit for Telegram
TEMP_FILE_PREFIX = 'terabox_'
VIDEO_EXTENSION = '.mp4'

# Job processing
JOB_TIMEOUT_SECONDS = 3600  # 1 hour max per job
WORKER_POLL_INTERVAL = 1  # seconds

# FFmpeg settings
FFMPEG_TIMEOUT = 3600  # 1 hour max for ffmpeg process
