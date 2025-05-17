import os
from confluent_kafka import Consumer, Producer
from bs4 import BeautifulSoup
import avro.schema
from avro.datafile import DataFileReader
from avro.io import DatumReader, DatumWriter, BinaryDecoder, BinaryEncoder
import io
from urllib.parse import urlparse, urlunparse
import tldextract
from app.models.schemas import CRAWLED_PAGE_AVRO_SCHEMA, ANCHOR_URL_AVRO_SCHEMA

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_SOURCE_TOPIC = os.getenv("KAFKA_SOURCE_TOPIC", "crawled_pages")
KAFKA_ANCHOR_TOPIC = os.getenv("KAFKA_ANCHOR_TOPIC", "anchor_text_urls")

class AvroKafkaConsumer:
    """
    Kafka consumer for Avro-encoded messages.
    Consumes messages from a Kafka topic and yields Avro records.
    """
    def __init__(self, bootstrap_servers, topic, avro_schema_str, group_id):
        self.topic = topic
        self.schema = avro.schema.parse(avro_schema_str)
        self.consumer = Consumer({
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': 'earliest'
        })
        self.consumer.subscribe([topic])

    def __iter__(self):
        return self

    def __next__(self):
        msg = self.consumer.poll(1.0)
        if msg is None:
            raise StopIteration
        if msg.error():
            print(f"[ERROR] Kafka error: {msg.error()}")
            raise StopIteration
        # Deserialize Avro
        buf = io.BytesIO(msg.value())
        reader = DataFileReader(buf, DatumReader())
        for record in reader:
            return record
        raise StopIteration

    def close(self):
        self.consumer.close()

class AvroKafkaProducer:
    """
    Kafka producer for Avro-encoded messages.
    Produces Avro records to a Kafka topic, using a specified key.
    """
    def __init__(self, bootstrap_servers, topic, avro_schema_str):
        self.topic = topic
        self.schema = avro.schema.parse(avro_schema_str)
        self.producer = Producer({'bootstrap.servers': bootstrap_servers})

    def send(self, record, key):
        buf = io.BytesIO()
        writer = avro.datafile.DataFileWriter(buf, DatumWriter(), self.schema)
        writer.append(record)
        writer.flush()
        writer.close()
        avro_bytes = buf.getvalue()
        self.producer.produce(self.topic, value=avro_bytes, key=key.encode('utf-8'))
        self.producer.flush()

    def close(self):
        self.producer.flush()

class AnchorTextExtractor:
    """
    Extracts anchor href URLs from HTML content, normalizes them, and produces them to Kafka.
    """
    def __init__(self, consumer, producer):
        self.consumer = consumer
        self.producer = producer

    @staticmethod
    def normalize_url(url):
        """
        Normalize a URL by removing fragments and query, and standardizing the scheme and netloc.
        """
        parsed = urlparse(url)
        normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip('/'), '', '', ''))
        return normalized

    def extract_and_produce(self):
        """
        Main loop: consumes Avro records, extracts anchor hrefs, normalizes them, and produces to Kafka.
        """
        print(f"[INFO] Consuming from '{self.consumer.topic}', producing to '{self.producer.topic}'...")
        try:
            for record in self.consumer:
                html = record.get('text')
                source_url = record.get('normalized_url')
                if not html or not source_url:
                    continue
                soup = BeautifulSoup(html, 'html.parser')
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if not href:
                        continue
                    normalized_href = self.normalize_url(href)
                    anchor_record = {
                        'normalized_url': normalized_href,
                        'source_url': source_url,
                        'timestamp': record.get('timestamp', '')
                    }
                    self.producer.send(anchor_record, key=normalized_href)
                    print(f"[INFO] Produced anchor URL: {normalized_href}")
        except KeyboardInterrupt:
            print("[INFO] Interrupted by user. Shutting down...")
        finally:
            self.consumer.close()
            self.producer.close()
            print("[INFO] Consumer and producer shutdown complete.")

if __name__ == "__main__":
    """
    Entrypoint for the AnchorTextExtractor consumer.
    Consumes Avro-encoded crawled pages, extracts anchor hrefs, normalizes them, and produces them to a new Kafka topic.
    """
    consumer = AvroKafkaConsumer(
        KAFKA_BOOTSTRAP_SERVERS,
        KAFKA_SOURCE_TOPIC,
        CRAWLED_PAGE_AVRO_SCHEMA,
        group_id="anchortext-extractor-group"
    )
    producer = AvroKafkaProducer(
        KAFKA_BOOTSTRAP_SERVERS,
        KAFKA_ANCHOR_TOPIC,
        ANCHOR_URL_AVRO_SCHEMA
    )
    extractor = AnchorTextExtractor(consumer, producer)
    extractor.extract_and_produce() 