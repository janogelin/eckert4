import os
import io
from confluent_kafka import Consumer
import avro.schema
from avro.datafile import DataFileReader
from avro.io import DatumReader
from app.models.schemas import ANCHOR_URL_AVRO_SCHEMA

# --- Docker Network Notes ---
# This script is intended to run in the 'kafka-net' Docker network.
# Kafka host: kafka:9092
# etcd host: etcd-test:2379 (if needed)
# memcached host: memcached-test:11211 (if needed)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_ANCHOR_TOPIC = os.getenv("KAFKA_ANCHOR_TOPIC", "anchor_text_urls")
GROUP_ID = os.getenv("KAFKA_DEBUG_GROUP_ID", "debug-anchor-url-consumer")

class AvroAnchorUrlConsumer:
    """
    Kafka consumer for Avro-encoded anchor URL records.
    Designed for debugging and log inspection in Docker.
    """
    def __init__(self, bootstrap_servers, topic, group_id, avro_schema_str):
        print(f"[DEBUG] Initializing AvroAnchorUrlConsumer with Kafka at {bootstrap_servers}, topic '{topic}', group '{group_id}'")
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.schema = avro.schema.parse(avro_schema_str)
        self.conf = {
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': self.group_id,
            'auto.offset.reset': 'earliest'
        }
        self.consumer = Consumer(self.conf)
        print(f"[DEBUG] Consumer config: {self.conf}")

    def start(self):
        print(f"[DEBUG] Subscribing to topic '{self.topic}'...")
        self.consumer.subscribe([self.topic])
        print(f"[DEBUG] Ready to consume messages from Kafka at {self.bootstrap_servers} on topic '{self.topic}'")
        self.consume()

    def consume(self):
        print("[DEBUG] Ready to consume messages from Kafka at {} on topic '{}'".format(self.bootstrap_servers, self.topic))
        print("\n===== BEGIN ANCHOR URL MESSAGES =====\n")
        try:
            while True:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    print("[DEBUG] No message received in this poll interval.")
                    continue
                if msg.error():
                    print(f"[ERROR] Kafka error: {msg.error()}")
                    continue
                # Deserialize Avro message
                record = self.deserialize_avro(msg.value())
                print(record)
        except KeyboardInterrupt:
            print("[DEBUG] Stopping consumer...")
        finally:
            print("\n===== END ANCHOR URL MESSAGES =====\n")
            self.consumer.close()

    def deserialize_avro(self, value):
        buf = io.BytesIO(value)
        reader = DataFileReader(buf, DatumReader())
        for record in reader:
            return record

if __name__ == "__main__":
    print("[DEBUG] Starting debug anchor URL consumer...")
    consumer = AvroAnchorUrlConsumer(
        KAFKA_BOOTSTRAP_SERVERS,
        KAFKA_ANCHOR_TOPIC,
        GROUP_ID,
        ANCHOR_URL_AVRO_SCHEMA
    )
    consumer.start() 