import ipaddress
import socket
from html.parser import HTMLParser
from urllib.parse import urlparse


"""
Website Content Extraction Module
---------------------------------

Uses Trafilatura to extract clean textual content
from webpages while removing boilerplate HTML.

This forms the primary textual retrieval layer
for TOBI.
"""


BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
}


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        text = (data or "").strip()
        if text:
            self.parts.append(text)

    def get_text(self):
        return " ".join(self.parts)


def validate_public_url(url):
    candidate = (url or "").strip()
    parsed = urlparse(candidate)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Please enter a valid public http(s) website URL.")

    if parsed.username or parsed.password:
        raise ValueError("Website URLs with embedded credentials are not allowed.")

    hostname = (parsed.hostname or "").strip().lower()

    if not hostname or hostname in BLOCKED_HOSTNAMES or hostname.endswith(".localhost"):
        raise ValueError("Please use a public website URL, not a local or private address.")

    try:
        ip = ipaddress.ip_address(hostname)
        if not ip.is_global:
            raise ValueError("Please use a public website URL, not a local or private address.")
    except ValueError as exc:
        if "public website URL" in str(exc):
            raise

    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError("TOBI could not resolve that website URL.") from exc

    for address in addresses:
        host = address[4][0]

        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            continue

        if not ip.is_global:
            raise ValueError("Please use a public website URL, not a local or private address.")

    return candidate


def extract_website_text(url):
    safe_url = validate_public_url(url)

    try:
        import requests
    except ImportError as exc:
        raise RuntimeError(
            "The requests package is not installed. "
            "Redeploy after Streamlit installs requirements.txt."
        ) from exc

    try:
        import trafilatura
    except ImportError:
        trafilatura = None

    if trafilatura is not None:
        downloaded = trafilatura.fetch_url(safe_url)

        if downloaded is None:
            return None

        text = trafilatura.extract(downloaded)
        if text:
            return text

    response = requests.get(
        safe_url,
        timeout=(3, 12),
        headers={"User-Agent": "TOBI/1.0 public-profile-fetcher"},
    )
    response.raise_for_status()

    parser = _TextExtractor()
    parser.feed(response.text)
    text = parser.get_text().strip()

    return text or None
