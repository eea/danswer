import pytest
from bs4 import BeautifulSoup
from onyx.utils.eea_utils import remove_by_selector

def test_remove_by_selector_simple():
    print("\n[Feature 3]: Testing web scraper HTML scrubbing (element removal by selector) -> OK")
    # Basic removal of matching elements
    html = "<html><body><div class='remove-me'>Noise</div><p>Valid Content</p></body></html>"
    soup = BeautifulSoup(html, "html.parser")

    remove_by_selector(soup, [".remove-me"])

    assert "Noise" not in str(soup)
    assert "Valid Content" in str(soup)

def test_remove_by_selector_with_meta_override():
    print("\n[Feature 3]: Testing web scraper HTML scrubbing (using dynamic page metadata) -> OK")
    # Checks if 'remove_by_selector' handles custom selectors from page metadata
    html = """
    <html>
        <head>
            <meta name="remove_by_selector" content="#extra-noise, .ad">
        </head>
        <body>
            <div id="extra-noise">Header Noise</div>
            <div class="ad">Sponsor content</div>
            <div class="regular-ad">Sidebar Ad</div>
            <p>Main content here</p>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")

    remove_by_selector(soup, [".regular-ad"])

    assert "Header Noise" not in str(soup)
    assert "Sponsor content" not in str(soup)
    assert "Sidebar Ad" not in str(soup)
    assert "Main content here" in str(soup)
