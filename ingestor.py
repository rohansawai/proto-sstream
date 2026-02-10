import json
import time
import psycopg2
from psycopg2.extras import LogicalReplicationConnection
import redis

SLOT_NAME = "my_slot"

r = redis.from_url("redis://localhost:6379/0")

def main():
    conn = psycopg2.connect(
        host="localhost",
        port=5434,
        user="repluser",
        password="replpass",
        dbname="shadowdb",
        connection_factory=LogicalReplicationConnection
    )
    
    cur = conn.cursor()
    
    try:
        cur.create_replication_slot(SLOT_NAME, output_plugin="test_decoding")
        print(f"Created slot: {SLOT_NAME}")
    except psycopg2.ProgrammingError:
        print(f"Slot {SLOT_NAME} already exists")
    
    cur.start_replication(slot_name=SLOT_NAME, decode=True)
    
    def handle_message(msg):
        payload = msg.payload
        
        # Skip BEGIN/COMMIT lines, only process actual changes
        if payload.startswith("table"):
            r.xadd("cdc:events", {"data": payload})
            print(f"Pushed to Redis: {payload[:60]}...")
        
        msg.cursor.send_feedback(flush_lsn=msg.data_start)
    
    print("Listening for changes...")
    cur.consume_stream(handle_message)

if __name__ == "__main__":
    main()