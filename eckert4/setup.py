from setuptools import setup, find_packages

setup(
    name="eckert4",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn[standard]",
        "confluent-kafka",
        "pymemcache",
        "pyarrow",
        "tldextract",
        "pydantic",
        "beautifulsoup4",
        "etcd3",
        "protobuf==3.20.3",
    ],
    entry_points={
        "console_scripts": [
            # Add CLI entry points here if needed
        ]
    },
    include_package_data=True,
    description="Distributed polite web crawler with FastAPI, Kafka, Memcached, and etcd.",
    author="Your Name",
    author_email="your.email@example.com",
    url="",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
) 