import os
import json
from confluent_kafka import Consumer
from bs4 import BeautifulSoup

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_SOURCE_TOPIC = os.getenv("KAFKA_SOURCE_TOPIC", "crawled_pages")
LOG_FILE = os.getenv("ANCHOR_LOG_FILE", "/app/anchortext_test.log")

consumer_conf = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': 'anchortext-extractor-test-group',
    'auto.offset.reset': 'earliest'
}

consumer = Consumer(consumer_conf)
consumer.subscribe([KAFKA_SOURCE_TOPIC])

print(f"[INFO] Test consumer started. Reading from '{KAFKA_SOURCE_TOPIC}' on {KAFKA_BOOTSTRAP_SERVERS}...")

HEADER_PRINTED = False

def extract_anchors(html):
    soup = BeautifulSoup(html, 'html.parser')
    return [a['href'] for a in soup.find_all('a', href=True)]

try:
    with open(LOG_FILE, "w") as logf:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"[ERROR] Kafka error: {msg.error()}")
                continue
            try:
                data = json.loads(msg.value().decode("utf-8"))
                html = data.get('html') or data.get('text')
                if not html:
                    print("[INFO] No HTML found in message.")
                    continue
                anchor_urls = extract_anchors(html)
                print(f"[INFO] Extracted {len(anchor_urls)} anchor URLs.")
                if anchor_urls and not HEADER_PRINTED:
                    logf.write("==== ANCHOR TEXT URLS EXTRACTED SUCCESSFULLY ====" + "\n")
                    HEADER_PRINTED = True
                for url in anchor_urls:
                    logf.write(url + "\n")
                    print(f"[ANCHOR] {url}")
                logf.flush()
            except Exception as e:
                print(f"[ERROR] Failed to process message: {e}")
except KeyboardInterrupt:
    print("[INFO] Interrupted by user. Shutting down...")
finally:
    consumer.close()
    print("[INFO] Test consumer shutdown complete.") 