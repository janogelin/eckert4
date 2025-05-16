import os
import json
from confluent_kafka import Consumer, Producer
from bs4 import BeautifulSoup

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_SOURCE_TOPIC = os.getenv("KAFKA_SOURCE_TOPIC", "crawled_pages")
KAFKA_ANCHOR_TOPIC = os.getenv("KAFKA_ANCHOR_TOPIC", "anchor_text")

consumer_conf = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': 'anchortext-extractor-group',
    'auto.offset.reset': 'earliest'
}
producer_conf = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS
}

consumer = Consumer(consumer_conf)
producer = Producer(producer_conf)
consumer.subscribe([KAFKA_SOURCE_TOPIC])

print(f"[INFO] Consuming from '{KAFKA_SOURCE_TOPIC}', producing to '{KAFKA_ANCHOR_TOPIC}'...")

def extract_anchors(html, source_url):
    soup = BeautifulSoup(html, 'html.parser')
    anchors = []
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        href = a['href']
        if text and href:
            anchors.append({
                'source_url': source_url,
                'anchor_text': text,
                'href': href
            })
    return anchors

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
            # Try to get HTML from 'text' or 'html' field
            html = data.get('html') or data.get('text')
            source_url = data.get('url') or data.get('original_url')
            if not html or not source_url:
                continue
            anchors = extract_anchors(html, source_url)
            for anchor in anchors:
                producer.produce(KAFKA_ANCHOR_TOPIC, json.dumps(anchor).encode('utf-8'))
            producer.flush()
            print(f"[INFO] Extracted and sent {len(anchors)} anchors from {source_url}")
        except Exception as e:
            print(f"[ERROR] Failed to process message: {e}")
except KeyboardInterrupt:
    print("[INFO] Interrupted by user. Shutting down...")
finally:
    consumer.close()
    print("[INFO] Consumer shutdown complete.") 