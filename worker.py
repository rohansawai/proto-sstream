import redis

r = redis.from_url("redis://localhost:6379/0")
last_id = "0"

print("Worker started, waiting for events...")

while True:
    # Block until new events arrive
    streams = r.xread({"cdc:events": last_id}, block=5000, count=1)
    
    if not streams:
        continue
    
    for stream_name, messages in streams:
        for msg_id, data in messages:
            event = data[b"data"].decode()
            print(f"[Worker] Processing: {event}")
            
            # Here you would do something with the event:
            # - Send to another service
            # - Write to another database
            # - Trigger a notification
            # - etc.
            
            last_id = msg_id
