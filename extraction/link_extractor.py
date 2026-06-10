import requests
from bs4 import BeautifulSoup
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
        soup = BeautifulSoup(response.text, "html.parser")

        links = set()

        base_domain = urlparse(safe_url).netloc

        for tag in soup.find_all("a", href=True):
            href = tag["href"]

            full_url = urljoin(safe_url, href)

            parsed = urlparse(full_url)

            if parsed.scheme in {"http", "https"} and parsed.netloc == base_domain:
                links.add(parsed._replace(fragment="").geturl())

        return list(links)

    except Exception as e:
        print(f"Error extracting links: {e}")
        return []
