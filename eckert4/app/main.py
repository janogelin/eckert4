from fastapi import FastAPI, BackgroundTasks, HTTPException
from app.models.schemas import URLListRequest
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
from aiokafka import AIOKafkaProducer
import asyncio
from pydantic import HttpUrl
from fastapi import Body
import logging
import traceback

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
    async def _send():
        producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)
        await producer.start()
        try:
            await producer.send_and_wait(topic, json.dumps(data).encode("utf-8"))
        finally:
            await producer.stop()
    asyncio.run(_send())

app = FastAPI()

@app.post("/crawl")
def crawl_urls(request: URLListRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_urls, request.urls)
    return {"status": "Crawling started", "url_count": len(request.urls)}

@app.post("/crawl_one")
def crawl_one(url: HttpUrl = Body(..., embed=True)):
    etcd_host = os.environ.get('ETCD_HOST', ETCD_HOST)
    etcd_port = int(os.environ.get('ETCD_PORT', ETCD_PORT))
    print(f"[DEBUG] Connecting to etcd at {etcd_host}:{etcd_port}")
    try:
        etcd = etcd3.client(host=etcd_host, port=etcd_port)
        # Test connection
        etcd.status()
    except Exception as e:
        print(f"[ERROR] Failed to connect to etcd at {etcd_host}:{etcd_port}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to connect to etcd at {etcd_host}:{etcd_port}: {e}")
    memcached = memcache_base.Client((settings.MEMCACHED_HOST, settings.MEMCACHED_PORT))
    crawler = PageCrawler()
    normalized_url = normalize_url(str(url))
    last_seen = memcached.get(normalized_url)
    if last_seen:
        raise HTTPException(status_code=409, detail=f"URL {normalized_url} already crawled. Last seen at {last_seen.decode()}")
    domain = get_domain(normalized_url)
    key, lease = None, None
    try:
        # Acquire thread slot for politeness
        while True:
            key, lease = acquire_thread_slot(etcd, domain)
            if key:
                break
            time.sleep(2)
        result = crawler.crawl(normalized_url)
        memcached.set(normalized_url, datetime.utcnow().isoformat())
        table = pa.table({
            "url": [normalized_url],
            "title": [result["title"]],
            "text": [result["text"]],
            "timestamp": [datetime.utcnow().isoformat()]
        })
        parquet_path = os.path.join(OUTPUT_DIR, f"{domain.replace('.', '_')}.parquet")
        pq.write_table(table, parquet_path)
        kafka_data = {
            "original_url": str(url),
            "url": normalized_url,
            "title": result["title"],
            "text": result["text"],
            "timestamp": datetime.utcnow().isoformat(),
            "parquet_path": parquet_path
        }
        send_to_kafka_sync(kafka_data, settings.KAFKA_BOOTSTRAP_SERVERS, settings.KAFKA_TOPIC)
        return {"status": "Crawling complete", "result": kafka_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to crawl {normalized_url}: {e}")
    finally:
        release_thread_slot(etcd, key, lease)

def process_urls(urls):
    etcd_host = os.environ.get('ETCD_HOST', ETCD_HOST)
    etcd_port = int(os.environ.get('ETCD_PORT', ETCD_PORT))
    print(f"[DEBUG] Connecting to etcd at {etcd_host}:{etcd_port}")
    try:
        etcd = etcd3.client(host=etcd_host, port=etcd_port)
        # Test connection
        etcd.status()
    except Exception as e:
        print(f"[ERROR] Failed to connect to etcd at {etcd_host}:{etcd_port}: {e}")
        traceback.print_exc()
        raise
    memcached = memcache_base.Client((settings.MEMCACHED_HOST, settings.MEMCACHED_PORT))
    crawler = PageCrawler()
    for url in urls:
        normalized_url = normalize_url(str(url))
        last_seen = memcached.get(normalized_url)
        if last_seen:
            print(f"URL {normalized_url} already crawled. Last seen at {last_seen.decode()}")
            continue
        domain = get_domain(normalized_url)
        key, lease = None, None
        try:
            # Acquire thread slot for politeness
            while True:
                key, lease = acquire_thread_slot(etcd, domain)
                if key:
                    break
                print(f"Thread limit reached for {domain}, waiting...")
                time.sleep(2)
            result = crawler.crawl(normalized_url)
            print(f"Crawled {normalized_url}: {result['title']}")
            # Store normalized URL and timestamp in Memcached
            memcached.set(normalized_url, datetime.utcnow().isoformat())
            # Save result as Parquet file
            table = pa.table({
                "url": [normalized_url],
                "title": [result["title"]],
                "text": [result["text"]],
                "timestamp": [datetime.utcnow().isoformat()]
            })
            parquet_path = os.path.join(OUTPUT_DIR, f"{domain.replace('.', '_')}.parquet")
            pq.write_table(table, parquet_path)
            print(f"Saved Parquet file: {parquet_path}")
            print(f"Parquet output: {table.to_pandas().to_dict()}")
            # Send result to Kafka
            kafka_data = {
                "original_url": url,
                "url": normalized_url,
                "title": result["title"],
                "text": result["text"],
                "timestamp": datetime.utcnow().isoformat(),
                "parquet_path": parquet_path
            }
            send_to_kafka_sync(kafka_data, settings.KAFKA_BOOTSTRAP_SERVERS, settings.KAFKA_TOPIC)
            print(f"Sent result to Kafka topic {settings.KAFKA_TOPIC}")
        except Exception as e:
            print(f"Failed to crawl {normalized_url}: {e}")
        finally:
            release_thread_slot(etcd, key, lease)
