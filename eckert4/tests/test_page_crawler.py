import pytest
from app.crawler.page_crawler import PageCrawler


def test_crawl_cnn():
    crawler = PageCrawler()
    result = crawler.crawl("https://www.cnn.com")
    assert isinstance(result, dict)
    assert "title" in result
    assert isinstance(result["title"], str)
    assert len(result["title"]) > 0
    assert "text" in result
    assert isinstance(result["text"], str)
    assert len(result["text"]) > 0 