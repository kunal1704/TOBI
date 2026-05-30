import streamlit as st
import streamlit.components.v1 as components

from extraction.website_extractor import extract_website_text
from extraction.link_extractor import get_internal_links
from retrieval.link_filter import filter_relevant_links
from retrieval.semantic_ranker import rank_pages_semantically
from generation.profile_extractor import extract_recipient_profile
from generation.email_generator import generate_email_draft
from gmail_drafts import GMAIL_DRAFTS_URL, create_gmail_draft
from configs import *

"""
TOBI Main Application
---------------------

Primary Streamlit interface for the TOBI outreach workflow.

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
    "Research-Oriented",
    "Warm",
    "Professional",
    "Concise",
    "Intellectually Curious",
    "Friendly",
    "Confident",
    "Humble",
    "Direct",
    "Collaborative",
    "Mentor-Seeking",
    "Polished",
    "Enthusiastic",
    "Respectful",
]

INTENTS = [
    "Guidance or mentorship",
    "Research collaboration",
    "Project discussion",
    "Networking",
    "Academic inquiry",
    "Founder or investor outreach",
    "Interview or coffee chat",
    "Follow-up conversation",
]

LENGTHS = [
    "Short",
    "Medium",
    "Detailed",
]


def initialize_state():
    defaults = {
        "started": False,
        "profile": None,
        "combined_text": "",
        "ranked_pages": [],
        "email_draft": None,
        "gmail_result": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def apply_styles():
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        #MainMenu,
        footer,
        header {
            display: none !important;
        }

        .stApp {
            background: linear-gradient(180deg, #f7faf8 0%, #eef4f3 58%, #fff8ed 100%);
            color: #1f2933;
        }

        .block-container {
            max-width: 1180px;
            padding: 2rem 2rem 4rem;
        }

        .hero {
            min-height: 78vh;
            display: grid;
            align-items: center;
            gap: 2rem;
            padding: 2.2rem 0 1.2rem;
        }

        .eyebrow {
            color: #2f6f5f;
            font-size: 0.78rem;
            font-weight: 760;
            letter-spacing: 0;
            text-transform: uppercase;
            margin-bottom: 0.8rem;
        }

        .hero h1 {
            color: #17221f;
            font-size: 5rem;
            line-height: 0.96;
            letter-spacing: 0;
            margin: 0 0 1rem;
        }

        .hero-copy {
            max-width: 760px;
            color: #40514b;
            font-size: 1.14rem;
            line-height: 1.7;
            margin-bottom: 1.5rem;
        }

        .feature-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.8rem;
            margin: 1.5rem 0;
        }

        .feature-tile {
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid rgba(31, 41, 51, 0.08);
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 14px 34px rgba(30, 47, 43, 0.07);
        }

        .feature-tile strong {
            color: #17221f;
            display: block;
            font-size: 0.98rem;
            margin-bottom: 0.35rem;
        }

        .feature-tile span {
            color: #52635e;
            display: block;
            font-size: 0.9rem;
            line-height: 1.45;
        }

        .section-title {
            color: #17221f;
            font-size: 2.15rem;
            line-height: 1.12;
            margin: 0;
        }

        .section-copy {
            color: #52635e;
            font-size: 1rem;
            line-height: 1.65;
            max-width: 820px;
            margin: 0.55rem 0 1.4rem;
        }

        .workflow-heading {
            margin-bottom: 1.2rem;
        }

        .result-card {
            background: rgba(255, 255, 255, 0.76);
            border: 1px solid rgba(31, 41, 51, 0.10);
            border-radius: 8px;
            padding: 1.1rem;
            margin-top: 1rem;
        }

        .success-card {
            background: #f2fbf5;
            border: 1px solid #b9e4c6;
            border-radius: 8px;
            color: #1f5130;
            padding: 1rem 1.1rem;
            margin: 1rem 0;
        }

        .gmail-link {
            color: #245f4f !important;
            font-weight: 760;
            text-decoration: none !important;
            border-bottom: 1px solid rgba(36, 95, 79, 0.28);
        }

        div[data-testid="stForm"] {
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid rgba(31, 41, 51, 0.10);
            border-radius: 8px;
            padding: 1.4rem;
        }

        .stTextInput label,
        .stTextArea label,
        .stSelectbox label {
            color: #22312d !important;
            font-weight: 720 !important;
        }

        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div {
            background: rgba(255, 255, 255, 0.86) !important;
            border: 1px solid rgba(31, 41, 51, 0.14) !important;
            border-radius: 8px !important;
            color: #17221f !important;
            min-height: 44px;
        }

        .stButton > button,
        .stFormSubmitButton > button {
            background: #1f5c4d !important;
            border: 1px solid #1f5c4d !important;
            border-radius: 8px !important;
            color: white !important;
            font-weight: 760 !important;
            min-height: 46px;
            padding: 0 1.25rem !important;
        }

        .stButton > button:hover,
        .stFormSubmitButton > button:hover {
            background: #183f36 !important;
            border-color: #183f36 !important;
        }

        [data-testid="stExpander"] {
            background: rgba(255, 255, 255, 0.58);
            border: 1px solid rgba(31, 41, 51, 0.10);
            border-radius: 8px;
        }

        @media (max-width: 800px) {
            .block-container {
                padding: 1rem 1rem 3rem;
            }

            .hero h1 {
                font-size: 2.8rem;
            }

            .feature-row {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def run_retrieval_pipeline(website):
    homepage_text = extract_website_text(website)
    links = get_internal_links(website)
    filtered_links = filter_relevant_links(links)

    page_data = []

    if homepage_text:
        page_data.append({
            "url": website,
            "text": homepage_text,
        })

    for item in filtered_links[:MAX_PAGES]:
        extracted = extract_website_text(item["url"])

        if extracted:
            page_data.append({
                "url": item["url"],
                "text": extracted,
            })

    ranked_pages = rank_pages_semantically(page_data)
    combined_text = ""

    for page in ranked_pages[:SEMANTIC_TOP_K]:
        combined_text += f"\n\nPAGE: {page['url']}\n\n"
        combined_text += page["text"][:MAX_TEXT_PER_PAGE]

    profile = extract_recipient_profile(combined_text)

    st.session_state.profile = profile
    st.session_state.combined_text = combined_text
    st.session_state.ranked_pages = ranked_pages

    return {
        "homepage_found": bool(homepage_text),
        "links_found": len(links),
        "relevant_links": len(filtered_links),
        "pages_ranked": len(ranked_pages),
    }


def render_landing():
    st.markdown(
        """
        <div class="hero">
            <div>
                <div class="eyebrow">Research-led outreach, drafted into Gmail</div>
                <h1>TOBI</h1>
                <p class="hero-copy">
                    TOBI turns a recipient's public website into a grounded outreach draft.
                    It reads the profile, extracts useful context, asks for the missing human
                    details, and saves a Gmail draft you can review before sending.
                </p>
                <div class="feature-row">
                    <div class="feature-tile">
                        <strong>Extracts signal</strong>
                        <span>Finds relevant profile, research, project, and writing pages.</span>
                    </div>
                    <div class="feature-tile">
                        <strong>Writes with context</strong>
                        <span>Uses your goal, tone, background, and call to action.</span>
                    </div>
                    <div class="feature-tile">
                        <strong>Saves to Gmail</strong>
                        <span>Creates a draft so the final send stays under your control.</span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Try TOBI"):
        st.session_state.started = True
        st.rerun()


def render_workflow():
    st.markdown(
        """
        <div class="workflow-heading">
            <p class="eyebrow">TOBI Draft Studio</p>
            <h1 class="section-title">Create a contextual Gmail draft</h1>
            <p class="section-copy">
                Share the recipient's website and the outreach details TOBI cannot infer.
                One click extracts context, writes the draft, saves it to Gmail, and points
                you to your drafts folder for review.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("draft_form"):
        st.markdown("#### Recipient")
        col1, col2 = st.columns(2)

        with col1:
            recipient_name = st.text_input("Recipient Name")
            recipient_email = st.text_input("Recipient Email")

        with col2:
            website = st.text_input("Website URL")
            intent = st.selectbox("Outreach Intent", INTENTS)

        st.markdown("#### Sender")
        col3, col4 = st.columns(2)

        with col3:
            sender_name = st.text_input("Your Name")
            sender_affiliation = st.text_input("Affiliation (if any)")

        with col4:
            sender_background = st.text_area(
                "Relevant Background",
                placeholder="A short note about your work, project, research interest, or reason this outreach matters.",
                height=110,
            )

        st.markdown("#### Draft Preferences")
        col5, col6, col7 = st.columns(3)

        with col5:
            tone = st.selectbox("Tone", TONES)

        with col6:
            length = st.selectbox("Email Length", LENGTHS)

        with col7:
            call_to_action = st.text_input(
                "Call to Action",
                value="Would you be open to a short conversation?",
            )

        outreach_goal = st.text_area(
            "Outreach Goal",
            placeholder="What should this email accomplish?",
            height=110,
        )
        extra_context = st.text_area(
            "Additional Context",
            placeholder="Shared connections, timing, specific projects, constraints, or anything TOBI should mention.",
            height=100,
        )
        avoid = st.text_area(
            "Things to Avoid",
            placeholder="Optional: topics, claims, tone, or wording you do not want in the email.",
            height=85,
        )

        generate_clicked = st.form_submit_button("Generate Draft")

    if generate_clicked:
        required_fields = {
            "recipient name": recipient_name,
            "recipient email": recipient_email,
            "website URL": website,
            "outreach goal": outreach_goal,
            "your name": sender_name,
        }
        missing = [label for label, value in required_fields.items() if not value.strip()]

        if missing:
            st.error(f"Please add {', '.join(missing)} before generating the draft.")
            st.stop()

        details = {
            "recipient_name": recipient_name,
            "recipient_email": recipient_email,
            "sender_name": sender_name,
            "sender_affiliation": sender_affiliation,
            "sender_background": sender_background,
            "tone": tone,
            "intent": intent,
            "call_to_action": call_to_action,
            "length": length,
            "outreach_goal": outreach_goal,
            "extra_context": extra_context,
            "things_to_avoid": avoid,
        }

        with st.status("Creating your Gmail draft...", expanded=True) as status:
            st.write("Reading the recipient website.")
            extraction_summary = run_retrieval_pipeline(website)

            st.write("Generating a grounded email draft.")
            draft = generate_email_draft(
                st.session_state.profile,
                st.session_state.combined_text,
                details,
            )

            if "error" in draft:
                status.update(
                    label="TOBI could not format the generated draft.",
                    state="error",
                    expanded=True,
                )
                st.session_state.email_draft = draft
                st.stop()

            st.session_state.email_draft = draft

            st.write("Saving the draft to Gmail.")
            gmail_result = create_gmail_draft(
                to_email=recipient_email,
                subject=draft["subject"],
                body=draft["body"],
            )
            st.session_state.gmail_result = gmail_result

            status.update(
                label="Draft saved to Gmail.",
                state="complete",
                expanded=False,
            )

        render_success(extraction_summary)

    elif st.session_state.email_draft:
        render_success()


def render_success(extraction_summary=None):
    draft = st.session_state.email_draft
    gmail_url = st.session_state.gmail_result.get("gmail_url", GMAIL_DRAFTS_URL)

    st.markdown(
        f"""
        <div class="success-card">
            <strong>Your draft is saved in Gmail.</strong><br>
            TOBI has prepared the email and placed it in your Gmail drafts.
            <a class="gmail-link" href="{gmail_url}" target="_blank" rel="noopener">
                Open Gmail drafts
            </a>
            to review it and click send when ready.
        </div>
        """,
        unsafe_allow_html=True,
    )

    components.html(
        f"""
        <script>
        setTimeout(() => {{
            window.open("{gmail_url}", "_blank", "noopener,noreferrer");
        }}, 1800);
        </script>
        """,
        height=0,
    )

    st.markdown('<div class="result-card">', unsafe_allow_html=True)
    st.markdown("#### Draft Preview")
    st.text_input("Subject", value=draft.get("subject", ""), disabled=True)
    st.text_area("Email Body", value=draft.get("body", ""), height=280, disabled=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if extraction_summary:
        col1, col2, col3 = st.columns(3)
        col1.metric("Links Found", extraction_summary["links_found"])
        col2.metric("Relevant Links", extraction_summary["relevant_links"])
        col3.metric("Pages Ranked", extraction_summary["pages_ranked"])

    with st.expander("Recipient intelligence"):
        st.json(st.session_state.profile)

    with st.expander("Source context"):
        st.text_area(
            "Combined extracted context",
            st.session_state.combined_text[:FINAL_CONTEXT_LIMIT],
            height=320,
            label_visibility="collapsed",
        )


st.set_page_config(page_title="TOBI", layout="wide", initial_sidebar_state="collapsed")
initialize_state()
apply_styles()

if st.session_state.started:
    render_workflow()
else:
    render_landing()
