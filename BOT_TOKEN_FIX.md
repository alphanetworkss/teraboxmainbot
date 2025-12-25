# Bot Token Validation Issue

## Error
```
[400 ACCESS_TOKEN_INVALID] - The bot access token is invalid
```

## Cause
The upload bot tokens in your `.env` file are invalid or expired.

## How to Fix

### 1. Verify Tokens with @BotFather

Open Telegram and talk to [@BotFather](https://t.me/BotFather):

1. Send `/mybots` to see all your bots
2. Select each bot
3. Click "API Token" to get/regenerate the token
4. Copy the **complete token** (format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Test a Single Token

Before adding all tokens, test one first:

```python
# test_token.py
from pyrogram import Client

API_ID = 123
API_HASH = "xxx"
BOT_TOKEN = "your_bot_token_here"  # Test one token

async def test():
    client = Client("test_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
    await client.start()
    me = await client.get_me()
    print(f"✅ Bot works: @{me.username}")
    await client.stop()

import asyncio
asyncio.run(test())
```

Run:
```bash
python test_token.py
```

### 3. Common Token Issues

❌ **Wrong format:**
```
8433884917:AAGZKK749fTwBvWRepHnWnd-LS2MxnXGxW  # Missing characters?
```

✅ **Correct format:**
```
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-1234567890
```

❌ **Extra spaces or line breaks:**
```env
UPLOAD_BOT_TOKENS=token1 ,token2, token3  # Spaces before commas
```

✅ **No spaces:**
```env
UPLOAD_BOT_TOKENS=token1,token2,token3
```

### 4. Get New Tokens

If tokens are revoked, create new bots:

1. Talk to [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Follow prompts to create bot
4. Copy the token
5. Repeat for 3-5 bots

### 5. Update .env File

```env
# Use ONLY valid, active bot tokens
UPLOAD_BOT_TOKENS=bot1_token,bot2_token,bot3_token

# Example (these are fake, use your real tokens):
UPLOAD_BOT_TOKENS=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz,9876543210:XYZwvuTSRqponMLKjihgfeDCBA
```

### 6. Minimum Requirement

You need **at least 1 valid token** for the bot to work. More tokens (3-5) help with:
- FloodWait avoidance
- Faster uploads
- Load distribution

### 7. Verify in @BotFather

For each bot, check:
- ✅ Bot exists in `/mybots`
- ✅ Bot is not deleted
- ✅ Token matches exactly (no typos)

## Quick Test

After updating tokens, test with:

```bash
python main_bot.py
```

Look for:
```
✅ Bot 0 initialized: @your_bot_username
✅ Bot 1 initialized: @another_bot_username
```

Instead of:
```
❌ Failed to initialize bot 0: [400 ACCESS_TOKEN_INVALID]
```

## Need Help?

1. Share screenshot of @BotFather showing your bots
2. Verify you copied the **complete token** including the colon `:`
3. Make sure there are no spaces or special characters
4. Try with just ONE token first to isolate the issue
