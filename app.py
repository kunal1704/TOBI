import streamlit as st

from extraction.website_extractor import extract_website_text
from extraction.link_extractor import get_internal_links
from retrieval.link_filter import filter_relevant_links
from retrieval.semantic_ranker import rank_pages_semantically
from generation.profile_extractor import extract_recipient_profile
from configs import *

"""
TOBI Main Application
---------------------

Primary Streamlit interface for the TOBI pipeline.

Pipeline Stages:
1. Website extraction
2. Internal link discovery
3. Relevance filtering
4. Semantic ranking
5. Recipient profile generation

Author: Kunal Kumar Pant
Project: TOBI
"""

st.set_page_config(page_title="TOBI", layout="wide")

st.title("TOBI")
st.subheader("Tonally Obliged, Bespoke Interface")

recipient = st.text_input("Recipient Name")

website = st.text_input("Website URL")

goal = st.text_area("Outreach Goal")

tone = st.selectbox(
    "Tone",
    [
        "Professional",
        "Warm",
        "Research-Oriented",
        "Concise",
        "Intellectually Curious"
    ]
)

if st.button("Generate Email"):

    if not website:
        st.error("Please enter a website URL.")
        st.stop()

    st.info("Starting TOBI retrieval pipeline...")

    # -----------------------------------------
    # STEP 1: Extract homepage
    # -----------------------------------------

    homepage_text = extract_website_text(website)

    if homepage_text:
        st.success("Homepage extracted successfully.")
    else:
        st.warning("Could not extract homepage text.")

    # -----------------------------------------
    # STEP 2: Discover internal links
    # -----------------------------------------

    st.info("Discovering internal links...")

    links = get_internal_links(website)

    st.write(f"Total internal links found: {len(links)}")

    # -----------------------------------------
    # STEP 3: Filter relevant links
    # -----------------------------------------

    filtered_links = filter_relevant_links(links)

    st.success(f"Relevant links found: {len(filtered_links)}")

    st.write("Relevant Links:")

    for item in filtered_links:

        st.write(f"""
        URL: {item['url']}
        Score: {item['score']}
        Categories: {item['categories']}
        """)

    # -----------------------------------------
    # STEP 4: Multi-page extraction
    # -----------------------------------------

    st.info("Extracting relevant pages...")

    page_data = []

    # Add homepage
    if homepage_text:

        page_data.append({
            "url": website,
            "text": homepage_text
        })

    # Extract filtered pages
    for idx, item in enumerate(filtered_links[:MAX_PAGES]):

        link = item["url"]

        st.write(f"Extracting page {idx + 1}: {link}")

        extracted = extract_website_text(link)

        if extracted:

            page_data.append({
                "url": link,
                "text": extracted
            })

    # -----------------------------------------
    # STEP 5: Semantic Ranking
    # -----------------------------------------

    st.info("Performing semantic relevance ranking...")

    ranked_pages = rank_pages_semantically(page_data)

    st.success("Semantic ranking completed.")

    st.subheader("Top Ranked Pages")

    for page in ranked_pages[:5]:

        st.write(f"""
        URL: {page['url']}

        Semantic Score: {page['semantic_score']}
        """)

    # -----------------------------------------
    # STEP 6: Build final combined context
    # -----------------------------------------

    combined_text = ""
    

    for page in ranked_pages[:SEMANTIC_TOP_K]:

        combined_text += f"\n\nPAGE: {page['url']}\n\n"

        combined_text += page["text"][:MAX_TEXT_PER_PAGE]

    st.info("Extracting recipient intelligence...")

    profile = extract_recipient_profile(combined_text)

    st.success("Recipient profile extracted.")

    st.json(profile)
    # -----------------------------------------
    # STEP 7: Display combined extraction
    # -----------------------------------------

    st.success("Combined contextual extraction completed.")

    st.text_area(
        "Combined Extracted Context",
        combined_text[:FINAL_CONTEXT_LIMIT],
        height=500
    )