# Consumers Directory Documentation

This directory contains Kafka consumer utilities for processing and debugging web crawl and anchor extraction data. All consumers are designed to work with Avro-encoded messages and integrate with the broader crawling pipeline.

---

## anchortext_extractor_consumer.py

**Purpose:**
- Consumes Avro-encoded crawled web page records from a Kafka topic.
- Extracts anchor (`<a href=...>`) URLs from the HTML content of each page.
- Normalizes each anchor URL and produces it as a new Avro record to a separate Kafka topic, using the normalized anchor URL as the Kafka key.

**Key Features:**
- Modular, class-based design (`AvroKafkaConsumer`, `AvroKafkaProducer`, `AnchorTextExtractor`).
- Uses a custom Avro schema for anchor URLs (`ANCHOR_URL_AVRO_SCHEMA`).
- Extensively documented and suitable for production or further extension.

**Environment Variables:**
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka broker address (default: `localhost:9092`).
- `KAFKA_SOURCE_TOPIC`: Topic to consume crawled pages from (default: `crawled_pages`).
- `KAFKA_ANCHOR_TOPIC`: Topic to produce anchor URLs to (default: `anchor_text_urls`).

**Usage:**
```bash
python anchortext_extractor_consumer.py
```

---

## debug_anchor_url_consumer.py

**Purpose:**
- Simple debugging utility to consume and print Avro-encoded anchor URL records from the anchor URL Kafka topic.
- Useful for verifying the output of the anchor extraction pipeline inside or outside a Docker container.

**Key Features:**
- Minimal, single-file script.
- Prints each decoded Avro record to the console.
- Handles Avro decoding errors gracefully.

**Environment Variables:**
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka broker address (default: `localhost:9092`).
- `KAFKA_ANCHOR_TOPIC`: Topic to consume anchor URLs from (default: `anchor_text_urls`).
- `KAFKA_DEBUG_GROUP_ID`: Consumer group ID (default: `debug-anchor-url-consumer`).

**Usage:**
```bash
python debug_anchor_url_consumer.py
```

**Docker Notes:**
- This script is suitable for running in a minimal Python Docker container with the required dependencies installed.

---

## kafka_parquet_consumer.py

**Purpose:**
- Consumes JSON-encoded crawled page records from a Kafka topic and writes them to Parquet files in batches.
- Used for archiving or further analysis of crawled data.

**Key Features:**
- Batches records and writes to Parquet using `pyarrow`.
- Prints info about each batch written.

**Environment Variables:**
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka broker address (default: `localhost:9092`).
- `KAFKA_TOPIC`: Topic to consume from (default: `crawled_pages`).
- `PARQUET_DIR`: Output directory for Parquet files (default: `parquet_output`).
- `PARQUET_BATCH_SIZE`: Number of records per Parquet file (default: `100`).

**Usage:**
```bash
python kafka_parquet_consumer.py
```

---

## Docker-based Test Workflow

**scripts/test_anchor_url_workflow.sh**

**Purpose:**
- Runs the anchor URL Avro test workflow in Docker containers on the `kafka-net` network.
- Each container is launched with `--rm` and `--name` for easy cleanup.
- Runs the Avro roundtrip test and then the debug consumer to print anchor URL records from Kafka.

**Prerequisites:**
- The following containers must be running in the `kafka-net` Docker network **with these names**:
  - `etcd-test`
  - `memcached-test`
  - `kafka`
  - `zookeeper`
- The Python image used must have all required dependencies (as listed in `requirements.txt`).

**Example: Launch required containers**
```bash
# Create the network if it doesn't exist
if ! docker network ls | grep -q kafka-net; then
  docker network create kafka-net
fi

# Start Zookeeper
# (You may want to use a specific version or image as needed)
docker run -d --rm --name zookeeper --network kafka-net -e ZOOKEEPER_CLIENT_PORT=2181 confluentinc/cp-zookeeper:7.4.0

# Start Kafka
# (Adjust KAFKA_ADVERTISED_LISTENERS as needed for your environment)
docker run -d --rm --name kafka --network kafka-net -e KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092 -e KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 \
  confluentinc/cp-kafka:7.4.0

# Start etcd
docker run -d --rm --name etcd-test --network kafka-net quay.io/coreos/etcd:latest \
  /usr/local/bin/etcd --advertise-client-urls http://0.0.0.0:2379 --listen-client-urls http://0.0.0.0:2379

# Start Memcached
docker run -d --rm --name memcached-test --network kafka-net memcached:alpine
```

**Usage:**
```bash
bash scripts/test_anchor_url_workflow.sh
```

**What it does:**
1. Checks that all required containers are running.
2. Cleans up any old containers with the same names.
3. Runs the Avro roundtrip test in a container (pytest).
4. Runs the debug anchor URL consumer in a container, printing Avro records from Kafka.
5. Cleans up all containers after completion.

---

## Tests

### tests/test_anchor_url_avro.py
**Purpose:**
- Tests Avro serialization and deserialization for anchor URL records using the custom schema.
- Ensures round-trip Avro encoding/decoding works as expected for anchor URLs.

**Usage:**
```bash
pytest tests/test_anchor_url_avro.py
```

### tests/test_anchortext_extractor_consumer.py
**Purpose:**
- Tests the anchor extraction logic from HTML using the AnchorTextExtractor class.
- Ensures anchor hrefs are correctly extracted and normalized.

**Usage:**
```bash
pytest tests/test_anchortext_extractor_consumer.py
```

---

## General Notes
- All Avro schemas are defined in `app/models/schemas.py`.
- For Avro consumers, ensure the Python `avro` library is installed.
- For Docker usage, copy only the necessary scripts and dependencies into your container for minimal images.
- Update environment variables as needed for your deployment. 