# Project Tasklist

## Planning & Design
- [ ] Review and refine functional and non-functional requirements
- [ ] Finalize technology stack and architecture
- [ ] Design API contract for URL submission and status endpoints
- [ ] Define data schema for Parquet files and Kafka messages
- [ ] Plan Kubernetes resource requirements (CPU, memory, storage)

## Development
- [ ] Set up project repository and initial codebase structure
- [ ] Integrate `page_crawler.py` for crawling logic
- [ ] Implement FastAPI service for URL intake and orchestration
- [ ] Add URL normalization and Memcached integration
- [ ] Implement etcd-based concurrency and thread limit enforcement
- [ ] Serialize crawled data to Parquet format
- [ ] Publish Parquet data to Kafka
- [ ] Develop anchortext parser consumer
- [ ] Develop embeddings consumer with Chroma integration
- [ ] Add logging, error handling, and metrics collection

## Deployment
- [ ] Write Kubernetes manifests or Helm charts for all components
- [ ] Set up MicroK8s or Rancher Desktop cluster
- [ ] Deploy Memcached, etcd, Kafka, and Chroma
- [ ] Deploy FastAPI service and consumers
- [ ] Configure service exposure (NodePort/Ingress)
- [ ] Set up persistent volumes for stateful services

## Testing & Validation
- [ ] Write unit and integration tests for core modules
- [ ] Test end-to-end flow: URL submission to vector DB
- [ ] Validate thread limits and politeness per TLD
- [ ] Verify data integrity in Memcached, Kafka, and Chroma
- [ ] Monitor resource usage and system health
- [ ] Document setup, usage, and troubleshooting steps

---

_This tasklist provides a roadmap for building, deploying, and validating the system as described in the specifications and PoC._ 