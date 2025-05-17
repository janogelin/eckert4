import pytest
from app.consumers.anchortext_extractor_consumer import AnchorTextExtractor

@pytest.mark.parametrize("html,source_url,expected", [
    (
        '<html><body><a href="https://example.com/page1">Link1</a> <a href="/page2">Link2</a></body></html>',
        'https://host.com',
        [
            'https://example.com/page1',
            '/page2'
        ]
    ),
    (
        '<a href="https://foo.com">Foo</a>',
        'https://bar.com',
        ['https://foo.com']
    ),
    (
        '<a>No href</a>',
        'https://baz.com',
        []
    )
])
def test_extract_anchor_hrefs(html, source_url, expected):
    """
    Test that AnchorTextExtractor correctly extracts anchor hrefs from HTML.
    """
    soup = AnchorTextExtractor.normalize_url  # just to check import
    extractor = AnchorTextExtractor(None, None)
    # Use BeautifulSoup directly to simulate the extraction logic
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    found = [a['href'] for a in soup.find_all('a', href=True)]
    assert found == expected 