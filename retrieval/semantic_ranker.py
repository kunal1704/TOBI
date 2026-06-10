"""
Semantic Page Ranking Module
----------------------------

Ranks extracted webpages using sentence-transformer
embeddings and cosine similarity against predefined
academic/professional semantic queries.

Purpose:
Improve retrieval quality for downstream
LLM-based personalization.
"""

model = None
query_embeddings = None

# Semantic queries representing useful academic/professional content
SEMANTIC_QUERIES = [
    "research interests",
    "publications and papers",
    "ongoing projects",
    "academic biography",
    "professional profile",
    "research philosophy",
    "technical expertise",
    "current work",
    "blogs and writings",
    "teaching and courses"
]


def _rank_pages_lexically(page_data):
    terms = {
        term
        for query in SEMANTIC_QUERIES
        for term in query.lower().split()
        if len(term) > 3
    }
    ranked_pages = []

    for page in page_data:
        text = page.get("text", "")

        if not text or len(text.strip()) < 100:
            continue

        lower_text = text[:5000].lower()
        matches = sum(lower_text.count(term) for term in terms)
        score = matches / max(1, len(terms))

        ranked_pages.append({
            "url": page["url"],
            "text": text,
            "semantic_score": round(score, 4),
        })

    ranked_pages.sort(
        key=lambda x: x["semantic_score"],
        reverse=True
    )

    return ranked_pages


def rank_pages_semantically(page_data):

    """
    page_data format:
    [
        {
            "url": "...",
            "text": "..."
        }
    ]
    """

    global model, query_embeddings

    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
    except ImportError:
        return _rank_pages_lexically(page_data)

    if model is None:
        model = SentenceTransformer("all-MiniLM-L6-v2")

    valid_pages = []

    if query_embeddings is None:
        query_embeddings = model.encode(SEMANTIC_QUERIES)

    for page in page_data:

        text = page["text"]

        if not text or len(text.strip()) < 100:
            continue

        valid_pages.append({
            "url": page["url"],
            "text": text,
            "truncated_text": text[:3000],
        })

    if not valid_pages:
        return []

    page_embeddings = model.encode([page["truncated_text"] for page in valid_pages])
    similarities = cosine_similarity(page_embeddings, query_embeddings)
    ranked_pages = []

    for page, page_similarities in zip(valid_pages, similarities):
        best_score = float(np.max(page_similarities))

        ranked_pages.append({
            "url": page["url"],
            "text": page["text"],
            "semantic_score": round(best_score, 4)
        })

    # Sort descending
    ranked_pages.sort(
        key=lambda x: x["semantic_score"],
        reverse=True
    )

    return ranked_pages
