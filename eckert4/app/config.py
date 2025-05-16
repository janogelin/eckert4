import os

class Settings:
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "crawled_pages")
    MEMCACHED_HOST = os.getenv("MEMCACHED_HOST", "localhost")
    MEMCACHED_PORT = int(os.getenv("MEMCACHED_PORT", 11211))

settings = Settings()

