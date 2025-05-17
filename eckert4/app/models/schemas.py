from pydantic import BaseModel, HttpUrl
from typing import List

class URLListRequest(BaseModel):
    urls: List[HttpUrl]

# Avro schema for a crawled web page (as a string)
CRAWLED_PAGE_AVRO_SCHEMA = '''
{
  "namespace": "eckert4.avro",
  "type": "record",
  "name": "CrawledPage",
  "fields": [
    {"name": "normalized_url", "type": "string"},
    {"name": "title", "type": "string"},
    {"name": "text", "type": "string"},
    {"name": "timestamp", "type": "string"}
  ]
}
'''

# Avro schema for anchor URLs (as a string)
ANCHOR_URL_AVRO_SCHEMA = '''
{
  "namespace": "eckert4.avro",
  "type": "record",
  "name": "AnchorUrl",
  "fields": [
    {"name": "normalized_url", "type": "string"},
    {"name": "source_url", "type": "string"},
    {"name": "timestamp", "type": "string"}
  ]
}
'''

