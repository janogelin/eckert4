import json
from confluent_kafka import Consumer

KAFKA_BOOTSTRAP_SERVERS = 'kafka:9092'
KAFKA_TOPIC = 'crawled_pages'

conf = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': 'simple-consumer-group',
    'auto.offset.reset': 'earliest'
}

consumer = Consumer(conf)
consumer.subscribe([KAFKA_TOPIC])

print(f"[INFO] Consuming from Kafka topic '{KAFKA_TOPIC}' on {KAFKA_BOOTSTRAP_SERVERS}...")

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
            print(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[ERROR] Failed to decode message: {e}")
            print(msg.value())
except KeyboardInterrupt:
    print("[INFO] Interrupted by user. Shutting down...")
finally:
    consumer.close()
    print("[INFO] Consumer shutdown complete.") 