from pydantic import BaseModel, HttpUrl
from typing import List

class URLListRequest(BaseModel):
    urls: List[HttpUrl]

