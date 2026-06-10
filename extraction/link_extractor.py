import requests
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from extraction.website_extractor import validate_public_url

"""
Internal Link Discovery Module
------------------------------

Extracts internal hyperlinks from a website homepage
using BeautifulSoup-based HTML parsing.

Used during the retrieval stage to discover
potentially relevant profile/research pages.
"""


class _HrefParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return

        for key, value in attrs:
            if key.lower() == "href" and value:
                self.links.add(value)


def get_internal_links(base_url):
    try:
        safe_url = validate_public_url(base_url)
        response = requests.get(
            safe_url,
            timeout=(3, 8),
            allow_redirects=False,
            headers={"User-Agent": "TOBI/1.0 public-profile-fetcher"},
        )
        response.raise_for_status()

        links = set()
        hrefs = set()

        base_domain = urlparse(safe_url).netloc

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(response.text, "html.parser")
            hrefs = {tag["href"] for tag in soup.find_all("a", href=True)}
        except Exception:
            parser = _HrefParser()
            parser.feed(response.text)
            hrefs = parser.links

        for href in hrefs:
            full_url = urljoin(safe_url, href)

            parsed = urlparse(full_url)

            if parsed.scheme in {"http", "https"} and parsed.netloc == base_domain:
                links.add(parsed._replace(fragment="").geturl())

        return list(links)

    except Exception as e:
        print(f"Error extracting links: {e}")
        return []
