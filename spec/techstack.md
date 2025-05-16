# Technology Stack

## Core Components
- **Programming Language:** Python (primary language for service logic, consumers, and data processing)
- **Web Framework:** FastAPI (for high-performance async API endpoints)
- **Crawling Component:** `page_crawler.py` from the [guanacos utils directory](https://github.com/janogelin/guanacos/tree/main/utils) (for robust, reusable crawling logic)
- **Concurrency & Coordination:** etcd (for distributed coordination and enforcing thread limits per TLD across nodes)
- **Async Processing:** asyncio, aiohttp (for non-blocking I/O and efficient crawling)
- **URL Normalization:** tldextract, urllib (for robust URL parsing and normalization)
- **Caching:** Memcached (for fast, in-memory storage of normalized URLs and timestamps)
- **Data Serialization:** Apache Parquet (efficient, columnar storage for web data)
- **Message Queue:** Apache Kafka (scalable, distributed event streaming)
- **Parquet Handling:** pyarrow (for reading/writing Parquet files)

## Consumers
- **Anchortext Parser:** Python, pyarrow, BeautifulSoup (for HTML parsing and anchortext extraction)
- **Embeddings Consumer:** Python, pyarrow, sentence-transformers or OpenAI API (for embedding generation), and Chroma vector database

## Vector Database Option
- **Chroma** (open-source, easy integration with Python and ML workflows)

## Infrastructure & DevOps
- **Containerization:** Docker (for reproducible, isolated environments)
- **Orchestration:** Kubernetes (for scaling, rolling updates, and service discovery)
- **Distributed Coordination:** etcd (for leader election, distributed locks, and configuration)
- **Monitoring & Logging:** Prometheus, Grafana (metrics), Loki (logs)
- **Authentication/Security:** OAuth2, API keys, or JWT (for securing endpoints)
- **Configuration Management:** environment variables, Kubernetes ConfigMaps/Secrets

## Optional/Extensions
- **Cloud Storage:** AWS S3, GCP Storage, or Azure Blob (for Parquet file backups and archival)
- **CI/CD:** GitHub Actions, GitLab CI, or Jenkins (for automated testing and deployment)
- **Infrastructure as Code:** Terraform or Helm (for reproducible infrastructure and deployments)

---

_This stack is inspired by modern, cloud-native, and distributed system best practices, as well as the structure and approach seen in the [guanacos project](https://github.com/janogelin/guanacos/blob/main/fresh/README.md). It is designed for scalability, reliability, and ease of integration with data and ML workflows. Adjust as needed for your team's expertise and deployment environment._ 