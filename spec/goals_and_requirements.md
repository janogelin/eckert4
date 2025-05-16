# Project Goals and Requirements

## Goals
1. Service should be able to take a list of URLs on a port and fetch pages from each domain, but restricted to the top-level domain of the site.
    - 1a. Service should be polite per top-level domain, restricted to 5 threads per top-level domain.
    - 1b. Service should normalize the URL and store it in memcached with a timestamp of last seen.
2. Service should put files in a Parquet file format onto a Kafka queue.
3. One consumer would be an anchortext parser that will, from the Parquet file, extract anchortext to the state with restriction to the site's top-level domain.
4. Another consumer will parse the Parquet file and store the embeddings in a vector database for later use with an LLM.

---

## Functional Requirements
- The service must accept a list of URLs via a specified port.
- The service must fetch web pages from each provided URL, restricted to the top-level domain of each site.
- The service must enforce a politeness policy, limiting to 5 concurrent threads per top-level domain.
- The service must normalize each URL and store it in memcached with a timestamp of when it was last seen.
- The service must serialize fetched data into Parquet file format and publish it to a Kafka queue.
- There must be a consumer that reads Parquet files from Kafka and extracts anchortext, restricted to the site's top-level domain.
- There must be a consumer that reads Parquet files from Kafka and stores embeddings in a vector database for later use with an LLM.

## Non-Functional Requirements
- The system should be scalable to handle multiple top-level domains and high input URL volume.
- The system should ensure data consistency and integrity when storing URLs and timestamps in memcached.
- The system should be fault-tolerant, ensuring that failures in one consumer do not affect others.
- The system should provide efficient and reliable serialization/deserialization of Parquet files.
- The system should maintain low latency for both fetching and processing URLs.
- The system should be secure, ensuring that only authorized users can submit URLs and access stored data.
- The system should be extensible to support additional consumers or processing steps in the future. 