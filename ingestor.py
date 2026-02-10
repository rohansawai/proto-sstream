import os
import time
import psycopg2
from psycopg2.extras import LogicalReplicationConnection
import redis
from kafka import KafkaProducer
import cdc_pb2  # Generated from proto

# Configuration from environment variables (with defaults for local dev)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5434"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")

SLOT_NAME = "cdc_slot"
KAFKA_TOPIC = "cdc.events"

r = redis.from_url(REDIS_URL)

# Kafka producer
producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=None  # We send raw bytes (Protobuf)
)

def parse_change(payload):
    """Parse the test_decoding output into structured data."""
    # Example: "table public.events: INSERT: id[integer]:1 name[text]:'hello'"
    parts = payload.split(": ", 2)
    table = parts[0].replace("table ", "")  # "public.events"
    operation = parts[1]                     # "INSERT", "UPDATE", "DELETE"
    raw_data = parts[2] if len(parts) > 2 else ""
    return table, operation, raw_data

def main():
    print(f"Connecting to PostgreSQL at {POSTGRES_HOST}:{POSTGRES_PORT}...")
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
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
        
        if payload.startswith("table"):
            table, operation, raw_data = parse_change(payload)
            
            # Create Protobuf message
            record = cdc_pb2.ChangeRecord(
                lsn=str(msg.data_start),
                commit_time=int(time.time() * 1000),
                table=table,
                operation=operation,
                raw_data=raw_data
            )
            
            # Serialize to bytes
            serialized = record.SerializeToString()
            
            # Push to Redis (low latency)
            r.xadd("cdc:events", {
                "payload": serialized,
                "table": table
            })
            
            # Push to Kafka (durable archive)
            producer.send(KAFKA_TOPIC, value=serialized, key=table.encode())
            producer.flush()
            
            print(f"Pushed: {operation} on {table} → Redis + Kafka")
        
        msg.cursor.send_feedback(flush_lsn=msg.data_start)
    
    print("Listening for changes...")
    cur.consume_stream(handle_message)

if __name__ == "__main__":
    main()