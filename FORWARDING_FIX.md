# Complete Fix for "Forwarded from" and "Peer ID Invalid" Issues

## Current Status

✅ **New videos work** - Sent from main bot  
❌ **Duplicate videos fail** - "Peer id invalid: -1002813604442"  
❌ **Sometimes sent from client bot** - Should always be from main bot

## Root Cause

The **MAIN BOT** is not an administrator of the log channel.

## Complete Solution

### Step 1: Add Main Bot to Log Channel

1. Open your log channel: **TERABOX_upload_Channel**
2. Go to **Channel Info** → **Administrators**
3. Click **"Add Administrator"**
4. Search for your **MAIN BOT** (not the upload bots)
5. Add it with these permissions:
   - ✅ Post Messages
   - ✅ Delete Messages (optional)

### Step 2: Verify All Bots Are Added

Your log channel should have these admins:
- ✅ Upload Bot 1
- ✅ Upload Bot 2
- ✅ Upload Bot 3
- ✅ Upload Bot 4
- ✅ Upload Bot 5
- ✅ Upload Bot 6
- ✅ Upload Bot 7
- ✅ **MAIN BOT** ← This is the important one!

### Step 3: Restart BOTH Servers

**Important:** You must restart BOTH the main bot AND the worker:

```bash
# Terminal 1: Stop and restart main bot
# Press Ctrl+C to stop
python main_bot.py

# Terminal 2: Stop and restart worker
# Press Ctrl+C to stop
python worker.py
```

### Step 4: Test

1. **Test with a NEW link:**
   - Should download and send from main bot ✅
   - No "Forwarded from" ✅

2. **Test with the SAME link again (duplicate):**
   - Should send cached version from main bot ✅
   - No "Forwarded from" ✅
   - No "Peer id invalid" error ✅

## Why Both Servers Need Restart

- **Main bot:** Handles duplicate detection and sending cached videos
- **Worker:** Handles new downloads and uploads

Both use the main bot token to send videos, so both need to be restarted after adding the main bot to the channel.

## Expected Behavior After Fix

### New Video
```
User sends link
  ↓
Main bot checks database → Not found
  ↓
Main bot pushes job to Redis queue
  ↓
Worker downloads video
  ↓
Worker uploads to log channel (using upload bot)
  ↓
Main bot sends video to user (using copy_message)
  ↓
User receives video from MAIN BOT ✅
No "Forwarded from" ✅
```

### Duplicate Video
```
User sends same link
  ↓
Main bot checks database → Found!
  ↓
Main bot copies video from log channel
  ↓
Main bot sends to user
  ↓
User receives video from MAIN BOT ✅
No "Forwarded from" ✅
```

## Troubleshooting

### Still shows "Forwarded from"
- Restart both main bot and worker
- Make sure you're using the latest code

### Still shows "Peer id invalid"
- Main bot is not admin of log channel
- Add main bot as admin
- Restart both servers

### Video sent from wrong bot
- Check that worker is using `settings.main_bot_token`
- Restart worker server

## Quick Checklist

- [ ] Main bot added as admin to log channel
- [ ] All 7 upload bots added as admin to log channel
- [ ] Main bot restarted
- [ ] Worker restarted
- [ ] Tested with new link
- [ ] Tested with duplicate link
