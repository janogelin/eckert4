# Eckert4 Automated Integration & Anchortext Extraction Test (scripts/)

## Overview

This directory contains the automation script for running a full end-to-end test of the Eckert4 distributed crawler, Kafka pipeline, and anchortext extraction workflow. The script launches all required containers, runs the main app and test consumers, and verifies the full data flow from crawl to Kafka to anchor extraction.

---

## Prerequisites

- Docker and Docker Compose installed
- Python 3.8+ (for development, not required for running the test script)
- All required Docker images built (see below)
- The `kafka-net` Docker network created

### Create the Docker Network
```
docker network create kafka-net
```

---

## Required Services (All on kafka-net)

### etcd (as etcd-test)
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

### Memcached (as memcached-test)
```
docker run -d \
  --name memcached-test \
  --network kafka-net \
  memcached:latest \
  memcached -vv
```

### Zookeeper
```
docker run -d --rm --name zookeeper --network kafka-net -p 2181:2181 zookeeper:3.8
```

### Kafka (as kafka)
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

### (Optional) Kafdrop for Kafka UI
```
docker run --rm -d --name kafdrop --network kafka-net \
  -e KAFKA_BROKERCONNECT=kafka:9092 \
  -p 9000:9000 obsidiandynamics/kafdrop
```

---

## Building Required Docker Images

- **Main app:**
  ```
  docker build -f Dockerfile.main_app -t eckert4-main-app .
  ```
- **Anchortext test consumer:**
  ```
  docker build -f Dockerfile.anchortext_test -t anchortext-test-consumer .
  ```

---

## Running the Automated Test

From the project root, run:
```
./scripts/test_anchortext_flow.sh
```

This script will:
- Clean up any old containers or log files
- Wait for etcd and Memcached to be healthy
- Delete the `crawled_pages` topic from Kafka
- Launch the main app as a container on `kafka-net`
- Crawl a new test URL (edit the script to change the URL)
- Build and run the anchortext test consumer as a container
- Print extracted anchor URLs to `anchortext_test.log` and to stdout
- Clean up all test containers and images

---

## Interpreting Results

- If successful, you will see anchor URLs from the test page in `anchortext_test.log` and in the script output.
- If the log file is empty, check that the test URL is truly new and that all services are running on `kafka-net`.
- The main app logs and consumer logs will be printed to the terminal for debugging.

---

## Customizing the Test URL

Edit the `TEST_URL` variable in `scripts/test_anchortext_flow.sh` to use any URL you want to crawl and extract anchors from. Make sure it is a URL that has not been crawled before, or clear Memcached/etcd state for a true end-to-end test.

---

## Troubleshooting

- **etcd or Memcached not healthy:**
  - Ensure both containers are running on `kafka-net` with the correct names.
  - Use `docker ps` to check container status.
- **Kafka connection errors:**
  - Ensure Kafka is running as `kafka` on `kafka-net` and is healthy.
  - Check logs with `docker logs kafka`.
- **Topic already exists or not deleted:**
  - The script deletes the `crawled_pages` topic before each run. If you see errors, ensure Kafka is healthy.
- **Log file is empty:**
  - The test URL may have already been crawled. Use a new URL or clear Memcached/etcd.
  - Check consumer logs for errors.
- **Container name conflicts:**
  - The script now pre-cleans containers, but you can manually stop containers with `docker stop <name>` if needed.

---

## Extending the Workflow

- To add new Kafka consumers, create a new consumer script in `eckert4/app/consumers/`, build a Docker image, and add a step to the test script.
- To test new topics, update the topic name in the test script and consumer.
- To run the main app or consumers with different environment variables, edit the `docker run` commands in the script.

---

## Contact & Contributions

For questions, issues, or contributions, please open an issue or pull request on the project repository.

---

**Happy crawling and testing!** 