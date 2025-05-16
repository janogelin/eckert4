aimport os
import time
import subprocess
import pytest
import requests
from multiprocessing import Process
from fastapi import FastAPI
from uvicorn import Config, Server
from app.main import app
import etcd3
import shutil
import socket
import traceback

MEMCACHED_PORT = 11211
ETCD_PORT = 2379
LOG_FILE = "test_crawl.log"
THREAD_LIMIT = 5

# Helper to run FastAPI server in a subprocess, redirecting output to a log file
def run_server():
    config = Config(app=app, host="0.0.0.0", port=8000, log_level="debug")
    server = Server(config)
    server.run()

@pytest.fixture(scope="module", autouse=True)
def setup_services():
    print("[DEBUG] Starting setup_services fixture...")
    with open(LOG_FILE, "a") as logf:
        logf.write("[DEBUG] Starting setup_services fixture...\n")
    # Log environment variables
    print(f"[DEBUG] ENV: {os.environ}")
    with open(LOG_FILE, "a") as logf:
        logf.write(f"[DEBUG] ENV: {os.environ}\n")
    # Remove old log file if it exists
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    # Check Memcached health (assume Memcached is already running)
    print("[DEBUG] Checking that Memcached is already running on the host...")
    with open(LOG_FILE, "a") as logf:
        logf.write("[DEBUG] Checking that Memcached is already running on the host...\n")
    memcached_healthy = False
    for attempt in range(10):
        try:
            print(f"[DEBUG] Attempting Memcached connection (attempt {attempt+1})...")
            with open(LOG_FILE, "a") as logf:
                logf.write(f"[DEBUG] Attempting Memcached connection (attempt {attempt+1})...\n")
            sock = socket.create_connection(("localhost", MEMCACHED_PORT), timeout=2)
            sock.close()
            from pymemcache.client import base as memcache_base
            client = memcache_base.Client(("localhost", MEMCACHED_PORT))
            test_key = "test_key"
            test_value = b"test_value"
            client.set(test_key, test_value)
            value = client.get(test_key)
            if value == test_value:
                print(f"[MEMCACHED STATUS] Set/get test succeeded on attempt {attempt+1}")
                with open(LOG_FILE, "a") as logf:
                    logf.write(f"[MEMCACHED STATUS] Set/get test succeeded on attempt {attempt+1}\n")
                memcached_healthy = True
                break
            else:
                print(f"[MEMCACHED ERROR] Set/get test failed on attempt {attempt+1}")
                with open(LOG_FILE, "a") as logf:
                    logf.write(f"[MEMCACHED ERROR] Set/get test failed on attempt {attempt+1}\n")
        except Exception as e:
            print(f"[MEMCACHED ERROR] Attempt {attempt+1}: {e}")
            traceback.print_exc()
            with open(LOG_FILE, "a") as logf:
                logf.write(f"[MEMCACHED ERROR] Attempt {attempt+1}: {e}\n")
                logf.write(traceback.format_exc())
            time.sleep(2)
    if not memcached_healthy:
        print("[DEBUG] Memcached is not healthy after multiple attempts.")
        with open(LOG_FILE, "a") as logf:
            logf.write("[DEBUG] Memcached is not healthy after multiple attempts.\n")
        raise RuntimeError("Memcached is not healthy after multiple attempts.")
    print("[INFO] Memcached is running and healthy.")
    with open(LOG_FILE, "a") as logf:
        logf.write("[INFO] Memcached is running and healthy.\n")
    # Robust etcd health check with retries
    etcd_healthy = False
    etcd = None
    for attempt in range(10):
        try:
            print(f"[DEBUG] Attempting etcd connection (attempt {attempt+1})...")
            with open(LOG_FILE, "a") as logf:
                logf.write(f"[DEBUG] Attempting etcd connection (attempt {attempt+1})...\n")
            etcd = etcd3.client(host="localhost", port=ETCD_PORT)
            status = etcd.status()
            print(f"[ETCD STATUS] {status}")
            with open(LOG_FILE, "a") as logf:
                logf.write(f"[ETCD STATUS] {status}\n")
            etcd_healthy = True
            break
        except Exception as e:
            print(f"[ETCD ERROR] Attempt {attempt+1}: {e}")
            traceback.print_exc()
            with open(LOG_FILE, "a") as logf:
                logf.write(f"[ETCD ERROR] Attempt {attempt+1}: {e}\n")
                logf.write(traceback.format_exc())
            time.sleep(2)
    if not etcd_healthy:
        print("[DEBUG] etcd is not healthy after multiple attempts.")
        with open(LOG_FILE, "a") as logf:
            logf.write("[DEBUG] etcd is not healthy after multiple attempts.\n")
        raise RuntimeError("etcd is not healthy after multiple attempts.")
    print("[INFO] etcd is running and healthy.")
    with open(LOG_FILE, "a") as logf:
        logf.write("[INFO] etcd is running and healthy.\n")
    # Store and list keys in etcd
    try:
        example_key = "/test/example_url"
        example_value = "https://example.com"
        etcd.put(example_key, example_value)
        all_keys = [metadata.key.decode() for value, metadata in etcd.get_all()]
        print(f"[ETCD ALL KEYS] {all_keys}")
        with open(LOG_FILE, "a") as logf:
            logf.write(f"[ETCD ALL KEYS] {all_keys}\n")
    except Exception as e:
        print(f"[DEBUG] Exception during etcd key storage/listing: {e}")
        traceback.print_exc()
        with open(LOG_FILE, "a") as logf:
            logf.write(f"[DEBUG] Exception during etcd key storage/listing: {e}\n")
            logf.write(traceback.format_exc())
        raise
    # Test etcd politeness semaphore logic
    test_domain = "example.com"
    acquired = []
    for i in range(THREAD_LIMIT):
        try:
            key, lease = acquire_thread_slot(etcd, test_domain)
            if key:
                print(f"[ETCD POLITENESS] Acquired slot {i+1}: {key}")
                with open(LOG_FILE, "a") as logf:
                    logf.write(f"[ETCD POLITENESS] Acquired slot {i+1}: {key}\n")
                acquired.append((key, lease))
            else:
                print(f"[ETCD POLITENESS] Failed to acquire slot {i+1}")
                with open(LOG_FILE, "a") as logf:
                    logf.write(f"[ETCD POLITENESS] Failed to acquire slot {i+1}\n")
        except Exception as e:
            print(f"[DEBUG] Exception during etcd politeness acquire: {e}")
            traceback.print_exc()
            with open(LOG_FILE, "a") as logf:
                logf.write(f"[DEBUG] Exception during etcd politeness acquire: {e}\n")
                logf.write(traceback.format_exc())
    # Try to acquire one more slot, should fail
    try:
        key, lease = acquire_thread_slot(etcd, test_domain)
        if not key:
            print(f"[ETCD POLITENESS] Correctly enforced thread limit for {test_domain}")
            with open(LOG_FILE, "a") as logf:
                logf.write(f"[ETCD POLITENESS] Correctly enforced thread limit for {test_domain}\n")
        else:
            print(f"[ETCD POLITENESS] ERROR: Acquired slot beyond limit: {key}")
            with open(LOG_FILE, "a") as logf:
                logf.write(f"[ETCD POLITENESS] ERROR: Acquired slot beyond limit: {key}\n")
    except Exception as e:
        print(f"[DEBUG] Exception during etcd politeness over-acquire: {e}")
        traceback.print_exc()
        with open(LOG_FILE, "a") as logf:
            logf.write(f"[DEBUG] Exception during etcd politeness over-acquire: {e}\n")
            logf.write(traceback.format_exc())
    # Release all acquired slots
    for idx, (key, lease) in enumerate(acquired):
        try:
            release_thread_slot(etcd, key, lease)
            print(f"[ETCD POLITENESS] Released slot {idx+1}: {key}")
            with open(LOG_FILE, "a") as logf:
                logf.write(f"[ETCD POLITENESS] Released slot {idx+1}: {key}\n")
        except Exception as e:
            print(f"[DEBUG] Exception during etcd politeness release: {e}")
            traceback.print_exc()
            with open(LOG_FILE, "a") as logf:
                logf.write(f"[DEBUG] Exception during etcd politeness release: {e}\n")
                logf.write(traceback.format_exc())
    # Start FastAPI server, redirecting stdout/stderr to log file
    print("[DEBUG] Launching FastAPI server...")
    with open(LOG_FILE, "a") as logf:
        logf.write("[DEBUG] Launching FastAPI server...\n")
    server_proc = Process(target=run_server)
    with open(LOG_FILE, "w") as logf:
        server_proc = subprocess.Popen([
            "venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "debug"
        ], stdout=logf, stderr=logf)
        print(f"[DEBUG] FastAPI server process PID: {server_proc.pid}")
        with open(LOG_FILE, "a") as logf2:
            logf2.write(f"[DEBUG] FastAPI server process PID: {server_proc.pid}\n")
        time.sleep(2)
        yield
        # Teardown
        print("[DEBUG] Tearing down services...")
        with open(LOG_FILE, "a") as logf:
            logf.write("[DEBUG] Tearing down services...\n")
        server_proc.terminate()
        print("[DEBUG] Teardown complete.")
        with open(LOG_FILE, "a") as logf:
            logf.write("[DEBUG] Teardown complete.\n")

def acquire_thread_slot(etcd, domain):
    prefix = f"/crawler/semaphores/{domain}/"
    keys = list(etcd.get_prefix(prefix, keys_only=True))
    if len(keys) < THREAD_LIMIT:
        lease = etcd.lease(300)  # 5 minutes
        import uuid
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

def test_crawl_endpoint():
    print("[TEST] Starting /crawl endpoint test...")
    with open(LOG_FILE, "a") as logf:
        logf.write("[TEST] Starting /crawl endpoint test...\n")
    # Test the /crawl endpoint
    url = "http://localhost:8000/crawl"
    data = {"urls": ["https://www.cnn.com"]}
    try:
        print(f"[DEBUG] Sending POST to {url} with data: {data}")
        with open(LOG_FILE, "a") as logf:
            logf.write(f"[DEBUG] Sending POST to {url} with data: {data}\n")
        response = requests.post(url, json=data)
        print(f"[TEST] POST {url} response: {response.status_code} {response.text}")
        with open(LOG_FILE, "a") as logf:
            logf.write(f"[TEST] POST {url} response: {response.status_code} {response.text}\n")
        assert response.status_code == 200
        assert response.json()["status"] == "Crawling started"
    except Exception as e:
        print(f"[TEST ERROR] Exception during crawl endpoint test: {e}")
        traceback.print_exc()
        with open(LOG_FILE, "a") as logf:
            logf.write(f"[TEST ERROR] Exception during crawl endpoint test: {e}\n")
            logf.write(traceback.format_exc())
        raise
    # Print the log file contents for inspection
    print("\n--- Server and Crawler Log ---")
    with open(LOG_FILE, "r") as logf:
        print(logf.read())
    print("--- End of Log ---\n") 