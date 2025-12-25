# DNS Fix for Redis Cloud Connection

## Problem
Your DNS server (JioFiber router at 192.168.31.1) cannot resolve the Redis Cloud hostname:
`redis-16569.c212.ap-south-1-1.ec2.redislabs.com`

Error: `Non-existent domain`

## Solutions

### Solution 1: Change DNS to Google DNS (Recommended)

**Windows 10/11:**

1. Press `Win + R`, type `ncpa.cpl`, press Enter
2. Right-click your active network connection (Wi-Fi or Ethernet)
3. Click **Properties**
4. Select **Internet Protocol Version 4 (TCP/IPv4)**
5. Click **Properties**
6. Select **Use the following DNS server addresses:**
   - **Preferred DNS**: `8.8.8.8` (Google DNS)
   - **Alternate DNS**: `8.8.4.4` (Google DNS)
7. Click **OK** on all windows
8. Open Command Prompt and run:
   ```cmd
   ipconfig /flushdns
   ```

### Solution 2: Add to Windows Hosts File (Quick Fix)

1. Open Notepad as Administrator
2. Open file: `C:\Windows\System32\drivers\etc\hosts`
3. Add this line at the end:
   ```
   13.232.219.134 redis-16569.c212.ap-south-1-1.ec2.redislabs.com
   ```
4. Save and close
5. Run in Command Prompt:
   ```cmd
   ipconfig /flushdns
   ```

**Note:** You need to find the actual IP address first. Let me help you with that.

### Solution 3: Use Cloudflare DNS

Same steps as Solution 1, but use:
- **Preferred DNS**: `1.1.1.1` (Cloudflare)
- **Alternate DNS**: `1.0.0.1` (Cloudflare)

### Solution 4: Use Redis Cloud IP Directly

Instead of hostname, use the IP address directly in your code:

```python
import redis

r = redis.Redis(
    host='13.232.219.134',  # IP instead of hostname
    port=16569,
    password='cLq4P1GbvewTeWeHMfv2lvXEN7ewmVBG',
    decode_responses=True,
    ssl=True,
    ssl_cert_reqs=None
)
```

## Recommended Steps

1. **Try Solution 1 first** (Change to Google DNS) - This is the most reliable
2. After changing DNS, wait 30 seconds
3. Run `ipconfig /flushdns` in Command Prompt
4. Test connection again with `python test\test.py`

## Why This Happens

JioFiber's DNS server sometimes has issues resolving certain cloud service domains, especially AWS-based services (Redis Cloud uses AWS). Using Google DNS or Cloudflare DNS resolves this issue.

## Verify DNS Change Worked

After changing DNS, test with:
```cmd
nslookup redis-16569.c212.ap-south-1-1.ec2.redislabs.com 8.8.8.8
```

Should return an IP address instead of "Non-existent domain".
