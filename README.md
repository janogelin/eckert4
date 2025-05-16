# Eckert4 Integration Test Instructions

## Prerequisites

Before running the integration test, you must have the following services running (can be started with Docker):

- **etcd** (v3.5.9)
- **Memcached** (latest)
- **Zookeeper** (3.8)
- **Kafka** (single instance, 2.13-2.8.1)

## Start Required Services

### Start etcd
```
docker run -d \
  --name etcd-single \
  --network host \
  -e ETCD_LOG_LEVEL=debug \
  quay.io/coreos/etcd:v3.5.9 \
  /usr/local/bin/etcd \
  --name s1 \
  --data-dir /etcd-data \
  --listen-client-urls http://127.0.0.1:2379 \
  --advertise-client-urls http://127.0.0.1:2379 \
  --listen-peer-urls http://127.0.0.1:2380 \
  --initial-advertise-peer-urls http://127.0.0.1:2380 \
  --initial-cluster s1=http://127.0.0.1:2380 \
  --initial-cluster-state new \
  --initial-cluster-token etcd-cluster-1
```

### Start Memcached
```
docker run -d \
  --name memcached \
  -p 11211:11211 \
  memcached:latest \
  memcached -vv
```

### Start Zookeeper
```
docker run -d --name zookeeper -p 2181:2181 zookeeper:3.8
```

### Start Kafka (single instance)
```
docker run -d --name kafka -p 9092:9092 \
  --env KAFKA_ZOOKEEPER_CONNECT=host.docker.internal:2181 \
  --env KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
  --env KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:9092 \
  --env KAFKA_BROKER_ID=1 \
  --env KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 \
  --env KAFKA_LOG_RETENTION_HOURS=1 \
  --env KAFKA_AUTO_CREATE_TOPICS_ENABLE=true \
  --link zookeeper wurstmeister/kafka:2.13-2.8.1
```

## Running the Test

Once all services are running, you can run the integration test:

```
pytest -v eckert4/tests/test_main_docker.py
```

Logs will be written to `test_crawl.log` for inspection.

---

## Reading the Output Parquet File

The crawl results are saved as a Parquet file (e.g., `cnn_com.parquet`).

### Using Python (pandas)

You can read the Parquet file using pandas:

```python
import pandas as pd

df = pd.read_parquet('cnn_com.parquet')
print(df.head())
```

Make sure you have the required dependencies:
```
pip install pandas pyarrow
```

### Using parquet-tools (CLI)

If you want to inspect the file from the command line, you can use [parquet-tools](https://github.com/apache/parquet-mr/tree/master/parquet-tools):

```
parquet-tools head cnn_com.parquet
```

To install parquet-tools:
- On Ubuntu: `sudo apt install parquet-tools` (if available)
- Or download the jar from the [official repo](https://github.com/apache/parquet-mr/tree/master/parquet-tools) and run with Java. 