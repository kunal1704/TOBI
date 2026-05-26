"""
Website Content Extraction Module
---------------------------------

Uses Trafilatura to extract clean textual content
from webpages while removing boilerplate HTML.

This forms the primary textual retrieval layer
for TOBI.

"""

import trafilatura


def extract_website_text(url):
    downloaded = trafilatura.fetch_url(url)

    if downloaded is None:
        return None

    text = trafilatura.extract(downloaded)

    return text