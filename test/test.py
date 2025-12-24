import redis

r = redis.Redis(
    host='redis-16569.c212.ap-south-1-1.ec2.redislabs.com',
    port=16569,
    password='cLq4P1GbvewTeWeHMfv2lvXEN7ewmVBG',
    decode_responses=True
)

print(r.ping())  # Should print: True
