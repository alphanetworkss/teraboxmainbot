import asyncio
from aiogram import Bot

# Test if main bot can access the log channel
async def test_channel_access():
    # Replace with your actual values
    MAIN_BOT_TOKEN = "7622285251:AAEV_WICBEggKgKclypxinORCbJRBRR3MrI"
    LOG_CHANNEL_ID = -1002813604442
    
    bot = Bot(token=MAIN_BOT_TOKEN)
    
    try:
        # Try to get chat info
        chat = await bot.get_chat(LOG_CHANNEL_ID)
        print(f"✅ Channel found: {chat.title}")
        print(f"   Type: {chat.type}")
        print(f"   ID: {chat.id}")
        
        # Try to get chat member count
        try:
            count = await bot.get_chat_member_count(LOG_CHANNEL_ID)
            print(f"✅ Member count: {count}")
        except Exception as e:
            print(f"⚠️  Could not get member count: {e}")
        
        # Try to send a test message
        try:
            msg = await bot.send_message(LOG_CHANNEL_ID, "🧪 Test message from main bot")
            print(f"✅ Can send messages! Message ID: {msg.message_id}")
            
            # Try to copy the message
            try:
                # Replace with a real user chat ID to test
                TEST_USER_CHAT_ID = 123456789  # Replace with your Telegram user ID
                await bot.copy_message(
                    chat_id=TEST_USER_CHAT_ID,
                    from_chat_id=LOG_CHANNEL_ID,
                    message_id=msg.message_id
                )
                print(f"✅ Can copy messages!")
            except Exception as e:
                print(f"❌ Cannot copy messages: {e}")
            
            # Delete test message
            await bot.delete_message(LOG_CHANNEL_ID, msg.message_id)
            
        except Exception as e:
            print(f"❌ Cannot send messages: {e}")
        
    except Exception as e:
        print(f"❌ Cannot access channel: {e}")
        print(f"\nPossible issues:")
        print(f"1. Bot is not admin of the channel")
        print(f"2. Channel ID is wrong")
        print(f"3. Bot token is wrong")
    
    finally:
        await bot.session.close()

# Run the test
asyncio.run(test_channel_access())
