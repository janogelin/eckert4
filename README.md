# Eckert4 Integration Test & Anchortext Extraction Workflow

## Prerequisites

Before running the integration test, you must have the following services running (all on the `kafka-net` Docker network):

- **etcd** (v3.5.9)
- **Memcached** (latest)
- **Zookeeper** (3.8)
- **Kafka** (single instance, 2.13-2.8.1)

## Start Required Services

### Create kafka-net if not existent
```
docker network create kafka-net
```

### Start etcd (as etcd-test on kafka-net)
```
docker run -d \
  --name etcd-test \
  --network kafka-net \
  -e ETCD_LOG_LEVEL=debug \
  quay.io/coreos/etcd:v3.5.9 \
  /usr/local/bin/etcd \
  --name s1 \
  --data-dir /etcd-data \
  --listen-client-urls http://0.0.0.0:2379 \
  --advertise-client-urls http://etcd-test:2379 \
  --listen-peer-urls http://0.0.0.0:2380 \
  --initial-advertise-peer-urls http://etcd-test:2380 \
  --initial-cluster s1=http://etcd-test:2380 \
  --initial-cluster-state new \
  --initial-cluster-token etcd-cluster-1
```

### Start Memcached (as memcached-test on kafka-net)
```
docker run -d \
  --name memcached-test \
  --network kafka-net \
  memcached:latest \
  memcached -vv
```

### Start Zookeeper
```
docker run -d --rm --name zookeeper --network kafka-net -p 2181:2181 zookeeper:3.8
```

### Start Kafka (single instance)
```
docker run -d --rm --name kafka --network kafka-net -p 9092:9092 \
  --env KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181 \
  --env KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092 \
  --env KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:9092 \
  --env KAFKA_BROKER_ID=1 \
  --env KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 \
  --env KAFKA_LOG_RETENTION_HOURS=1 \
  --env KAFKA_AUTO_CREATE_TOPICS_ENABLE=true \
  --link zookeeper wurstmeister/kafka:2.13-2.8.1
```

### (Optional) Check queue with kafdrop
```
docker run --rm -d --name kafdrop --network kafka-net \
  -e KAFKA_BROKERCONNECT=kafka:9092 \
  -p 9000:9000 obsidiandynamics/kafdrop
```

---

## Automated End-to-End Test: Anchortext Extraction

Once all services are running, you can run the full integration and anchortext extraction test:

```
./scripts/test_anchortext_flow.sh
```

This script will:
- Ensure a clean environment (removes old containers/logs)
- Wait for etcd and Memcached to be healthy
- Delete the `crawled_pages` topic from Kafka
- Launch the main app as a Docker container on `kafka-net`
- Crawl a new test URL (edit the script to change the URL)
- Build and run the anchortext test consumer as a Docker container
- Print extracted anchor URLs to `anchortext_test.log` and to stdout
- Clean up all test containers and images

### Interpreting Results
- If successful, you will see anchor URLs from the test page in `anchortext_test.log` and in the script output.
- If the log file is empty, check that the test URL is truly new and that all services are running on `kafka-net`.

---

## Reading the Output Parquet File

The crawl results are saved as a Parquet file (e.g., `bbc_com.parquet`).

### Using Python (pandas)

```python
import pandas as pd

df = pd.read_parquet('bbc_com.parquet')
print(df.head())
```

Make sure you have the required dependencies:
```
pip install pandas pyarrow
```

### Using parquet-tools (CLI)

If you want to inspect the file from the command line, you can use [parquet-tools](https://github.com/apache/parquet-mr/tree/master/parquet-tools):

```
parquet-tools head bbc_com.parquet
```

To install parquet-tools:
- On Ubuntu: `sudo apt install parquet-tools` (if available)
- Or download the jar from the [official repo](https://github.com/apache/parquet-mr/tree/master/parquet-tools) and run with Java. 