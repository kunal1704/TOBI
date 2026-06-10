import ipaddress
import socket
from urllib.parse import urlparse

import trafilatura


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
    downloaded = trafilatura.fetch_url(safe_url)

    if downloaded is None:
        return None

    text = trafilatura.extract(downloaded)

    return text
