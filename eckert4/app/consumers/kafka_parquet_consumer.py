import os
import json
from confluent_kafka import Consumer
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "crawled_pages")
PARQUET_DIR = os.getenv("PARQUET_DIR", "parquet_output")
BATCH_SIZE = int(os.getenv("PARQUET_BATCH_SIZE", 100))

os.makedirs(PARQUET_DIR, exist_ok=True)

conf = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': 'parquet-consumer-group',
    'auto.offset.reset': 'earliest'
}

consumer = Consumer(conf)
consumer.subscribe([KAFKA_TOPIC])

batch = []

print(f"[INFO] Consuming from Kafka topic '{KAFKA_TOPIC}' and writing to '{PARQUET_DIR}'...")

def flush_batch(batch, parquet_dir):
    if not batch:
        return
    table = pa.Table.from_pylist(batch)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    parquet_path = os.path.join(parquet_dir, f"crawled_pages_batch_{ts}.parquet")
    pq.write_table(table, parquet_path)
    print(f"[INFO] Wrote {len(batch)} records to {parquet_path}")
    batch.clear()

try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print(f"[ERROR] Kafka error: {msg.error()}")
            continue
        try:
            data = json.loads(msg.value().decode("utf-8"))
            batch.append(data)
            if len(batch) >= BATCH_SIZE:
                flush_batch(batch, PARQUET_DIR)
        except Exception as e:
            print(f"[ERROR] Failed to process message: {e}")
except KeyboardInterrupt:
    print("[INFO] Interrupted by user. Flushing remaining records...")
finally:
    flush_batch(batch, PARQUET_DIR)
    consumer.close()
    print("[INFO] Consumer shutdown complete.") 