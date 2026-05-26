from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


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

# Load embedding model once
model = SentenceTransformer("all-MiniLM-L6-v2")

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

    ranked_pages = []

    # Create query embeddings
    query_embeddings = model.encode(SEMANTIC_QUERIES)

    for page in page_data:

        text = page["text"]

        if not text or len(text.strip()) < 100:
            continue

        # Limit text size for efficiency
        truncated_text = text[:3000]

        # Embed page
        page_embedding = model.encode([truncated_text])

        # Compute similarity with all semantic queries
        similarities = cosine_similarity(
            page_embedding,
            query_embeddings
        )[0]

        # Take best similarity score
        best_score = float(np.max(similarities))

        ranked_pages.append({
            "url": page["url"],
            "text": text,
            "semantic_score": round(best_score, 4)
        })

    # Sort descending
    ranked_pages.sort(
        key=lambda x: x["semantic_score"],
        reverse=True
    )

    return ranked_pages