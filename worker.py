import os
import redis
import cdc_pb2

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(REDIS_URL)
last_id = "0"

print("Worker started, waiting for events...")

while True:
    streams = r.xread({"cdc:events": last_id}, block=5000, count=1)
    
    if not streams:
        continue
    
    for stream_name, messages in streams:
        for msg_id, data in messages:
            # Deserialize Protobuf
            record = cdc_pb2.ChangeRecord()
            record.ParseFromString(data[b"payload"])
            
            print(f"[Worker] {record.operation} on {record.table}")
            print(f"         LSN: {record.lsn}")
            print(f"         Data: {record.raw_data[:50]}...")
            
            last_id = msg_id