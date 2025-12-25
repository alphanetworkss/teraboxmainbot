# TeraBox Telegram Bot System

Production-ready, scalable Telegram bot system for TeraBox video downloading with distributed architecture.

## 🏗️ Architecture

- **Main Bot Server**: Handles user interactions, link validation, duplicate detection
- **Worker Servers**: Process download jobs, upload videos, manage files
- **MongoDB**: Stores video records for duplicate detection
- **Redis**: Job queue for distributing work to workers
- **Multi-Bot Upload**: Multiple Telegram bots for parallel uploads and FloodWait avoidance

## ✨ Features

- ✅ TeraBox link validation (`/s/` and `?surl=` patterns)
- ✅ **Force subscribe channel** (optional, require users to join channel)
- ✅ SHA256-based duplicate detection
- ✅ Automatic best quality selection from M3U8 playlists
- ✅ FFmpeg stream copy (no re-encoding)
- ✅ Multi-bot upload with round-robin selection
- ✅ FloodWait handling with automatic retry
- ✅ Log channel storage with user forwarding
- ✅ Automatic file cleanup
- ✅ Concurrent job processing
- ✅ Production-ready logging

## 📋 Requirements

- Python 3.11+
- FFmpeg (installed and in PATH)
- MongoDB server
- Redis server
- Multiple Telegram bot tokens (3-5 recommended)
- Telegram log channel

## 🚀 Installation

### 1. Clone and Setup

```bash
cd "e:\Terabox dowanloader\terabox_bot_system"
pip install -r requirements.txt
```

### 2. Install FFmpeg

**Windows:**
- Download from https://ffmpeg.org/download.html
- Add to PATH

**Linux:**
```bash
sudo apt update
sudo apt install ffmpeg
```

### 3. Setup MongoDB

**Local:**
```bash
# Install MongoDB Community Edition
# Start MongoDB service
```

**Cloud (MongoDB Atlas):**
- Create free cluster at https://www.mongodb.com/cloud/atlas
- Get connection string

### 4. Setup Redis

**Local:**
```bash
# Windows: Download from https://github.com/microsoftarchive/redis/releases
# Linux: sudo apt install redis-server
```

**Cloud (Redis Cloud):**
- Create free database at https://redis.com/try-free/

### 5. Configure Environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Main bot token
MAIN_BOT_TOKEN=your_main_bot_token

# Telegram API credentials
API_ID=123
API_HASH=xxx

# Upload bot tokens (comma-separated)
UPLOAD_BOT_TOKENS=token1,token2,token3

# Log channel ID (create a private channel, add bots as admin)
LOG_CHANNEL_ID=-1001234567890

# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=terabox_bot

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# TeraBox API
TERABOX_API_URL=https://api.starbots.in/api/terabox

# Worker settings
MAX_CONCURRENT_DOWNLOADS=3
DOWNLOAD_DIR=./downloads
```

### 6. Create Log Channel

1. Create a private Telegram channel
2. Add all your upload bots as administrators
3. Get channel ID using [@userinfobot](https://t.me/userinfobot)
4. Add ID to `.env` as `LOG_CHANNEL_ID`

### 7. Setup Force Subscribe (Optional)

To require users to join a channel before using the bot:

1. Create a public or private channel
2. Add your main bot as administrator to the channel
3. Get channel ID:
   - For public channels: Use `@channel_username` or get ID with [@userinfobot](https://t.me/userinfobot)
   - For private channels: Get ID with [@userinfobot](https://t.me/userinfobot) (format: -100xxxxxxxxxx)
4. Add to `.env`:
   ```env
   FORCE_SUBSCRIBE_CHANNEL_ID=-1001234567890
   ```
5. To disable force subscribe, set to `0`:
   ```env
   FORCE_SUBSCRIBE_CHANNEL_ID=0
   ```

**How it works:**
- Users who haven't joined will see a "Join Channel" button
- After joining, they click "I Joined" to verify
- Bot checks membership before processing any requests

## 🎯 Usage

### Run Main Bot

```bash
python main_bot.py
```

### Run Worker(s)

Run 3-4 workers on separate servers or terminals:

```bash
# Worker 1
python worker.py

# Worker 2 (different terminal/server)
python worker.py

# Worker 3 (different terminal/server)
python worker.py
```

---

## 🖥️ Worker Server Setup Guide

### Overview

Workers are separate processes that consume download jobs from the Redis queue. For production, you should run workers on **dedicated servers** for optimal performance and scalability.

### Architecture Options

#### Option 1: Single Server (Development/Small Scale)
- Main bot + 2-3 workers on same machine
- Good for: Testing, low traffic (< 1000 users)
- Requirements: 4GB RAM, 2 CPU cores

#### Option 2: Separate Servers (Recommended for Production)
- Main bot on Server 1
- Workers on Servers 2, 3, 4
- Good for: High traffic (20k+ users)
- Requirements per worker: 2GB RAM, 1-2 CPU cores

#### Option 3: Cloud/VPS Deployment
- Main bot on primary VPS
- Workers on cheap VPS instances (DigitalOcean, Hetzner, etc.)
- Good for: Scalable production deployment

---

### Worker Server Setup (Separate Server)

#### 1. Prepare Worker Server

**Install Python 3.11+:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# CentOS/RHEL
sudo yum install python3.11
```

**Install FFmpeg:**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg

# Verify installation
ffmpeg -version
```

#### 2. Clone Project on Worker Server

```bash
# Create project directory
mkdir -p /opt/terabox_bot
cd /opt/terabox_bot

# Copy project files from main server
# Option A: Using SCP
scp -r user@main-server:/path/to/terabox_bot_system/* .

# Option B: Using Git
git clone your-repo-url .

# Option C: Manual upload via FTP/SFTP
```

#### 3. Install Dependencies

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

#### 4. Configure Worker Environment

Create `.env` file on worker server:

```bash
nano .env
```

**Worker `.env` configuration:**
```env
# Telegram API credentials (SAME as main bot)
API_ID=123
API_HASH=xxx

# Upload bot tokens (SAME as main bot)
UPLOAD_BOT_TOKENS=token1,token2,token3

# Log channel ID (SAME as main bot)
LOG_CHANNEL_ID=-1001234567890

# MongoDB connection (point to main server or shared MongoDB)
MONGODB_URI=mongodb://main-server-ip:27017
# OR use MongoDB Atlas for shared access
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/terabox_bot

# Redis connection (point to main server or shared Redis)
REDIS_HOST=main-server-ip
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# TeraBox API (SAME as main bot)
TERABOX_API_URL=https://your-api-endpoint.com/extract

# Worker settings
MAX_CONCURRENT_DOWNLOADS=3
DOWNLOAD_DIR=./downloads
LOG_LEVEL=INFO
```

**Important Notes:**
- MongoDB and Redis must be accessible from worker server
- If MongoDB/Redis are on main server, ensure firewall allows connections
- For production, use MongoDB Atlas and Redis Cloud for shared access

#### 5. Configure Firewall (if MongoDB/Redis on main server)

**On Main Server:**
```bash
# Allow MongoDB connections from worker IPs
sudo ufw allow from worker-ip-1 to any port 27017
sudo ufw allow from worker-ip-2 to any port 27017

# Allow Redis connections from worker IPs
sudo ufw allow from worker-ip-1 to any port 6379
sudo ufw allow from worker-ip-2 to any port 6379
```

**Configure MongoDB to accept remote connections:**
```bash
# Edit MongoDB config
sudo nano /etc/mongod.conf

# Change bindIp to:
net:
  bindIp: 0.0.0.0  # Allow all IPs (or specify worker IPs)

# Restart MongoDB
sudo systemctl restart mongod
```

**Configure Redis to accept remote connections:**
```bash
# Edit Redis config
sudo nano /etc/redis/redis.conf

# Change bind to:
bind 0.0.0.0

# Set password:
requirepass your_strong_password

# Restart Redis
sudo systemctl restart redis
```

#### 6. Test Worker Connection

```bash
# Activate virtual environment
source venv/bin/activate

# Test worker
python worker.py
```

You should see:
```
Starting worker server...
Connecting to MongoDB: mongodb://...
Successfully connected to MongoDB
Connecting to Redis: ...
Successfully connected to Redis
Initializing 3 upload bot clients
Worker server started successfully
Starting job consumer
```

#### 7. Run Worker as System Service

Create systemd service file:

```bash
sudo nano /etc/systemd/system/terabox-worker.service
```

**Service configuration:**
```ini
[Unit]
Description=TeraBox Worker Server
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/opt/terabox_bot
Environment="PATH=/opt/terabox_bot/venv/bin"
ExecStart=/opt/terabox_bot/venv/bin/python worker.py
Restart=always
RestartSec=10

# Logging
StandardOutput=append:/var/log/terabox-worker.log
StandardError=append:/var/log/terabox-worker-error.log

[Install]
WantedBy=multi-user.target
```

**Enable and start service:**
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable terabox-worker

# Start service
sudo systemctl start terabox-worker

# Check status
sudo systemctl status terabox-worker

# View logs
sudo journalctl -u terabox-worker -f
```

#### 8. Running Multiple Workers on Same Server

Create multiple service files:

```bash
# Worker 1
sudo cp /etc/systemd/system/terabox-worker.service /etc/systemd/system/terabox-worker@1.service

# Worker 2
sudo cp /etc/systemd/system/terabox-worker.service /etc/systemd/system/terabox-worker@2.service

# Worker 3
sudo cp /etc/systemd/system/terabox-worker.service /etc/systemd/system/terabox-worker@3.service
```

Edit each service to use different log files:
```bash
sudo nano /etc/systemd/system/terabox-worker@1.service
# Change StandardOutput and StandardError to:
StandardOutput=append:/var/log/terabox-worker-1.log
StandardError=append:/var/log/terabox-worker-1-error.log
```

Start all workers:
```bash
sudo systemctl daemon-reload
sudo systemctl enable terabox-worker@{1,2,3}
sudo systemctl start terabox-worker@{1,2,3}

# Check all workers
sudo systemctl status terabox-worker@*
```

---

### Worker Monitoring & Management

#### Check Worker Status
```bash
# System service status
sudo systemctl status terabox-worker

# View real-time logs
sudo journalctl -u terabox-worker -f

# View application logs
tail -f /opt/terabox_bot/logs/worker.log
```

#### Restart Worker
```bash
sudo systemctl restart terabox-worker
```

#### Stop Worker
```bash
sudo systemctl stop terabox-worker
```

#### Worker Performance Monitoring
```bash
# Check CPU/Memory usage
htop

# Check disk usage
df -h

# Check download directory size
du -sh /opt/terabox_bot/downloads
```

---

### Scaling Workers

#### Add More Workers
1. Deploy new server
2. Follow worker setup steps 1-7
3. Workers automatically connect to shared Redis queue
4. No changes needed to main bot

#### Remove Workers
1. Stop worker service: `sudo systemctl stop terabox-worker`
2. Disable service: `sudo systemctl disable terabox-worker`
3. Jobs will be processed by remaining workers

---

### Troubleshooting Workers

#### Worker Can't Connect to MongoDB
```bash
# Test MongoDB connection
mongo mongodb://main-server-ip:27017

# Check firewall
sudo ufw status

# Check MongoDB is listening
sudo netstat -tulpn | grep 27017
```

#### Worker Can't Connect to Redis
```bash
# Test Redis connection
redis-cli -h main-server-ip -p 6379 -a your_password ping

# Should return: PONG
```

#### Worker Not Processing Jobs
```bash
# Check Redis queue size
redis-cli -h main-server-ip -p 6379 -a your_password
> LLEN terabox:download_jobs

# Check worker logs
tail -f logs/worker.log

# Restart worker
sudo systemctl restart terabox-worker
```

#### FFmpeg Errors
```bash
# Verify FFmpeg installation
ffmpeg -version

# Check FFmpeg can access M3U8 URLs
ffmpeg -i "https://test-m3u8-url.m3u8" -t 5 test.mp4
```

---

## 🚀 Production Deployment

### Production Deployment

Use process managers like `systemd`, `supervisor`, or `pm2`:

**systemd example:**

```ini
# /etc/systemd/system/terabox-main-bot.service
[Unit]
Description=TeraBox Main Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/terabox_bot_system
ExecStart=/usr/bin/python3 main_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/terabox-worker@.service
[Unit]
Description=TeraBox Worker %i
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/terabox_bot_system
ExecStart=/usr/bin/python3 worker.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Start services:
```bash
sudo systemctl start terabox-main-bot
sudo systemctl start terabox-worker@1
sudo systemctl start terabox-worker@2
sudo systemctl start terabox-worker@3
```

## 📊 Monitoring

Logs are stored in `logs/` directory:
- `main_bot.log` - Main bot logs
- `worker.log` - Worker logs
- `*_errors.log` - Error-only logs

Monitor queue size:
```python
from queue import job_queue
import asyncio

async def check_queue():
    size = await job_queue.get_queue_size()
    print(f"Queue size: {size}")

asyncio.run(check_queue())
```

## 🔧 Configuration

### Adjust Concurrent Downloads

Edit `.env`:
```env
MAX_CONCURRENT_DOWNLOADS=5  # Increase for more powerful servers
```

### Add More Upload Bots

1. Create new bots with [@BotFather](https://t.me/BotFather)
2. Add tokens to `.env`:
```env
UPLOAD_BOT_TOKENS=token1,token2,token3,token4,token5
```
3. Add bots as admin to log channel
4. Restart services

## 🐛 Troubleshooting

### FFmpeg not found
```bash
# Verify FFmpeg installation
ffmpeg -version

# Add to PATH if needed
```

### MongoDB connection failed
- Check MongoDB is running: `sudo systemctl status mongod`
- Verify connection string in `.env`

### Redis connection failed
- Check Redis is running: `sudo systemctl status redis`
- Verify host/port in `.env`

### FloodWait errors
- Add more upload bots
- Reduce concurrent downloads
- Check bot limits with [@BotFather](https://t.me/BotFather)

### Files not cleaning up
- Check disk space
- Verify `DOWNLOAD_DIR` permissions
- Check logs for cleanup errors

## 📝 API Integration

The worker expects your TeraBox API to return JSON with M3U8 URL:

```json
{
  "m3u8_url": "https://example.com/video.m3u8"
}
```

Or:
```json
{
  "url": "https://example.com/video.m3u8"
}
```

Adjust `fetch_m3u8_from_api()` in `worker.py` if your API format differs.

## 🔒 Security

- Never commit `.env` file
- Use environment variables for all secrets
- Restrict log channel access
- Use MongoDB authentication in production
- Use Redis password in production

## 📈 Scaling

### Horizontal Scaling
- Run multiple worker servers
- Use load balancer for main bot (if needed)
- Use MongoDB replica set
- Use Redis cluster

### Vertical Scaling
- Increase `MAX_CONCURRENT_DOWNLOADS`
- Add more CPU/RAM to worker servers
- Use SSD for faster file I/O

## 📄 License

This project is provided as-is for educational and production use.

## 🤝 Support

For issues or questions:
1. Check logs in `logs/` directory
2. Verify configuration in `.env`
3. Review this README

---

**Built with ❤️ for high-scale Telegram bot deployments**
