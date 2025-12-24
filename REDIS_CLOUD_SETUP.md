# Redis Cloud Configuration Guide

Based on your Redis Cloud database screenshot, here's how to configure your `.env` file:

## Your Redis Details

- **Database name**: starbots
- **Database ID**: #13852050
- **Public endpoint**: redis-16569.c212.ap-south-1-1.ec2.redislabs.com:16569

## Configuration Steps

### 1. Get Your Redis Password

You need to get the password from Redis Cloud:

1. Click on the database "starbots"
2. Go to "Configuration" tab
3. Look for "Default user password" or "Security" section
4. Copy the password

### 2. Update Your .env File

Edit your `.env` file in the `terabox_bot_system` directory:

```env
# ===== REDIS CONFIGURATION =====
# Redis Cloud connection
REDIS_HOST=redis-16569.c212.ap-south-1-1.ec2.redislabs.com
REDIS_PORT=16569
REDIS_DB=0
REDIS_PASSWORD=your_redis_password_here
```

**Important:**
- Replace `your_redis_password_here` with the actual password from Redis Cloud
- The host and port are extracted from the endpoint: `redis-16569.c212.ap-south-1-1.ec2.redislabs.com:16569`

### 3. Test Connection

After updating `.env`, test the connection:

```bash
# Using redis-cli
redis-cli -h redis-16569.c212.ap-south-1-1.ec2.redislabs.com -p 16569 -a your_password ping

# Should return: PONG
```

Or test with Python:

```python
import redis

r = redis.Redis(
    host='redis-16569.c212.ap-south-1-1.ec2.redislabs.com',
    port=16569,
    password='your_password',
    decode_responses=True
)

print(r.ping())  # Should print: True
```

### 4. Benefits of Redis Cloud

✅ **No local Redis installation needed**
✅ **Accessible from all worker servers**
✅ **Automatic backups and high availability**
✅ **Free tier: 30MB storage (sufficient for job queue)**
✅ **No firewall configuration needed**

### 5. Complete .env Example

```env
# ===== TELEGRAM BOT CONFIGURATION =====
MAIN_BOT_TOKEN=your_main_bot_token
API_ID=123
API_HASH=xxx
UPLOAD_BOT_TOKENS=token1,token2,token3
LOG_CHANNEL_ID=-1001234567890
FORCE_SUBSCRIBE_CHANNEL_ID=0

# ===== DATABASE CONFIGURATION =====
# You can also use MongoDB Atlas (cloud MongoDB)
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=terabox_bot

# ===== REDIS CONFIGURATION =====
# Redis Cloud (from your screenshot)
REDIS_HOST=redis-16569.c212.ap-south-1-1.ec2.redislabs.com
REDIS_PORT=16569
REDIS_DB=0
REDIS_PASSWORD=your_actual_redis_password

# ===== TERABOX API CONFIGURATION =====
TERABOX_API_URL=https://your-api-endpoint.com/extract

# ===== WORKER CONFIGURATION =====
MAX_CONCURRENT_DOWNLOADS=3
DOWNLOAD_DIR=./downloads

# ===== LOGGING =====
LOG_LEVEL=INFO
LOG_FILE_MAX_SIZE=100MB
```

## Multi-Server Setup with Redis Cloud

With Redis Cloud, all your servers can connect to the same Redis instance:

```
Server 1 (Main Bot):
  - main_bot.py
  - Connects to Redis Cloud ✓
  - MongoDB (local or Atlas)

Server 2 (Worker 1):
  - worker.py
  - Connects to Redis Cloud ✓
  - No local Redis needed!

Server 3 (Worker 2):
  - worker.py
  - Connects to Redis Cloud ✓
  - No local Redis needed!
```

## Security Notes

⚠️ **Keep your Redis password secure**
- Don't commit `.env` to Git (already in `.gitignore`)
- Use strong password from Redis Cloud
- Redis Cloud automatically uses TLS encryption

## Troubleshooting

### Connection Refused
- Check if Redis password is correct
- Verify endpoint URL is exactly as shown in Redis Cloud
- Ensure your IP is not blocked (Redis Cloud free tier allows all IPs)

### Authentication Failed
- Double-check the password in Redis Cloud dashboard
- Make sure there are no extra spaces in `.env` file

### Timeout Errors
- Check your internet connection
- Verify firewall allows outbound connections on port 16569

## Next Steps

1. ✅ Get Redis password from Redis Cloud dashboard
2. ✅ Update `.env` file with Redis configuration
3. ✅ Test connection with `redis-cli` or Python
4. ✅ Start your bot: `python main_bot.py`
5. ✅ Start workers: `python worker.py`

All servers will now share the same Redis queue automatically! 🎉
