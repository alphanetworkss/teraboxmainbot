import redis
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Redis Cloud connection (NO SSL - free tier uses plain TCP)
r = redis.Redis(
    host='redis-16569.c212.ap-south-1-1.ec2.cloud.redislabs.com',
    port=16569,
    password='cLq4P1GbvewTeWeHMfv2lvXEN7ewmVBG',
    decode_responses=True,
    socket_timeout=10,
    socket_connect_timeout=10
)

try:
    print("Testing Redis connection...")
    result = r.ping()
    print(f"✅ Connection successful! PING returned: {result}")
    
    # Test setting and getting a value
    r.set('test_key', 'Hello from TeraBox Bot!')
    value = r.get('test_key')
    print(f"✅ Set/Get test successful! Value: {value}")
    
    # Clean up
    r.delete('test_key')
    print("✅ All tests passed!")
    print("\n🎉 Your Redis Cloud is working perfectly!")
    print("\nYou can now update your .env file with:")
    print("REDIS_HOST=redis-16569.c212.ap-south-1-1.ec2.cloud.redislabs.com")
    print("REDIS_PORT=16569")
    print("REDIS_PASSWORD=cLq4P1GbvewTeWeHMfv2lvXEN7ewmVBG")
    
except redis.exceptions.ConnectionError as e:
    print(f"❌ Connection Error: {e}")
    print("\nTroubleshooting:")
    print("1. Check your internet connection")
    print("2. Verify Redis Cloud endpoint is correct")
    print("3. Check if Redis password is correct")
except Exception as e:
    print(f"❌ Error: {e}")
