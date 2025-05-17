import os
import io
from confluent_kafka import Producer
import avro.schema
from avro.datafile import DataFileWriter
from avro.io import DatumWriter
from app.models.schemas import ANCHOR_URL_AVRO_SCHEMA

# --- Docker Network Notes ---
# This script is intended to run in the 'kafka-net' Docker network.
# Kafka host: kafka:9092

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_ANCHOR_TOPIC = os.getenv("KAFKA_ANCHOR_TOPIC", "anchor_text_urls")

class AvroAnchorUrlProducer:
    """
    Kafka producer for Avro-encoded anchor URL records.
    Sends a single test message for workflow validation.
    """
    def __init__(self, bootstrap_servers, topic, avro_schema_str):
        print(f"[DEBUG] Initializing AvroAnchorUrlProducer with Kafka at {bootstrap_servers}, topic '{topic}'")
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.schema = avro.schema.parse(avro_schema_str)
        self.producer = Producer({'bootstrap.servers': self.bootstrap_servers})

    def serialize_avro(self, record):
        buf = io.BytesIO()
        writer = DataFileWriter(buf, DatumWriter(), self.schema)
        writer.append(record)
        writer.flush()
        avro_bytes = buf.getvalue()
        writer.close()
        return avro_bytes

    def produce(self, record):
        avro_bytes = self.serialize_avro(record)
        print(f"[DEBUG] Producing Avro-encoded message to topic '{self.topic}'...")
        self.producer.produce(self.topic, value=avro_bytes, on_delivery=self.delivery_report)
        self.producer.flush()

    @staticmethod
    def delivery_report(err, msg):
        if err is not None:
            print(f"[ERROR] Message delivery failed: {err}")
        else:
            print(f"[INFO] Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

if __name__ == "__main__":
    print("[DEBUG] Starting test anchor URL Avro producer...")
    producer = AvroAnchorUrlProducer(
        KAFKA_BOOTSTRAP_SERVERS,
        KAFKA_ANCHOR_TOPIC,
        ANCHOR_URL_AVRO_SCHEMA
    )
    test_record = {
        'normalized_url': 'https://www.svt.se',
        'source_url': 'https://source.svt.se',
        'timestamp': '2024-01-01T00:00:00Z'
    }
    producer.produce(test_record)
    print("[INFO] Test anchor URL message produced.") 