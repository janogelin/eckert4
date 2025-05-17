#!/bin/bash
set -e

# Pre-check: Remove old log file or directory and stop main app container if running
rm -rf anchortext_test.log
if docker ps --format '{{.Names}}' | grep -q '^eckert4-main-app-test$'; then
    docker stop eckert4-main-app-test || true
fi

# Cleanup function to remove Docker image, log file, and stop main app container
do_cleanup() {
    echo "[CLEANUP] Removing Docker image, log file, and stopping main app container..."
    docker rmi -f "$DOCKER_IMAGE" 2>/dev/null || true
    rm -f "$LOG_FILE"
    docker stop eckert4-main-app-test 2>/dev/null || true
}

docker_cleanup_needed=1
trap do_cleanup EXIT INT

# Check that memcached-test is running on kafka-net
if ! docker ps --format '{{.Names}}' | grep -q '^memcached-test$'; then
    echo "[ERROR] Memcached container 'memcached-test' is not running. Please launch it manually on kafka-net before running this script."
    exit 1
fi

# Wait for etcd to be healthy
ETCD_HEALTHY=0
echo "[WAIT] Waiting for etcd-test:2379 to be healthy..."
for i in {1..60}; do
    OUT=$(docker run --rm --network kafka-net curlimages/curl:7.88.1 -s -w '%{http_code}' http://etcd-test:2379/health)
    BODY="${OUT::-3}"
    CODE="${OUT: -3}"
    echo "[DEBUG] Attempt $i: HTTP $CODE, Body: $BODY"
    if echo "$BODY" | grep -q '"health":"true"'; then
        echo "[INFO] etcd is healthy."
        ETCD_HEALTHY=1
        break
    fi
    sleep 1
done
if [ $ETCD_HEALTHY -ne 1 ]; then
    echo "[ERROR] etcd did not become healthy in time."
    exit 1
fi

# Step 0: Delete the crawled_pages topic from Kafka to ensure a clean test
KAFKA_CONTAINER="kafka"
echo "[STEP 0] Deleting 'crawled_pages' topic from Kafka (if exists)..."
docker exec $KAFKA_CONTAINER bash -c "/opt/kafka/bin/kafka-topics.sh --delete --topic crawled_pages --bootstrap-server kafka:9092" || true

# Step 1: Launch the main app container
MAIN_APP_IMAGE="eckert4-main-app"
echo "[STEP 1] Launching main app container..."
docker run --rm --network kafka-net -p 8000:8000 --name eckert4-main-app-test -e MEMCACHED_HOST=memcached-test -e ETCD_HOST=etcd-test -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 "$MAIN_APP_IMAGE" &
MAIN_APP_PID=$!

# Wait for the FastAPI server to be up
for i in {1..30}; do
    if curl -s http://localhost:8000/docs >/dev/null; then
        echo "[INFO] Main app is up."
        break
    fi
    sleep 1
done

# Step 2: Crawl a test URL using the main program's REST API
TEST_URL="https://www.cnn.com"
API_ENDPOINT="http://localhost:8000/crawl_one"
LOG_FILE="anchortext_test.log"

# Remove old log file if exists
rm -f "$LOG_FILE"

echo "[STEP 2] Crawling test URL: $TEST_URL"
curl -X POST "$API_ENDPOINT" \
    -H "Content-Type: application/json" \
    -d '{"url": "'$TEST_URL'"}'

# Step 3: Build the Docker image for the anchortext test consumer
DOCKER_IMAGE="anchortext-test-consumer"
DOCKERFILE="Dockerfile.anchortext_test"

echo "[STEP 3] Building Docker image: $DOCKER_IMAGE"
docker build -f "$DOCKERFILE" -t "$DOCKER_IMAGE" .

# Step 4: Run the Docker container on kafka-net and wait for log output

echo "[STEP 4] Running Docker container and waiting for log output..."
touch anchortext_test.log
docker run --rm --network kafka-net -v "$(pwd)/anchortext_test.log:/app/anchortext_test.log" "$DOCKER_IMAGE" &
CONSUMER_PID=$!

# Wait for the log file to be created and have content
for i in {1..30}; do
    if [ -s "$LOG_FILE" ]; then
        break
    fi
    sleep 1
done

# Step 5: Print the log file contents
if [ -s "$LOG_FILE" ]; then
    echo "[STEP 5] Anchor text log file contents:"
    cat "$LOG_FILE"
else
    echo "[ERROR] Log file was not created or is empty."
fi

# Stop the consumer container if still running
kill $CONSUMER_PID 2>/dev/null || true

docker_cleanup_needed=0 