"""
Heuristic Link Filtering Module
-------------------------------

Scores discovered URLs using keyword-category matching
to identify pages likely to contain:
- research information
- publications
- profiles
- projects
- writings

Acts as a lightweight pre-ranking stage before
semantic retrieval.
"""

KEYWORD_GROUPS = {
    "research": [
        "research",
        "investigation",
        "study",
        "scholarly"
    ],

    "publications": [
        "publication",
        "paper",
        "article",
        "journal",
        "conference",
        "preprint"
    ],

    "projects": [
        "project",
        "initiative",
        "prototype",
        "work"
    ],

    "personal": [
        "about",
        "bio",
        "profile",
        "cv",
        "resume"
    ],

    "writing": [
        "blog",
        "essay",
        "article",
        "writing",
        "notes"
    ],

    "interest": [
        "interest",
        "passion",
        "focus",
        "specialize",
        "expertise",
        "research interests"
    ]
}


IGNORE_KEYWORDS = [
    "login",
    "signup",
    "privacy",
    "terms",
    "cookie",
    "admin"
]


def filter_relevant_links(links):

    scored_links = []

    for link in links:

        lower = link.lower()

        if any(ignore in lower for ignore in IGNORE_KEYWORDS):
            continue

        score = 0

        matched_categories = []

        for category, words in KEYWORD_GROUPS.items():

            if any(word in lower for word in words):

                score += 1
                matched_categories.append(category)

        if score > 0:

            scored_links.append({
                "url": link,
                "score": score,
                "categories": matched_categories
            })

    scored_links.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return scored_links