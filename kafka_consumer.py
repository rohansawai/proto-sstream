import os
from kafka import KafkaConsumer
import cdc_pb2

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC = "cdc.events"

consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=[KAFKA_BROKER],
    group_id="cdc-consumer-group",
    auto_offset_reset="earliest",
    value_deserializer=None
)

print(f"Kafka consumer started, listening to {KAFKA_TOPIC}...")

for message in consumer:
    record = cdc_pb2.ChangeRecord()
    record.ParseFromString(message.value)
    
    print(f"[Kafka] {record.operation} on {record.table}")
    print(f"        LSN: {record.lsn}")
    print(f"        Data: {record.raw_data[:50]}...")