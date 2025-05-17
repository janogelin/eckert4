from fastapi import FastAPI, BackgroundTasks, HTTPException
from app.models.schemas import URLListRequest, CRAWLED_PAGE_AVRO_SCHEMA
from app.config import settings
from app.crawler.page_crawler import PageCrawler
import etcd3
import uuid
import time
from urllib.parse import urlparse, urlunparse
import tldextract
from pymemcache.client import base as memcache_base
from datetime import datetime
import pyarrow as pa
import pyarrow.parquet as pq
import os
import json
from confluent_kafka import Producer
from fastapi import Body
from pydantic import HttpUrl
import logging
import traceback
import avro.schema
from avro.datafile import DataFileWriter
from avro.io import DatumWriter

THREAD_LIMIT = 5
ETCD_HOST = "localhost"
ETCD_PORT = 2379
OUTPUT_DIR = "test_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def normalize_url(url):
    # Use tldextract to get the registered domain and scheme
    parts = tldextract.extract(url)
    parsed = urlparse(url)
    # Remove fragments and query for normalization
    normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip('/'), '', '', ''))
    return normalized

def get_domain(url):
    return urlparse(url).netloc.replace('www.', '')

def acquire_thread_slot(etcd, domain):
    prefix = f"/crawler/semaphores/{domain}/"
    keys = list(etcd.get_prefix(prefix, keys_only=True))
    if len(keys) < THREAD_LIMIT:
        lease = etcd.lease(300)  # 5 minutes
        thread_id = str(uuid.uuid4())
        key = f"{prefix}thread-{thread_id}"
        etcd.put(key, "", lease=lease)
        return key, lease
    return None, None

def release_thread_slot(etcd, key, lease):
    if key:
        etcd.delete(key)
        if lease:
            lease.revoke()

def send_to_kafka_sync(data, bootstrap_servers, topic):
    producer_conf = {'bootstrap.servers': bootstrap_servers}
    producer = Producer(producer_conf)
    try:
        producer.produce(topic, json.dumps(data).encode("utf-8"))
        producer.flush()
    except Exception as e:
        print(f"[ERROR] Failed to send message to Kafka: {e}")

class AvroKafkaProducer:
    def __init__(self, bootstrap_servers, topic, avro_schema_str):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.schema = avro.schema.parse(avro_schema_str)
        self.producer = Producer({'bootstrap.servers': bootstrap_servers})

    def send(self, record):
        # Serialize record to Avro binary
        import io
        buf = io.BytesIO()
        writer = DataFileWriter(buf, DatumWriter(), self.schema)
        writer.append(record)
        writer.flush()
        writer.close()
        avro_bytes = buf.getvalue()
        # Use normalized_url as key
        key = record['normalized_url'].encode('utf-8')
        self.producer.produce(self.topic, value=avro_bytes, key=key)
        self.producer.flush()

class CrawlerService:
    def __init__(self, settings):
        self.settings = settings
        self.memcached = memcache_base.Client((settings.MEMCACHED_HOST, settings.MEMCACHED_PORT))
        self.crawler = PageCrawler()
        self.avro_producer = AvroKafkaProducer(
            settings.KAFKA_BOOTSTRAP_SERVERS,
            settings.KAFKA_TOPIC,
            CRAWLED_PAGE_AVRO_SCHEMA
        )

    def crawl_one(self, url, etcd):
        normalized_url = normalize_url(str(url))
        last_seen = self.memcached.get(normalized_url)
        if last_seen:
            raise HTTPException(status_code=409, detail=f"URL {normalized_url} already crawled. Last seen at {last_seen.decode()}")
        domain = get_domain(normalized_url)
        key, lease = None, None
        try:
            while True:
                key, lease = acquire_thread_slot(etcd, domain)
                if key:
                    break
                time.sleep(2)
            result = self.crawler.crawl(normalized_url)
            self.memcached.set(normalized_url, datetime.utcnow().isoformat())
            record = {
                "normalized_url": normalized_url,
                "title": result["title"],
                "text": result["text"],
                "timestamp": datetime.utcnow().isoformat()
            }
            # Send to Kafka as Avro
            self.avro_producer.send(record)
            return {"status": "Crawling complete", "result": record}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to crawl {normalized_url}: {e}")
        finally:
            release_thread_slot(etcd, key, lease)

    def crawl_many(self, urls, etcd):
        for url in urls:
            try:
                self.crawl_one(url, etcd)
            except Exception as e:
                print(f"Failed to crawl {url}: {e}")

app = FastAPI()
crawler_service = CrawlerService(settings)

@app.post("/crawl")
def crawl_urls(request: URLListRequest, background_tasks: BackgroundTasks):
    etcd_host = os.environ.get('ETCD_HOST', ETCD_HOST)
    etcd_port = int(os.environ.get('ETCD_PORT', ETCD_PORT))
    etcd = etcd3.client(host=etcd_host, port=etcd_port)
    background_tasks.add_task(crawler_service.crawl_many, request.urls, etcd)
    return {"status": "Crawling started", "url_count": len(request.urls)}

@app.post("/crawl_one")
def crawl_one(url: HttpUrl = Body(..., embed=True)):
    etcd_host = os.environ.get('ETCD_HOST', ETCD_HOST)
    etcd_port = int(os.environ.get('ETCD_PORT', ETCD_PORT))
    etcd = etcd3.client(host=etcd_host, port=etcd_port)
    return crawler_service.crawl_one(url, etcd)
