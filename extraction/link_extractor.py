import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

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
        response = requests.get(base_url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        links = set()

        base_domain = urlparse(base_url).netloc

        for tag in soup.find_all("a", href=True):
            href = tag["href"]

            full_url = urljoin(base_url, href)

            parsed = urlparse(full_url)

            if parsed.netloc == base_domain:
                links.add(full_url)

        return list(links)

    except Exception as e:
        print(f"Error extracting links: {e}")
        return []