# TeraBox Downloader Bot

A powerful Telegram bot for downloading and uploading TeraBox videos with parallel processing, multiple upload bots, and automatic thumbnail embedding.

## Features

- ✅ **Parallel Processing**: Download up to 10 videos simultaneously
- ✅ **Multiple Upload Bots**: Distribute uploads across multiple bot accounts
- ✅ **Automatic Thumbnail Embedding**: Embeds video thumbnails automatically
- ✅ **Duplicate Detection**: Prevents re-downloading the same video
- ✅ **Progress Tracking**: Real-time download/upload progress with speed and ETA
- ✅ **Auto-Delete**: Videos auto-delete from user chat after 1 hour
- ✅ **Force Subscribe**: Require users to join channels before using the bot
- ✅ **Redis Queue**: Efficient job queue management
- ✅ **MongoDB Storage**: Persistent video record storage

## Prerequisites

- Python 3.10 or higher
- MongoDB database
- Redis server
- FFmpeg installed
- Multiple Telegram bot tokens (for parallel uploads)

## Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd teraboxmainbot-main
```

### 2. Create Virtual Environment (Recommended)

Using a virtual environment isolates your bot's dependencies from system Python packages.

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

Your terminal prompt should now show `(venv)` indicating the virtual environment is active.

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install FFmpeg

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg -y
```

**CentOS/RHEL:**
```bash
sudo yum install ffmpeg -y
```

### 4. Configure Environment Variables

Copy the example `.env` file and edit it:

```bash
cp .env.example .env
nano .env
```

**Required Configuration:**

```env
# Main Bot Token
MAIN_BOT_TOKEN=your_main_bot_token

# Upload Bot Tokens (comma-separated for parallel uploads)
UPLOAD_BOT_TOKENS=bot1_token,bot2_token,bot3_token,bot4_token,bot5_token

# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=terabox_bot

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Telegram Settings
LOG_CHANNEL_ID=-1001234567890  # Your log channel ID

# Force Subscribe (optional)
FORCE_SUBSCRIBE_CHANNEL_ID=-1001234567890
FORCE_SUBSCRIBE_CHANNEL_USERNAME=@YourChannel

# Parallel Processing
MAX_CONCURRENT_DOWNLOADS=10
CPU_HIGH_THRESHOLD=75.0
CPU_HIGH_DURATION=5
GLOBAL_ACTIVE_LIMIT_MAX=10
UPLOAD_ACTIVE_LIMIT_MAX=10

# TeraBox API
TERABOX_API_URL=http://api.starbots.in/terabox
```

## Hosting on VPS with Screen

### Why Use Screen?

`screen` allows you to run processes in the background that persist even after you disconnect from SSH. This is perfect for hosting bots on a VPS.

### Step 1: Install Screen

```bash
sudo apt update
sudo apt install screen -y
```

### Step 2: Start the Main Bot

```bash
# Create a new screen session named "mainbot"
screen -S mainbot

# Activate virtual environment
source venv/bin/activate

# Run the main bot
python main_bot.py

# Detach from screen: Press Ctrl+A, then D
```

### Step 3: Start the Worker

```bash
# Create a new screen session named "worker"
screen -S worker

# Activate virtual environment
source venv/bin/activate

# Run the worker
python worker.py

# Detach from screen: Press Ctrl+A, then D
```

### Managing Screen Sessions

**List all screen sessions:**
```bash
screen -ls
```

**Reattach to a session:**
```bash
screen -r mainbot   # Attach to main bot
screen -r worker    # Attach to worker
```

**Kill a session:**
```bash
screen -X -S mainbot quit   # Kill main bot session
screen -X -S worker quit    # Kill worker session
```

**View logs while detached:**
```bash
# Attach to session in read-only mode
screen -x mainbot
screen -x worker
```

## Quick Start Commands

### Start Both Services

```bash
# Start main bot (with venv)
screen -dmS mainbot bash -c 'source venv/bin/activate && python main_bot.py'

# Start worker (with venv)
screen -dmS worker bash -c 'source venv/bin/activate && python worker.py'

# Check if running
screen -ls
```

### Stop Both Services

```bash
screen -X -S mainbot quit
screen -X -S worker quit
```

### Restart Services

```bash
# Restart main bot
screen -X -S mainbot quit
screen -dmS mainbot bash -c 'source venv/bin/activate && python main_bot.py'

# Restart worker
screen -X -S worker quit
screen -dmS worker bash -c 'source venv/bin/activate && python worker.py'
```

## Utility Scripts

### Check Queue Status

```bash
python check_queue.py
```

Shows the number of jobs waiting in the Redis queue.

### Clear Queue

```bash
python clear_queue.py
```

Clears all pending jobs from the queue (requires confirmation).

### Cleanup Orphaned Files

```bash
python cleanup_files.py
```

Removes orphaned video files from the downloads directory (requires confirmation).

## Monitoring

### View Logs in Real-Time

```bash
# Attach to main bot screen
screen -r mainbot

# Attach to worker screen
screen -r worker

# Or view log file
tail -f logs.txt
```

### Check System Resources

```bash
# CPU and Memory usage
htop

# Disk space
df -h

# Network usage
iftop
```

## Troubleshooting

### Bot Not Responding

1. Check if the process is running:
   ```bash
   screen -ls
   ```

2. Reattach to screen and check logs:
   ```bash
   screen -r mainbot
   ```

3. Restart the bot:
   ```bash
   screen -X -S mainbot quit
   screen -dmS mainbot python main_bot.py
   ```

### Worker Not Processing Jobs

1. Check Redis connection:
   ```bash
   redis-cli ping
   ```

2. Check queue size:
   ```bash
   python check_queue.py
   ```

3. Restart worker:
   ```bash
   screen -X -S worker quit
   screen -dmS worker python worker.py
   ```

### Storage Full

1. Check disk usage:
   ```bash
   df -h
   ```

2. Clean up orphaned files:
   ```bash
   python cleanup_files.py
   ```

3. Clear old MongoDB records (optional):
   ```bash
   mongo terabox_bot --eval "db.videos.deleteMany({created_at: {\$lt: new Date(Date.now() - 30*24*60*60*1000)}})"
   ```

### FILE_PART_INVALID Errors

These errors are usually harmless and caused by Telegram rate limiting during parallel uploads. The uploads still succeed due to Pyrogram's retry logic.

**Solution**: Add more upload bot tokens to distribute the load.

## Performance Optimization

### For Powerful Servers

Increase parallel processing in `.env`:

```env
MAX_CONCURRENT_DOWNLOADS=20
GLOBAL_ACTIVE_LIMIT_MAX=20
UPLOAD_ACTIVE_LIMIT_MAX=20
CPU_HIGH_THRESHOLD=85.0
```

### For Limited Resources

Reduce parallel processing:

```env
MAX_CONCURRENT_DOWNLOADS=3
GLOBAL_ACTIVE_LIMIT_MAX=5
UPLOAD_ACTIVE_LIMIT_MAX=5
CPU_HIGH_THRESHOLD=60.0
```

## Auto-Start on Boot (Optional)

### Using Systemd

Create service files for automatic startup:

**Main Bot Service:**
```bash
sudo nano /etc/systemd/system/terabox-mainbot.service
```

```ini
[Unit]
Description=TeraBox Main Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/teraboxmainbot-main
ExecStart=/path/to/teraboxmainbot-main/venv/bin/python main_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Worker Service:**
```bash
sudo nano /etc/systemd/system/terabox-worker.service
```

```ini
[Unit]
Description=TeraBox Worker
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/teraboxmainbot-main
ExecStart=/path/to/teraboxmainbot-main/venv/bin/python worker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start services:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable terabox-mainbot
sudo systemctl enable terabox-worker
sudo systemctl start terabox-mainbot
sudo systemctl start terabox-worker
```

**Check status:**
```bash
sudo systemctl status terabox-mainbot
sudo systemctl status terabox-worker
```

## Architecture

```
┌─────────────────┐
│   Telegram      │
│   Users         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Main Bot      │  ← Receives links, queues jobs
│   (main_bot.py) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Redis Queue   │  ← Job queue
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Worker        │  ← Downloads & uploads (10 parallel)
│   (worker.py)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Upload Bots    │  ← Multiple bots for parallel uploads
│  (8 bots)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Log Channel    │  ← Stores videos
└─────────────────┘
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License.

## Support

For issues and questions, please open an issue on GitHub or contact [@Thestarbots](https://t.me/Thestarbots).
