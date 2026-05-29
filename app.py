import streamlit as st

from extraction.website_extractor import extract_website_text
from extraction.link_extractor import get_internal_links
from retrieval.link_filter import filter_relevant_links
from retrieval.semantic_ranker import rank_pages_semantically
from generation.profile_extractor import extract_recipient_profile
from generation.email_generator import generate_email_draft
from gmail_drafts import create_gmail_draft
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
6. User-guided outreach drafting
7. Gmail draft creation

Author: Kunal Kumar Pant
Project: TOBI
"""


TONES = [
    "Professional",
    "Warm",
    "Research-Oriented",
    "Concise",
    "Intellectually Curious"
]


def initialize_state():
    defaults = {
        "profile": None,
        "combined_text": "",
        "ranked_pages": [],
        "email_draft": None,
        "gmail_result": None
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def run_retrieval_pipeline(website):
    st.info("Starting TOBI retrieval pipeline...")

    homepage_text = extract_website_text(website)

    if homepage_text:
        st.success("Homepage extracted successfully.")
    else:
        st.warning("Could not extract homepage text.")

    st.info("Discovering internal links...")

    links = get_internal_links(website)

    st.write(f"Total internal links found: {len(links)}")

    filtered_links = filter_relevant_links(links)

    st.success(f"Relevant links found: {len(filtered_links)}")

    with st.expander("Relevant links"):
        for item in filtered_links:
            st.write(f"URL: {item['url']}")
            st.write(f"Score: {item['score']}")
            st.write(f"Categories: {item['categories']}")

    st.info("Extracting relevant pages...")

    page_data = []

    if homepage_text:
        page_data.append({
            "url": website,
            "text": homepage_text
        })

    for idx, item in enumerate(filtered_links[:MAX_PAGES]):
        link = item["url"]

        st.write(f"Extracting page {idx + 1}: {link}")

        extracted = extract_website_text(link)

        if extracted:
            page_data.append({
                "url": link,
                "text": extracted
            })

    st.info("Performing semantic relevance ranking...")

    ranked_pages = rank_pages_semantically(page_data)

    st.success("Semantic ranking completed.")

    combined_text = ""

    for page in ranked_pages[:SEMANTIC_TOP_K]:
        combined_text += f"\n\nPAGE: {page['url']}\n\n"
        combined_text += page["text"][:MAX_TEXT_PER_PAGE]

    st.info("Extracting recipient intelligence...")

    profile = extract_recipient_profile(combined_text)

    st.success("Recipient profile extracted.")

    st.session_state.profile = profile
    st.session_state.combined_text = combined_text
    st.session_state.ranked_pages = ranked_pages
    st.session_state.email_draft = None
    st.session_state.gmail_result = None


def render_extraction_results():
    if not st.session_state.profile:
        return

    st.subheader("Recipient Intelligence")
    st.json(st.session_state.profile)

    with st.expander("Top ranked pages"):
        for page in st.session_state.ranked_pages[:5]:
            st.write(f"URL: {page['url']}")
            st.write(f"Semantic Score: {page['semantic_score']}")

    with st.expander("Combined extracted context"):
        st.text_area(
            "Context",
            st.session_state.combined_text[:FINAL_CONTEXT_LIMIT],
            height=360,
            label_visibility="collapsed"
        )


def render_email_form(default_recipient, default_goal, default_tone):
    if not st.session_state.profile:
        return

    st.subheader("Draft Email")

    with st.form("email_details_form"):
        col1, col2 = st.columns(2)

        with col1:
            recipient_name = st.text_input(
                "Recipient Name",
                value=default_recipient
            )
            recipient_email = st.text_input("Recipient Email")
            sender_name = st.text_input("Your Name")
            sender_role = st.text_input("Your Role / Affiliation")

        with col2:
            tone = st.selectbox(
                "Tone",
                TONES,
                index=TONES.index(default_tone)
            )
            relationship = st.selectbox(
                "Relationship",
                [
                    "Cold outreach",
                    "Warm intro",
                    "Follow-up",
                    "Reconnection"
                ]
            )
            call_to_action = st.text_input(
                "Call to Action",
                value="Would you be open to a short conversation?"
            )
            length = st.selectbox(
                "Email Length",
                [
                    "Short",
                    "Medium",
                    "Detailed"
                ]
            )

        outreach_goal = st.text_area(
            "Outreach Goal",
            value=default_goal
        )
        extra_context = st.text_area(
            "Additional Context",
            placeholder="Add any shared connection, project, timing, constraints, or details TOBI should know."
        )

        generate_clicked = st.form_submit_button("Generate Draft")

    if generate_clicked:
        if not outreach_goal:
            st.error("Please add an outreach goal before generating the email.")
            st.stop()

        details = {
            "recipient_name": recipient_name,
            "recipient_email": recipient_email,
            "sender_name": sender_name,
            "sender_role": sender_role,
            "tone": tone,
            "relationship": relationship,
            "call_to_action": call_to_action,
            "length": length,
            "outreach_goal": outreach_goal,
            "extra_context": extra_context
        }

        with st.spinner("Writing a contextual email draft..."):
            st.session_state.email_draft = generate_email_draft(
                st.session_state.profile,
                st.session_state.combined_text,
                details
            )
            st.session_state.gmail_result = None

    if st.session_state.email_draft:
        render_draft_preview(recipient_email, sender_name)


def render_draft_preview(default_to_email, default_sender_name):
    draft = st.session_state.email_draft

    if "error" in draft:
        st.error("The email draft could not be parsed as structured JSON.")
        st.text_area("Raw model output", draft.get("raw_output", ""), height=300)
        return

    subject = st.text_input("Subject", value=draft["subject"])
    body = st.text_area("Email Body", value=draft["body"], height=320)
    to_email = st.text_input("Save To Gmail Recipient", value=default_to_email)
    sender_name = st.text_input("Gmail Sender Name", value=default_sender_name)

    save_clicked = st.button("Save Gmail Draft")

    if save_clicked:
        try:
            with st.spinner("Saving draft to Gmail..."):
                st.session_state.gmail_result = create_gmail_draft(
                    to_email=to_email,
                    subject=subject,
                    body=body,
                    sender_name=sender_name
                )

            st.success("Draft saved to Gmail.")
            st.json(st.session_state.gmail_result)

        except Exception as exc:
            st.error(str(exc))


st.set_page_config(page_title="TOBI", layout="wide")
initialize_state()

st.title("TOBI")
st.subheader("Tonally Obliged, Bespoke Interface")

with st.sidebar:
    st.header("Extraction")

    recipient = st.text_input("Recipient Name")
    website = st.text_input("Website URL")

    goal = st.text_area("Outreach Goal")

    tone = st.selectbox("Tone", TONES)

    extract_clicked = st.button("Extract Intelligence")

if extract_clicked:
    if not website:
        st.error("Please enter a website URL.")
        st.stop()

    run_retrieval_pipeline(website)

render_extraction_results()
render_email_form(recipient, goal, tone)
