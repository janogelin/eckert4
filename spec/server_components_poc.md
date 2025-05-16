# Server Components Proof of Concept (PoC)

## Overview
This document outlines a proof of concept (PoC) for deploying the core server components of the system using a simple Kubernetes setup with either Rancher or MicroK8s. The goal is to demonstrate basic orchestration, service connectivity, and scalability in a local or small-scale environment.

## Architecture Diagram
```
[User/API Client]
      |
  [FastAPI Service]  <---+--- [Memcached]
      |                  |
      |                  +--- [etcd]
      |                  |
      |                  +--- [Kafka]
      |                  |
      |                  +--- [Chroma Vector DB]
      |
  [Consumers: Anchortext Parser, Embeddings Processor]
```

## Core Components
- **FastAPI Service**: Handles incoming URL lists and orchestrates crawling.
- **page_crawler.py**: Used as the main crawling logic (from guanacos project).
- **Memcached**: Caching for normalized URLs and timestamps.
- **etcd**: Distributed coordination and thread limit enforcement.
- **Kafka**: Message queue for Parquet data.
- **Chroma**: Vector database for embeddings.
- **Consumers**: Separate pods/services for anchortext parsing and embedding processing.

## Kubernetes Setup Options
- **Rancher Desktop**: Easy GUI for managing local Kubernetes clusters.
- **MicroK8s**: Lightweight, single-node Kubernetes for local development.

## Basic Deployment Steps
1. **Install MicroK8s or Rancher Desktop**
   - MicroK8s: `sudo snap install microk8s --classic`
   - Rancher Desktop: Download and install from [rancherdesktop.io](https://rancherdesktop.io/)
2. **Enable Required Add-ons (MicroK8s)**
   - `microk8s enable dns storage ingress metallb`
3. **Deploy Core Services**
   - Use Kubernetes manifests or Helm charts for:
     - FastAPI Service (with page_crawler.py)
     - Memcached
     - etcd
     - Kafka (use bitnami/kafka Helm chart for simplicity)
     - Chroma (as a containerized service)
     - Consumers (as separate deployments)
4. **Expose Services**
   - Use NodePort or Ingress for FastAPI endpoint.
   - Internal ClusterIP for supporting services.
5. **Test End-to-End Flow**
   - Submit a list of URLs to FastAPI.
   - Verify crawling, caching, message queuing, and consumer processing.

## Example: Deploying FastAPI Service
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: fastapi-service
  template:
    metadata:
      labels:
        app: fastapi-service
    spec:
      containers:
      - name: fastapi
        image: yourrepo/fastapi-crawler:latest
        ports:
        - containerPort: 8000
```

## Notes
- For a minimal PoC, all components can run on a single node.
- Use persistent volumes for Kafka and Chroma if data durability is needed.
- Scale up by increasing replicas or moving to a multi-node cluster as needed.

---

_This PoC provides a foundation for iterating towards a production-grade, cloud-native deployment._ 