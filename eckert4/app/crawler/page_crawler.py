import requests
from bs4 import BeautifulSoup
from typing import Dict, Any

class PageCrawler:
    """
    A simple web page crawler that fetches a URL and parses its content using BeautifulSoup.
    Returns extracted data as a dictionary.
    """

    def fetch_page(self, url: str) -> str:
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/122.0.0.0 Safari/537.36'
            )
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text

    def parse_content(self, html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.title.string if soup.title else ''
        texts = soup.stripped_strings
        visible_text = ' '.join(texts)
        return {
            'title': title,
            'text': visible_text
        }

    def crawl(self, url: str) -> Dict[str, Any]:
        html = self.fetch_page(url)
        data = self.parse_content(html)
        return data
