#!/bin/bash
set -e

# This script runs the anchor URL Avro test workflow in Docker using the kafka-net network.
# Requirements (must be running in the kafka-net network with these names):
#   - etcd-test
#   - memcached-test
#   - kafka
#   - zookeeper
# Each container is launched with --rm and --name for easy cleanup.
# Assumes Kafka, Zookeeper, Memcached, and etcd are already running on the kafka-net network.
#
# For maximum reproducibility, consider pinning the Python image to a specific patch version, e.g. python:3.10.14-slim

NETWORK="kafka-net"
PRODUCER_NAME="anchor-url-producer"
CONSUMER_NAME="anchor-url-debug-consumer"
PY_IMAGE="python:3.10-slim"
APP_DIR=$(cd "$(dirname "$0")/.." && pwd)

# Cleanup old containers if they exist
for cname in "$PRODUCER_NAME" "$CONSUMER_NAME"; do
  if docker ps -a --format '{{.Names}}' | grep -Eq "^$cname$"; then
    echo "[INFO] Removing old container $cname..."
    docker rm -f $cname || true
  fi
done

# Make appuser UID configurable
APPUSER_UID=${APPUSER_UID:-1000}
USER_SETUP="id -u appuser &>/dev/null || useradd -m -u $APPUSER_UID appuser; chown -R appuser /app"
PIP_FLAGS="--user"

# Install python3-wheel via apt before pip installs (best practice)
APT_WHEEL_INSTALL="apt-get update && apt-get install -y python3-wheel && rm -rf /var/lib/apt/lists/*"

# Check required containers
REQUIRED_CONTAINERS=(etcd-test memcached-test kafka zookeeper)
for cname in "${REQUIRED_CONTAINERS[@]}"; do
  if ! docker inspect -f '{{.State.Running}}' "$cname" 2>/dev/null | grep -q true; then
    echo "[ERROR] Required container '$cname' is not running in network '$NETWORK'" >&2
    exit 1
  fi
done

# Wait for Kafka to be ready
KAFKA_WAIT_RETRIES=10
KAFKA_WAIT_DELAY=2
for i in $(seq 1 $KAFKA_WAIT_RETRIES); do
  if docker exec kafka bash -c 'echo > /dev/tcp/localhost/9092' 2>/dev/null; then
    echo "[INFO] Kafka is ready."
    break
  else
    echo "[INFO] Waiting for Kafka to be ready ($i/$KAFKA_WAIT_RETRIES)..."
    sleep $KAFKA_WAIT_DELAY
  fi
done

# Run Avro roundtrip test
echo "[INFO] Running anchor URL Avro producer (pytest)..."
docker run --rm --name $PRODUCER_NAME --network $NETWORK -v "$APP_DIR":/app -w /app \
  $PY_IMAGE bash -c "$APT_WHEEL_INSTALL && $USER_SETUP && su appuser -c 'export PATH=/home/appuser/.local/bin:$PATH && pip install --upgrade pip $PIP_FLAGS && pip install -r requirements.txt $PIP_FLAGS && pip install pytest $PIP_FLAGS && pip install avro-python3 $PIP_FLAGS && pip list && pytest tests/test_anchor_url_avro.py'"

# Produce a test anchor URL Avro message to Kafka
echo "[INFO] Producing a test anchor URL Avro message to Kafka..."
docker run --rm --name ${PRODUCER_NAME}_msg --network $NETWORK -v "$APP_DIR":/app -w /app \
  -e PYTHONPATH=/app \
  $PY_IMAGE bash -c "$APT_WHEEL_INSTALL && $USER_SETUP && su appuser -c 'export PATH=/home/appuser/.local/bin:$PATH && pip install --upgrade pip $PIP_FLAGS && pip install -r requirements.txt $PIP_FLAGS && pip install avro-python3 $PIP_FLAGS && pip list && python app/consumers/produce_test_anchor_url.py'"

# Print anchor text URLs from debug consumer
echo "[INFO] Running anchor URL Avro debug consumer and printing anchor text URLs to stdout..."
docker run --rm --name $CONSUMER_NAME --network $NETWORK -v "$APP_DIR":/app -w /app \
  -e PYTHONPATH=/app \
  $PY_IMAGE bash -c "$APT_WHEEL_INSTALL && $USER_SETUP && su appuser -c 'export PATH=/home/appuser/.local/bin:$PATH && pip install --upgrade pip $PIP_FLAGS && pip install -r requirements.txt $PIP_FLAGS && pip install pytest $PIP_FLAGS && pip install avro-python3 $PIP_FLAGS && pip list && python app/consumers/debug_anchor_url_consumer.py'"

echo "[INFO] Workflow complete. All containers cleaned up." 