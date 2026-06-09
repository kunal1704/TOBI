from datetime import datetime
from html import escape
from textwrap import dedent

import streamlit as st
import streamlit.components.v1 as components

from auth_storage import (
    clear_remembered_user,
    create_user,
    get_remembered_user,
    get_user,
    remember_user,
    save_user_profile,
    verify_user,
)
from configs import *
from document_extractors import extract_uploaded_file
from extraction.link_extractor import get_internal_links
from extraction.website_extractor import extract_website_text
from generation.email_generator import generate_email_draft
from generation.profile_extractor import extract_recipient_profile
from generation.user_profile_builder import build_user_profile
from gmail_drafts import GMAIL_DRAFTS_URL, create_gmail_draft
from retrieval.link_filter import filter_relevant_links
from retrieval.semantic_ranker import rank_pages_semantically


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
        "profile": None,
        "combined_text": "",
        "ranked_pages": [],
        "email_draft": None,
        "gmail_result": None,
        "outreach_history": [],
        "workflow_status": {},
        "current_user": None,
        "editing_sender_profile": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if st.session_state.current_user is None:
        remembered_user = get_remembered_user()

        if remembered_user:
            st.session_state.current_user = remembered_user


def is_try_mode():
    return st.query_params.get("mode") == "try"


def current_mode():
    return st.query_params.get("mode", "landing")


def is_profile_mode():
    return current_mode() == "profile"


def is_auth_mode():
    return current_mode() == "auth"


def is_logout_mode():
    return current_mode() == "logout"


def get_current_profile():
    user = st.session_state.get("current_user") or {}
    return user.get("profile") or {}


def get_current_user_email():
    user = st.session_state.get("current_user") or {}
    return user.get("email", "")


def as_lines(value):
    if isinstance(value, list):
        return "\n".join(str(item) for item in value if item)

    if value:
        return str(value)

    return ""


def lines_to_list(value):
    return [line.strip() for line in value.splitlines() if line.strip()]


def build_sender_context(profile):
    parts = []

    simple_fields = [
        ("Name", profile.get("full_name")),
        ("Affiliation", profile.get("affiliation")),
        ("Location", profile.get("location")),
        ("Summary", profile.get("summary")),
        ("Current focus", profile.get("current_focus")),
        ("Writing style", profile.get("writing_style")),
        ("Availability", profile.get("availability")),
        ("Signature", profile.get("signature")),
    ]

    for label, value in simple_fields:
        if value:
            parts.append(f"{label}: {value}")

    list_fields = [
        ("Expertise", profile.get("expertise")),
        ("Projects", profile.get("projects")),
        ("Achievements", profile.get("achievements")),
        ("Education", profile.get("education")),
        ("Collaboration interests", profile.get("collaboration_interests")),
        ("Target audience", profile.get("target_audience")),
        ("Outreach strengths", profile.get("outreach_strengths")),
    ]

    for label, values in list_fields:
        if isinstance(values, list) and values:
            parts.append(f"{label}: {', '.join(str(value) for value in values if value)}")

    return "\n".join(parts)


def render_html(markup):
    try:
        st.html(markup)
    except Exception:
        st.markdown(markup, unsafe_allow_html=True)


def get_initials(name):
    parts = [part for part in name.strip().split() if part]

    if not parts:
        return "TO"

    return "".join(part[0] for part in parts[:2]).upper()


def add_outreach_record(details, draft, extraction_summary, gmail_result):
    record = {
        "recipient_name": details["recipient_name"],
        "recipient_email": details["recipient_email"],
        "website": details["website"],
        "intent": details["intent"],
        "tone": details["tone"],
        "goal": details["outreach_goal"],
        "subject": draft.get("subject", ""),
        "gmail_url": gmail_result.get("gmail_url", GMAIL_DRAFTS_URL),
        "links_found": extraction_summary["links_found"],
        "relevant_links": extraction_summary["relevant_links"],
        "pages_ranked": extraction_summary["pages_ranked"],
        "created_at": datetime.now().strftime("%d %b, %I:%M %p"),
    }

    st.session_state.outreach_history = [
        record,
        *st.session_state.outreach_history[:11],
    ]


def render_outreach_board(records=None, sample=False):
    board_records = records or []

    if sample:
        board_records = [
            {
                "recipient_name": "Sarah Kim",
                "recipient_email": "sarah@infralabs.ai",
                "website": "sarahkim.dev",
                "intent": "Research collaboration",
                "tone": "Direct",
                "goal": "Ask about inference optimization lessons for edge LLM deployment.",
                "subject": "Edge inference notes and possible overlap",
                "gmail_url": "#",
                "links_found": 14,
                "relevant_links": 5,
                "pages_ranked": 4,
                "created_at": "Preview",
            },
            {
                "recipient_name": "Prof. Aditya Rao",
                "recipient_email": "aditya@lab.edu",
                "website": "rai-lab.edu",
                "intent": "Guidance or mentorship",
                "tone": "Research-Oriented",
                "goal": "Request focused guidance on multi-modal RAG research directions.",
                "subject": "Question on your multi-modal RAG work",
                "gmail_url": "#",
                "links_found": 21,
                "relevant_links": 7,
                "pages_ranked": 5,
                "created_at": "Preview",
            },
            {
                "recipient_name": "Maya Chen",
                "recipient_email": "maya@northstar.vc",
                "website": "northstar.vc",
                "intent": "Founder or investor outreach",
                "tone": "Polished",
                "goal": "Reference thesis fit and request feedback on TOBI's early direction.",
                "subject": "TOBI and your AI workflow thesis",
                "gmail_url": "#",
                "links_found": 11,
                "relevant_links": 4,
                "pages_ranked": 3,
                "created_at": "Preview",
            },
        ]

    if not board_records:
        render_html(
            """
            <div class="empty-board">
                <p class="section-label">Outreach Board</p>
                <h2 class="section-headline">Generated drafts will appear here.</h2>
                <p class="section-sub">Once you create Gmail drafts, TOBI shows session placards with recipient, intent, subject, retrieval depth, and review link.</p>
            </div>
            """
        )
        return

    cards = []

    for record in board_records:
        initials = escape(get_initials(record["recipient_name"]))
        name = escape(record["recipient_name"])
        email = escape(record["recipient_email"])
        website = escape(record["website"])
        intent = escape(record["intent"])
        tone = escape(record["tone"])
        goal = escape(record["goal"])
        subject = escape(record["subject"])
        created_at = escape(record["created_at"])
        gmail_url = escape(record["gmail_url"])
        links_found = record["links_found"]
        relevant_links = record["relevant_links"]
        pages_ranked = record["pages_ranked"]

        cards.append(
            dedent(
        f"""
        <article class="outreach-card">
                <div class="outreach-card-top">
                    <div class="profile-avatar compact">{initials}</div>
                    <div>
                        <div class="profile-name">{name}</div>
                        <div class="profile-role">{email}</div>
                    </div>
                    <span class="status-pill">Gmail draft</span>
                </div>
                <div class="outreach-subject">{subject}</div>
                <div class="outreach-goal">{goal}</div>
                <div class="outreach-meta-grid">
                    <div><span>Intent</span>{intent}</div>
                    <div><span>Tone</span>{tone}</div>
                    <div><span>Source</span>{website}</div>
                    <div><span>Created</span>{created_at}</div>
                </div>
                <div class="retrieval-strip">
                    <span>{links_found} links</span>
                    <span>{relevant_links} relevant</span>
                    <span>{pages_ranked} ranked</span>
                </div>
                <a class="gmail-link" href="{gmail_url}" target="_blank" rel="noopener">Open Gmail draft</a>
        </article>
            """
            )
        )

    cards_html = "\n".join(cards)

    render_html(
        f"""
        <div class="outreach-board fade-section">
            <div class="board-heading">
                <div>
                    <p class="section-label">Outreach Board</p>
                    <h2 class="section-headline">Preview every person you have drafted for.</h2>
                </div>
                <p class="section-sub">
                    Placards summarize who TOBI contacted, why, what it found, and where to review the Gmail draft.
                </p>
            </div>
            <div class="outreach-grid">
                {cards_html}
            </div>
        </div>
        """
    )


def apply_styles():
    render_html(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Sora:wght@300;400;500;600&display=swap');

        :root {
            --bg: #080b0f;
            --bg-card: #0d1117;
            --bg-subtle: #111621;
            --border: rgba(255,255,255,0.07);
            --border-bright: rgba(255,255,255,0.13);
            --text-primary: #eef1f7;
            --text-secondary: #8a93a6;
            --text-muted: #4a5268;
            --accent: #c8f542;
            --accent-dim: rgba(200,245,66,0.12);
            --violet: #9b8cff;
            --cyan: #54d6ff;
            --rose: #ff7ab6;
            --blue: #7dc4e4;
            --amber: #e5a445;
            --font-sans: 'Sora', sans-serif;
            --font-mono: 'DM Mono', monospace;
        }

        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        [data-testid="stHeader"],
        #MainMenu,
        footer {
            display: none !important;
        }

        html {
            scroll-behavior: smooth;
        }

        .stApp {
            background:
                radial-gradient(circle at 15% 20%, rgba(84,214,255,0.12), transparent 35%),
                radial-gradient(circle at 85% 15%, rgba(155,140,255,0.12), transparent 35%),
                radial-gradient(circle at 30% 90%, rgba(229,164,69,0.10), transparent 35%),
                linear-gradient(180deg, #070b10 0%, #090d14 100%);
            min-height: 100vh;
            color: var(--text-primary);
            font-family: var(--font-sans);
        }

        .stApp::before {
            content: '';
            position: fixed;
            inset: 0;
            background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
            pointer-events: none;
            opacity: 0.38;
            z-index: 0;
        }

        .block-container {
            max-width: 1100px;
            padding: 0 2rem 5rem;
            position: relative;
            z-index: 1;
        }

        h1, h2, h3, p {
            font-family: var(--font-sans);
        }

        h1, h2, h3 {
            color: var(--text-primary) !important;
            font-weight: 300 !important;
            letter-spacing: -0.02em;
        }

        p {
            color: var(--text-secondary);
            font-weight: 300;
        }

        .tobi-nav {
            position: sticky;
            top: 0;
            z-index: 100;
            display: flex;
            align-items: center;
            justify-content: space-between;
            height: 58px;
            margin: 0 -2rem;
            padding: 0 2rem;
            border-bottom: 1px solid var(--border);
            background: rgba(8,11,15,0.80);
            backdrop-filter: blur(18px);
        }

        .nav-logo {
            color: var(--accent);
            font-family: var(--font-mono);
            font-size: 18px;
            font-weight: 500;
            letter-spacing: 0.08em;
            text-decoration: none;
        }

        .nav-tag {
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: 11px;
            letter-spacing: 0.06em;
        }

        .nav-actions {
            align-items: center;
            display: flex;
            gap: 0.8rem;
        }

        .nav-link {
            color: var(--text-secondary) !important;
            font-family: var(--font-mono);
            font-size: 11px;
            letter-spacing: 0.06em;
            text-decoration: none !important;
            text-transform: uppercase;
        }

        .nav-link:hover {
            color: var(--accent) !important;
        }

        .btn-primary {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: var(--accent);
            border-radius: 6px;
            color: #0a0d07 !important;
            font-family: var(--font-sans);
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 0.03em;
            padding: 9px 20px;
            text-decoration: none !important;
            transition: transform 0.15s ease, opacity 0.15s ease;
        }

        .btn-primary:hover {
            opacity: 0.92;
            transform: translateY(-1px);
        }

        .hero {
            padding: 5.5rem 0 4rem;
            position: relative;
            transition: opacity 0.35s ease;
            overflow: visible;
        }


        .hero-inner {
            position: relative;
            z-index: 1;
            max-width: 900px;
        }

        .eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            color: var(--accent);
            font-family: var(--font-mono);
            font-size: 11px;
            letter-spacing: 0.12em;
            margin-bottom: 1.8rem;
            text-transform: uppercase;
        }

        .eyebrow-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--accent);
            animation: pulse 2.4s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.8); }
        }

        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .fade-section {
            animation: fadeInUp 0.6s ease forwards;
        }

        .hero-headline {
            color: var(--text-primary);
            font-size: 4.0rem;
            font-weight: 300;
            line-height: 1.2;
            letter-spacing: -0.025em;
            margin: 0 0 1.5rem;
            max-width: 720px;
        }

        .hero-headline em {
            color: var(--accent);
            font-style: normal;
        }

        .hero-sub {
            color: var(--text-secondary);
            font-size: 15px;
            font-weight: 300;
            line-height: 1.75;
            max-width: 480px;
            margin: 0 0 2.4rem;
        }

        .hero-actions {
            display: flex;
            align-items: center;
            gap: 20px;
            margin-top: 2rem;
        }

        .hero-stat {
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: 12px;
        }

        .hero-layout {
            display: flex;
            align-items: center;
            gap: 4rem;
            position: relative;
            z-index: 1;
        }

        .hero-preview {
            background: rgba(13, 17, 23, 0.6);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            min-width: 280px;
            flex-shrink: 0;
            position: relative;
            z-index: 1;
            transition: border-color 0.3s ease, box-shadow 0.3s ease;
        }

        .hero-preview:hover {
            border-color: var(--border-bright);
            box-shadow: 0 0 30px rgba(200,245,66,0.03);
        }

        .hero-preview::before {
            content: '';
            position: absolute;
            inset: -30px;
            border-radius: 42px;
            background: radial-gradient(ellipse 60% 50% at 50% 40%, rgba(200,245,66,0.04), rgba(84,214,255,0.02), transparent 70%);
            filter: blur(30px);
            z-index: -1;
            pointer-events: none;
        }

        .preview-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.4rem 0;
        }

        .preview-label {
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: 11px;
            letter-spacing: 0.04em;
        }

        .preview-value {
            color: var(--text-primary);
            font-family: var(--font-mono);
            font-size: 12px;
        }

        .preview-divider {
            height: 1px;
            background: var(--border);
            margin: 0.6rem 0;
        }

        .preview-ok {
            color: var(--accent);
        }

        .runtime-card {
            background: rgba(13, 17, 23, 0.6);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            transition: all .25s ease;
        }

        .runtime-card:hover {
            transform: translateY(-6px);
            border-color: var(--border-bright);
        }

        .workspace-card {
            background: rgba(13, 17, 23, 0.6);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            transition: all .25s ease;
        }

        .workspace-card:hover {
            transform: translateY(-6px);
            border-color: var(--border-bright);
        }

        .workspace-card-body {
            padding: 1.5rem;
        }

        .workspace-stat-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            padding: 0.75rem 0;
        }

        .workspace-stat-item {
            padding: 0.75rem 0.5rem;
            text-align: center;
        }

        .workspace-stat-item + .workspace-stat-item {
            border-left: 1px solid var(--border);
        }

        .workspace-stat-num {
            color: var(--text-primary);
            font-family: var(--font-sans);
            font-size: 1.6rem;
            font-weight: 300;
            letter-spacing: -0.03em;
        }

        .workspace-stat-num span {
            color: var(--accent);
        }

        .workspace-stat-label {
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: 11px;
            letter-spacing: 0.08em;
            margin-top: 4px;
        }

        .runtime-card-header {
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: 11px;
            letter-spacing: 0.08em;
            margin-bottom: 1rem;
            text-transform: uppercase;
        }

        .runtime-step {
            color: var(--text-secondary);
            font-family: var(--font-mono);
            font-size: 12px;
            padding: 0.35rem 0;
            line-height: 1.6;
        }

        .runtime-check {
            color: var(--accent);
            margin-right: 0.6rem;
        }

        .runtime-pending {
            color: var(--text-muted);
            margin-right: 0.6rem;
        }

        .runtime-running {
            color: var(--accent);
            margin-right: 0.6rem;
        }

        .runtime-failed {
            color: var(--rose);
            margin-right: 0.6rem;
        }

        .workflow-steps {
            display: flex;
            flex-direction: column;
            gap: 0;
            margin-top: 3rem;
        }

        .workflow-step {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 0.5rem 0;
            position: relative;
        }

        .workflow-step:not(:last-child) {
            padding-bottom: 1.25rem;
        }

        .workflow-step:not(:last-child)::after {
            content: '';
            position: absolute;
            left: 23px;
            top: 54px;
            bottom: 0;
            width: 1px;
            background: linear-gradient(180deg, var(--border-bright), transparent);
        }

        .workflow-marker {
            width: 46px;
            height: 46px;
            border-radius: 50%;
            border: 1px solid var(--border-bright);
            background: var(--bg-card);
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            position: relative;
            z-index: 1;
            transition: border-color 0.2s;
        }

        .workflow-marker span {
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: 11px;
            letter-spacing: 0.04em;
        }

        .workflow-step:hover .workflow-marker {
            border-color: var(--accent);
        }

        .workflow-step:hover .workflow-marker span {
            color: var(--accent);
        }

        .workflow-label {
            color: var(--text-primary);
            font-size: 14px;
            font-weight: 400;
        }

        .divider {
            background: linear-gradient(90deg, transparent, var(--border-bright), transparent);
            height: 1px;
            margin: 0;
        }

        .section {
            padding: 6rem 0;
        }

        .section.accented,
        .draft-header {
            position: relative;
            padding: 4.5rem 0;
            transition: opacity 0.35s ease;
        }

        .section-label {
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: 11px;
            letter-spacing: 0.14em;
            margin-bottom: 1rem;
            text-transform: uppercase;
        }

        .section-headline {
            color: var(--text-primary);
            font-size: 2.4rem;
            font-weight: 300;
            line-height: 1.2;
            margin: 0 0 1rem;
        }

        .section-sub {
            color: var(--text-secondary);
            font-size: 15px;
            font-weight: 300;
            line-height: 1.75;
            max-width: 520px;
            margin-bottom: 0;
        }

        .email-demo,
        .profile-card,
        .terminal,
        .draft-panel,
        .success-panel {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
        }

        .profile-card {
            transition: all .25s ease;
        }

        .profile-card:hover {
            transform: translateY(-6px);
            border-color: var(--border-bright);
        }

        .email-demo {
            margin-top: 3rem;
            transition: all .25s ease;
        }

        .email-demo:hover {
            transform: translateY(-6px);
            border-color: var(--border-bright);
        }

        .window-bar,
        .terminal-bar {
            align-items: center;
            border-bottom: 1px solid var(--border);
            display: flex;
            gap: 8px;
            padding: 12px 16px;
        }

        .dot {
            border-radius: 50%;
            height: 10px;
            width: 10px;
        }

        .dot-r { background: #ff5f57; }
        .dot-y { background: #febc2e; }
        .dot-g { background: #28c840; }

        .window-title {
            color: var(--text-muted);
            flex: 1;
            font-family: var(--font-mono);
            font-size: 11px;
            text-align: center;
        }

        .email-body,
        .terminal-body,
        .profile-card,
        .draft-panel,
        .success-panel {
            padding: 2rem;
        }

        .email-field {
            display: flex;
            font-size: 12px;
            gap: 12px;
            margin-bottom: 6px;
        }

        .email-field-label {
            color: var(--text-muted);
            font-family: var(--font-mono);
            min-width: 40px;
        }

        .email-field-value,
        .email-content {
            color: var(--text-secondary);
        }

        .email-subject {
            border-bottom: 1px solid var(--border);
            color: var(--text-primary);
            font-size: 14px;
            font-weight: 500;
            margin: 1rem 0 1.2rem;
            padding-bottom: 1rem;
        }

        .email-content {
            font-size: 14px;
            line-height: 1.9;
        }

        .highlight {
            background: linear-gradient(90deg, rgba(200,245,66,0.16), rgba(84,214,255,0.10));
            border-radius: 3px;
            color: var(--accent);
            font-family: var(--font-mono);
            font-size: 12px;
            padding: 1px 5px;
        }

        .email-tag,
        .tech-pill,
        .profile-source {
            background: rgba(255,255,255,0.03);
            border: 1px solid var(--border);
            border-radius: 4px;
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: 10px;
            letter-spacing: 0.06em;
            padding: 3px 8px;
        }

        .split {
            align-items: center;
            display: grid;
            gap: 5rem;
            grid-template-columns: 1fr 1fr;
        }

        .split.reverse {
            direction: rtl;
        }

        .split.reverse > * {
            direction: ltr;
        }

        .tech-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 1.5rem;
        }

        .profile-card-header {
            align-items: flex-start;
            border-bottom: 1px solid var(--border);
            display: flex;
            gap: 16px;
            margin-bottom: 1.5rem;
            padding-bottom: 1.5rem;
        }

        .profile-avatar {
            align-items: center;
            background: linear-gradient(135deg, #151d2a, #1e3145);
            border: 1px solid var(--border-bright);
            border-radius: 10px;
            color: var(--text-secondary);
            display: flex;
            flex-shrink: 0;
            font-family: var(--font-mono);
            font-size: 14px;
            height: 48px;
            justify-content: center;
            width: 48px;
        }

        .profile-name {
            color: var(--text-primary);
            font-size: 15px;
            font-weight: 500;
        }

        .profile-role {
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: 12px;
        }

        .profile-source {
            margin-left: auto;
        }

        .insight-row {
            align-items: flex-start;
            display: flex;
            gap: 10px;
            margin-bottom: 12px;
        }

        .insight-key {
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: 10px;
            letter-spacing: 0.06em;
            min-width: 90px;
            padding-top: 2px;
        }

        .insight-val {
            color: var(--text-secondary);
            font-size: 13px;
            line-height: 1.6;
        }

        .terminal {
            background: #050709;
            transition: all .25s ease;
        }

        .terminal:hover {
            transform: translateY(-6px);
            border-color: var(--border-bright);
        }

        .outreach-board {
            padding: 6rem 0;
        }

        .board-heading {
            align-items: end;
            display: grid;
            gap: 1.5rem;
            grid-template-columns: 1.1fr 0.9fr;
            margin-bottom: 2rem;
        }

        .outreach-grid {
            display: grid;
            gap: 1rem;
            grid-template-columns: repeat(3, minmax(0, 1fr));
        }

        .outreach-card {
            backdrop-filter: blur(20px);
            background: linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 14px;
            min-height: 360px;
            padding: 1.25rem;
            position: relative;
            overflow: hidden;
            transition: transform .2s ease, border-color .2s ease;
        }

        .outreach-card:hover {
            transform: translateY(-6px);
            border-color: var(--border-bright);
        }

        .outreach-card::before {
            content: '';
            position: absolute;
            inset: 0;
            background: linear-gradient(135deg, rgba(200,245,66,0.12), transparent 34%, rgba(84,214,255,0.08));
            opacity: 0.55;
            pointer-events: none;
        }

        .outreach-card > * {
            position: relative;
            z-index: 1;
        }

        .outreach-card-top {
            align-items: center;
            display: flex;
            gap: 12px;
            margin-bottom: 1.2rem;
        }

        .profile-avatar.compact {
            border-radius: 12px;
            height: 44px;
            width: 44px;
        }

        .status-pill {
            background: rgba(200,245,66,0.10);
            border: 1px solid rgba(200,245,66,0.22);
            border-radius: 999px;
            color: var(--accent);
            font-family: var(--font-mono);
            font-size: 10px;
            margin-left: auto;
            padding: 4px 8px;
            white-space: nowrap;
        }

        .outreach-subject {
            color: var(--text-primary);
            font-size: 16px;
            font-weight: 500;
            line-height: 1.45;
            margin-bottom: 0.8rem;
        }

        .outreach-goal {
            color: var(--text-secondary);
            font-size: 13px;
            line-height: 1.65;
            min-height: 64px;
            margin-bottom: 1.2rem;
        }

        .outreach-meta-grid {
            display: grid;
            gap: 0.7rem;
            grid-template-columns: 1fr 1fr;
            margin-bottom: 1rem;
        }

        .outreach-meta-grid div {
            color: var(--text-secondary);
            font-size: 12px;
            line-height: 1.35;
        }

        .outreach-meta-grid span {
            color: var(--text-muted);
            display: block;
            font-family: var(--font-mono);
            font-size: 9px;
            letter-spacing: 0.08em;
            margin-bottom: 3px;
            text-transform: uppercase;
        }

        .retrieval-strip {
            border-top: 1px solid var(--border);
            border-bottom: 1px solid var(--border);
            color: var(--text-muted);
            display: flex;
            font-family: var(--font-mono);
            font-size: 10px;
            justify-content: space-between;
            margin: 1rem 0;
            padding: 0.7rem 0;
        }

        .empty-board {
            background: var(--bg-card);
            border: 1px dashed var(--border-bright);
            border-radius: 14px;
            margin: 2rem 0;
            padding: 2rem;
        }

        .progress-panel {
            background:
                linear-gradient(135deg, rgba(200,245,66,0.09), transparent 42%),
                linear-gradient(245deg, rgba(84,214,255,0.09), transparent 45%),
                var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 14px;
            margin: 1.5rem 0;
            overflow: hidden;
            padding: 1.4rem;
            position: relative;
        }

        .progress-panel::before {
            content: '';
            position: absolute;
            top: 0;
            left: -35%;
            width: 35%;
            height: 2px;
            background: linear-gradient(90deg, transparent, var(--accent), var(--cyan), transparent);
            animation: scanline 1.4s ease-in-out infinite;
        }

        @keyframes scanline {
            0% { left: -35%; }
            100% { left: 100%; }
        }

        .progress-title {
            align-items: center;
            color: var(--text-primary);
            display: flex;
            font-size: 16px;
            gap: 10px;
            margin-bottom: 1.2rem;
        }

        .progress-ring {
            border: 2px solid rgba(255,255,255,0.10);
            border-top-color: var(--accent);
            border-right-color: var(--cyan);
            border-radius: 50%;
            height: 20px;
            width: 20px;
            animation: spin 0.9s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .progress-steps {
            display: grid;
            gap: 0.75rem;
            grid-template-columns: repeat(4, minmax(0, 1fr));
        }

        .progress-step {
            background: rgba(5,7,9,0.62);
            border: 1px solid var(--border);
            border-radius: 10px;
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: 10px;
            min-height: 74px;
            padding: 0.8rem;
            position: relative;
        }

        .progress-step.active {
            border-color: rgba(200,245,66,0.45);
            color: var(--accent);
        }

        .progress-step.done {
            border-color: rgba(84,214,255,0.30);
            color: var(--blue);
        }

        .progress-step strong {
            color: var(--text-primary);
            display: block;
            font-family: var(--font-sans);
            font-size: 13px;
            font-weight: 500;
            letter-spacing: 0;
            margin: 0.35rem 0 0.2rem;
        }

        .progress-step span {
            color: var(--text-secondary);
            display: block;
            font-family: var(--font-sans);
            font-size: 12px;
            line-height: 1.35;
        }

        .progress-step.active strong,
        .progress-step.done strong {
            color: inherit;
        }

        .terminal-body {
            font-family: var(--font-mono);
            font-size: 12px;
            line-height: 1.9;
        }

        .t-dim { color: var(--text-muted); }
        .t-green { color: var(--accent); }
        .t-blue { color: var(--blue); }
        .t-orange { color: var(--amber); }
        .t-white { color: var(--text-primary); }

        .usecase-grid {
            border: 1px solid var(--border);
            border-radius: 12px;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            margin-top: 3rem;
            overflow: hidden;
        }

        .usecase-card {
            background: var(--bg-card);
            border-bottom: 1px solid var(--border);
            border-right: 1px solid var(--border);
            padding: 2rem;
            transition: all .25s ease;
        }

        .usecase-card:hover {
            background: var(--bg-subtle);
            transform: translateY(-6px);
            border-color: var(--border-bright);
        }

        .usecase-num {
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: 10px;
            letter-spacing: 0.08em;
            margin-bottom: 1.2rem;
        }

        .usecase-title {
            color: var(--text-primary);
            font-size: 15px;
            font-weight: 500;
            margin-bottom: 0.6rem;
        }

        .usecase-desc {
            color: var(--text-muted);
            font-size: 13px;
            font-weight: 300;
            line-height: 1.7;
        }

        .stat-row {
            border: 1px solid var(--border);
            border-radius: 10px;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            margin-top: 3rem;
            overflow: hidden;
        }

        .stat-item {
            background: var(--bg-card);
            border-right: 1px solid var(--border);
            padding: 2rem 1.5rem;
            text-align: center;
        }

        .stat-item:last-child {
            border-right: 0;
        }

        .stat-num {
            color: var(--text-primary);
            font-family: var(--font-sans);
            font-size: 2.4rem;
            font-weight: 300;
            letter-spacing: -0.03em;
        }

        .stat-num span {
            color: var(--accent);
        }

        .stat-label {
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: 11px;
            letter-spacing: 0.08em;
            margin-top: 4px;
        }

        .tobi-footer {
            align-items: center;
            border-top: 1px solid var(--border);
            color: var(--text-muted);
            display: flex;
            font-family: var(--font-mono);
            font-size: 11px;
            justify-content: space-between;
            padding: 3rem 0;
        }

        .draft-header {
            padding: 1.5rem 0 0.5rem;
        }

        .workflow-headline {
            font-size: 3rem;
        }

        .draft-panel {
            margin-top: 1.5rem;
        }

        .auth-shell,
        .profile-shell {
            padding: 5rem 0 3rem;
        }

        .profile-summary-card {
            background:
                linear-gradient(145deg, rgba(200,245,66,0.10), transparent 42%),
                linear-gradient(245deg, rgba(84,214,255,0.08), transparent 45%),
                var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1.5rem;
        }

        .profile-kv {
            border-bottom: 1px solid var(--border);
            display: grid;
            gap: 1rem;
            grid-template-columns: 140px 1fr;
            padding: 0.8rem 0;
        }

        .profile-kv:last-child {
            border-bottom: 0;
        }

        .profile-kv span {
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: 10px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .profile-kv strong {
            color: var(--text-primary);
            font-size: 13px;
            font-weight: 500;
        }

        div[data-testid="stForm"] {
            background: rgba(13,17,23,0.45);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1.25rem;
            backdrop-filter: blur(10px);
        }

        .stTextInput label,
        .stTextArea label,
        .stSelectbox label {
            color: var(--text-primary) !important;
            font-family: var(--font-mono) !important;
            font-size: 11px !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase;
        }

        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div {
            background: rgba(255,255,255,0.02) !important;
            border: 1px solid var(--border-bright) !important;
            border-radius: 8px !important;
            color: var(--text-primary) !important;
            font-family: var(--font-sans) !important;
            min-height: 44px;
        }

        .stTextArea textarea {
            line-height: 1.6;
        }

        .stSelectbox svg {
            color: var(--text-secondary) !important;
        }

        .stFormSubmitButton > button {
            background: var(--accent) !important;
            border: 0 !important;
            border-radius: 6px !important;
            color: #0a0d07 !important;
            font-family: var(--font-sans) !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            min-height: 44px;
            padding: 0 20px !important;
            transition: opacity 0.15s ease, transform 0.15s ease;
        }

        .stFormSubmitButton > button:hover {
            opacity: 0.92;
            transform: translateY(-1px);
        }

        .success-panel {
            margin-top: 2rem;
        }

        .gmail-link {
            color: var(--accent) !important;
            font-family: var(--font-mono);
            text-decoration: none !important;
        }

        [data-testid="stMetric"] {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 1rem;
        }

        [data-testid="stMetricLabel"] p {
            color: var(--text-muted) !important;
            font-family: var(--font-mono) !important;
            font-size: 10px !important;
        }

        [data-testid="stMetricValue"] {
            color: var(--accent) !important;
        }

        [data-testid="stExpander"] {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
        }

        @media (max-width: 768px) {
            .block-container {
                padding: 0 1rem 4rem;
            }

            .tobi-nav {
                margin: 0 -1rem;
                padding: 0 1rem;
            }

            .nav-tag {
                display: none;
            }

            .hero-headline {
                font-size: 3rem;
            }

            .split,
            .usecase-grid,
            .stat-row,
            .outreach-grid,
            .board-heading,
            .progress-steps {
                display: grid;
                grid-template-columns: 1fr;
                gap: 1rem;
            }

            .split.reverse {
                direction: ltr;
            }

            .usecase-card,
            .stat-item {
                border-right: 0;
            }

            .tobi-footer {
                align-items: flex-start;
                flex-direction: column;
                gap: 0.6rem;
            }
        }
        </style>
        """
    )


def render_nav(show_try=True):
    user = st.session_state.get("current_user")
    profile_label = "Profile" if user else "Login"
    profile_href = "?mode=profile" if user else "?mode=auth"
    auth_action = '<a href="?mode=logout" class="nav-link">Sign out</a>' if user else ""
    action = (
        """
        <a href="?mode=try" class="btn-primary">
            Try now
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M2.5 6H9.5M9.5 6L7 3.5M9.5 6L7 8.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        </a>
        """
        if show_try
        else "<span></span>"
    )

    render_html(
        f"""
        <div class="tobi-nav">
            <a href="?" class="nav-logo">TOBI</a>
            <span class="nav-tag">AI outreach engine - v0.1</span>
            <div class="nav-actions">
                <a href="{profile_href}" class="nav-link">{profile_label}</a>
                {auth_action}
                {action}
            </div>
        </div>
        """
    )


def render_landing():
    render_nav(show_try=True)

    draft = st.session_state.get("email_draft")
    latest = st.session_state.get("outreach_history", [])
    has_draft = draft and latest
    sample = latest[0] if has_draft else None

    if has_draft and sample:
        hero_name = escape(sample["recipient_name"])
        hero_website = escape(sample["website"])
        hero_intent = escape(sample.get("intent", "Outreach"))
        hero_links = sample.get("links_found", 0)
        hero_relevant = sample.get("relevant_links", 0)
        hero_ranked = sample.get("pages_ranked", 0)

        to_email = escape(sample.get("recipient_email", ""))
        to_display = f"{hero_name} &lt;{to_email}&gt;"
        subject = escape(draft.get("subject", ""))
        body = draft.get("body", "").replace(chr(10), "<br>")
    else:
        hero_name = "Prof. Aditya Rao"
        hero_website = "rai-lab.edu"
        hero_intent = "Research Collaboration"
        hero_links = 21
        hero_relevant = 7
        hero_ranked = 5
        to_display = 'prof.aditya@lab.edu <span class="email-tag">RETRIEVED</span>'
        subject = 'Re: Your recent work on <span class="highlight">multi-modal RAG pipelines</span>'
        body = (
            '<p>Dear Prof. Aditya,</p>'
            '<p>I came across your group\'s work on <span class="highlight">retrieval-augmented generation for scientific literature</span>, especially the recent paper on cross-document reasoning, and it maps closely to what I am exploring.</p>'
            '<p>Would a 20-minute conversation make sense to ask a few focused questions and see if there is common ground?</p>'
            '<p>Best,<br>Kunal</p>'
        )

    render_html(
        f"""
        <section class="hero">
            <div class="hero-grid-bg"></div>
            <div class="hero-layout">
                <div class="hero-inner">
                    <div class="eyebrow"><span class="eyebrow-dot"></span>Agentic AI - RAG - Personalization</div>
                    <h1 class="hero-headline">
                        Cold emails that<br>
                        actually sound like<br>
                        you did <em>your homework.</em>
                    </h1>
                    <p class="hero-sub">
                        TOBI reads their website, understands their work, and writes outreach so specific it feels handcrafted at scale.
                    </p>
                    <div class="hero-actions">
                        <a href="?mode=try" class="btn-primary">
                            Generate Draft
                        </a>
                        <span class="hero-stat">
                            URL &rarr; Gmail draft in ~15 seconds
                        </span>
                    </div>
                </div>
                <div class="hero-preview">
                    <div class="preview-row"><span class="preview-label">Recipient</span><span class="preview-value">{hero_name}</span></div>
                    <div class="preview-row"><span class="preview-label">Website</span><span class="preview-value">{hero_website}</span></div>
                    <div class="preview-row"><span class="preview-label">Intent</span><span class="preview-value">{hero_intent}</span></div>
                    <div class="preview-divider"></div>
                    <div class="preview-row"><span class="preview-label">Links Found</span><span class="preview-value">{hero_links}</span></div>
                    <div class="preview-row"><span class="preview-label">Relevant</span><span class="preview-value">{hero_relevant}</span></div>
                    <div class="preview-row"><span class="preview-label">Ranked</span><span class="preview-value">{hero_ranked}</span></div>
                    <div class="preview-divider"></div>
                    <div class="preview-row"><span class="preview-label">Status</span><span class="preview-value preview-ok">Draft Saved to Gmail</span></div>
                </div>
            </div>
        </section>
        <div class="divider"></div>
        <section class="section fade-section">
            <p class="section-label">Output Example</p>
            <h2 class="section-headline">From URL to inbox-ready copy.</h2>
            <p class="section-sub">Paste a prospect's website. TOBI reads every relevant page, builds an intelligence profile, then drafts.</p>
            <div class="email-demo">
                <div class="window-bar">
                    <span class="dot dot-r"></span><span class="dot dot-y"></span><span class="dot dot-g"></span>
                    <span class="window-title">tobi - gmail draft</span>
                </div>
                <div class="email-body">
                    <div class="email-field"><span class="email-field-label">from</span><span class="email-field-value">your@email.com</span></div>
                    <div class="email-field"><span class="email-field-label">to</span><span class="email-field-value">{to_display}</span></div>
                    <div class="email-subject">{subject}</div>
                    <div class="email-content">{body}</div>
                </div>
            </div>
        </section>
        <div class="divider"></div>
        """
    )

    render_outreach_board(sample=True)

    render_html(
        """
        <div class="divider"></div>
        <section class="section fade-section">
            <p class="section-label">How TOBI Thinks</p>
            <h2 class="section-headline">From URL to email in five steps.</h2>
            <p class="section-sub">Every outreach begins as a URL and passes through TOBI's research pipeline before a single word is written.</p>
            <div class="workflow-steps">
                <div class="workflow-step">
                    <div class="workflow-marker"><span>01</span></div>
                    <div class="workflow-label">Website</div>
                </div>
                <div class="workflow-step">
                    <div class="workflow-marker"><span>02</span></div>
                    <div class="workflow-label">Links Discovered</div>
                </div>
                <div class="workflow-step">
                    <div class="workflow-marker"><span>03</span></div>
                    <div class="workflow-label">Relevant Pages Ranked</div>
                </div>
                <div class="workflow-step">
                    <div class="workflow-marker"><span>04</span></div>
                    <div class="workflow-label">Recipient Profile Generated</div>
                </div>
                <div class="workflow-step">
                    <div class="workflow-marker"><span>05</span></div>
                    <div class="workflow-label">Personalized Email Draft</div>
                </div>
            </div>
        </section>
        """
    )

    render_html(
        """
        <div class="divider"></div>
        <section class="section accented fade-section">
            <div class="split">
                <div>
                    <p class="section-label">Intelligence Layer</p>
                    <h2 class="section-headline">It reads, not just scrapes.</h2>
                    <p class="section-sub">TOBI builds a structured profile from public pages, ranked by semantic relevance to your goal.</p>
                    <div class="tech-grid">
                        <span class="tech-pill">Trafilatura</span>
                        <span class="tech-pill">BeautifulSoup</span>
                        <span class="tech-pill">Sentence Transformers</span>
                        <span class="tech-pill">scikit-learn</span>
                        <span class="tech-pill">OpenRouter API</span>
                    </div>
                </div>
                <div class="profile-card">
                    <div class="profile-card-header">
                        <div class="profile-avatar">SK</div>
                        <div>
                            <div class="profile-name">Sarah Kim</div>
                            <div class="profile-role">Founder - AI Infrastructure</div>
                        </div>
                        <div class="profile-source">tobi://profile</div>
                    </div>
                    <div class="insight-row"><span class="insight-key">FOCUS</span><span class="insight-val">Building <span class="highlight">inference optimization</span> tooling for edge deployment.</span></div>
                    <div class="insight-row"><span class="insight-key">RECENT</span><span class="insight-val">Published notes on <span class="highlight">quantization tradeoffs</span> and production latency.</span></div>
                    <div class="insight-row"><span class="insight-key">SIGNAL</span><span class="insight-val">Open to technical partnerships with infrastructure teams.</span></div>
                    <div class="insight-row"><span class="insight-key">TONE FIT</span><span class="insight-val">Technical, direct, low-fluff; responds well to specificity.</span></div>
                </div>
            </div>
        </section>
        <div class="divider"></div>
        <section class="section fade-section">
            <div class="split reverse">
                <div>
                    <p class="section-label">Under the Hood</p>
                    <h2 class="section-headline">Agentic pipeline, not a template engine.</h2>
                    <p class="section-sub">Every step runs autonomously, from link crawling to profile synthesis to Gmail draft creation. You guide tone; TOBI does the research.</p>
                </div>
                <div class="terminal">
                    <div class="terminal-bar"><span class="dot dot-r"></span><span class="dot dot-y"></span><span class="dot dot-g"></span></div>
                    <div class="terminal-body">
                        <div><span class="t-dim">$</span> <span class="t-green">tobi run</span> <span class="t-white">--url https://sarahkim.dev</span></div><br>
                        <div><span class="t-dim">[01/06]</span> <span class="t-blue">Extracting</span> homepage content...</div>
                        <div><span class="t-dim">[02/06]</span> <span class="t-blue">Discovered</span> <span class="t-orange">14 internal links</span></div>
                        <div><span class="t-dim">[03/06]</span> <span class="t-blue">Filtering</span> by heuristic relevance...</div>
                        <div><span class="t-dim">[04/06]</span> <span class="t-blue">Ranking</span> by semantic similarity...</div>
                        <div><span class="t-dim">[05/06]</span> <span class="t-blue">Synthesizing</span> LLM profile...</div>
                        <div><span class="t-dim">[06/06]</span> <span class="t-green">OK Draft saved to Gmail</span></div>
                    </div>
                </div>
            </div>
        </section>
        <div class="divider"></div>
        <section class="section fade-section">
            <p class="section-label">Use Cases</p>
            <h2 class="section-headline">Built for anyone who reaches out for a living.</h2>
            <div class="usecase-grid">
                <div class="usecase-card"><div class="usecase-num">01 / ACADEMIA</div><div class="usecase-title">Research Outreach</div><div class="usecase-desc">Email professors with specific references to their publications and labs.</div></div>
                <div class="usecase-card"><div class="usecase-num">02 / STARTUPS</div><div class="usecase-title">Founder Outreach</div><div class="usecase-desc">Reference exact portfolio and thesis signals before asking for time.</div></div>
                <div class="usecase-card"><div class="usecase-num">03 / RECRUITING</div><div class="usecase-title">Recruiting</div><div class="usecase-desc">Reference open-source work, blog posts, or talks without sounding generic.</div></div>
                <div class="usecase-card"><div class="usecase-num">04 / BD</div><div class="usecase-title">Partnership Discovery</div><div class="usecase-desc">Identify product overlap and strategic fit before writing a single word.</div></div>
            </div>
            <div class="stat-row">
                <div class="stat-item"><div class="stat-num"><span>14</span>+</div><div class="stat-label">Pages Analyzed</div></div>
                <div class="stat-item"><div class="stat-num"><span>7</span>+</div><div class="stat-label">Signals Extracted</div></div>
                <div class="stat-item"><div class="stat-num"><span>&lt;15</span>s</div><div class="stat-label">URL &rarr; Draft</div></div>
            </div>
        </section>
        <div class="tobi-footer">
            <span>TOBI - Tonally Obliged, Bespoke Interface</span>
            <span><a href="https://github.com/kunal1704/TOBI"
                    target="_blank"
                    class="gmail-link"
                    >
                    GitHub →
                </a>
            </span>
        </div>
        """
    )


def render_auth_page():
    render_nav(show_try=True)
    render_html(
        """
        <section class="auth-shell">
            <div class="eyebrow"><span class="eyebrow-dot"></span>TOBI Account</div>
            <h1 class="workflow-headline">Save your sender profile<br>on this device.</h1>
            <p class="hero-sub">
                Sign up or log in to keep your sender profile and avoid re-entering the same information.
            </p>
        </section>
        """
    )

    login_tab, signup_tab = st.tabs(["Login", "Sign up"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            remember = st.checkbox("Stay signed in on this device", value=True)
            submitted = st.form_submit_button("Login")

        if submitted:
            user = verify_user(email, password)

            if not user:
                st.error("Invalid email or password.")
                st.stop()

            st.session_state.current_user = user

            if remember:
                remember_user(user["email"])

            st.query_params["mode"] = "profile"
            st.rerun()

    with signup_tab:
        with st.form("signup_form"):
            full_name = st.text_input("Full Name", key="signup_name")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            remember = st.checkbox("Stay signed in on this device", value=True, key="signup_remember")
            submitted = st.form_submit_button("Create Account")

        if submitted:
            if len(password) < 8:
                st.error("Please use a password with at least 8 characters.")
                st.stop()

            try:
                user = create_user(email, password, full_name=full_name)
            except ValueError as exc:
                st.error(str(exc))
                st.stop()

            st.session_state.current_user = user

            if remember:
                remember_user(user["email"])

            st.query_params["mode"] = "profile"
            st.rerun()


def extract_link_sources(link_map, other_links):
    sources = []

    for label, url in link_map.items():
        if not url:
            continue

        text = extract_website_text(url)
        sources.append({
            "type": label,
            "url": url,
            "text": text or "",
        })

    for url in other_links:
        if not url:
            continue

        text = extract_website_text(url)
        sources.append({
            "type": "other_link",
            "url": url,
            "text": text or "",
        })

    return sources


def extract_file_sources(cv_file, other_files):
    sources = []

    for label, uploaded_file in [("cv_resume", cv_file)]:
        if not uploaded_file:
            continue

        sources.append({
            "type": label,
            "name": uploaded_file.name,
            "text": extract_uploaded_file(uploaded_file),
        })

    for uploaded_file in other_files or []:
        sources.append({
            "type": "other_file",
            "name": uploaded_file.name,
            "text": extract_uploaded_file(uploaded_file),
        })

    return sources


def render_profile_summary(profile):
    if not profile:
        render_html(
            """
            <div class="profile-summary-card">
                <p class="section-label">Sender Profile</p>
                <h2 class="section-headline">No profile built yet.</h2>
                <p class="section-sub">Upload your links and documents, then build a sender profile TOBI can reuse for every draft.</p>
            </div>
            """
        )
        return

    name = escape(profile.get("full_name", ""))
    affiliation = escape(profile.get("affiliation", ""))
    current_focus = escape(profile.get("current_focus", ""))
    summary = escape(profile.get("summary", ""))
    expertise = ", ".join(profile.get("expertise", [])[:6]) if isinstance(profile.get("expertise"), list) else ""

    render_html(
        f"""
        <div class="profile-summary-card">
            <p class="section-label">Sender Profile</p>
            <h2 class="section-headline">{name or "Your TOBI profile"}</h2>
            <div class="profile-kv"><span>Affiliation</span><strong>{affiliation}</strong></div>
            <div class="profile-kv"><span>Current Focus</span><strong>{current_focus}</strong></div>
            <div class="profile-kv"><span>Expertise</span><strong>{escape(expertise)}</strong></div>
            <div class="profile-kv"><span>Summary</span><strong>{summary}</strong></div>
        </div>
        """
    )


def render_profile_editor(user, profile):
    profile = profile or {}
    links = profile.get("links", {}) if isinstance(profile.get("links"), dict) else {}

    st.markdown("#### Update Sender Profile")

    with st.form("profile_editor_form"):
        col1, col2 = st.columns(2)

        with col1:
            full_name = st.text_input(
                "Full Name",
                value=profile.get("full_name", user.get("full_name", "")),
                key="edit_full_name",
            )
            affiliation = st.text_input(
                "Affiliation (if any)",
                value=profile.get("affiliation", ""),
                key="edit_affiliation",
            )
            location = st.text_input(
                "Location",
                value=profile.get("location", ""),
                key="edit_location",
            )
            signature = st.text_input(
                "Email Signature",
                value=profile.get("signature", ""),
                placeholder="Best, Kunal",
                key="edit_signature",
            )
            availability = st.text_input(
                "Availability",
                value=profile.get("availability", ""),
                placeholder="e.g. Open to short calls on weekdays",
                key="edit_availability",
            )

        with col2:
            summary = st.text_area(
                "Professional Summary",
                value=profile.get("summary", ""),
                height=130,
                key="edit_summary",
            )
            current_focus = st.text_area(
                "Current Focus",
                value=profile.get("current_focus", ""),
                height=105,
                key="edit_current_focus",
            )
            writing_style = st.text_area(
                "Writing Style",
                value=profile.get("writing_style", ""),
                placeholder="e.g. concise, technical, warm, low-fluff",
                height=95,
                key="edit_writing_style",
            )

        st.markdown("#### Experience and Outreach Context")
        col3, col4 = st.columns(2)

        with col3:
            expertise = st.text_area(
                "Expertise",
                value=as_lines(profile.get("expertise")),
                placeholder="One skill or domain per line.",
                height=120,
                key="edit_expertise",
            )
            projects = st.text_area(
                "Projects",
                value=as_lines(profile.get("projects")),
                placeholder="One project per line.",
                height=120,
                key="edit_projects",
            )
            achievements = st.text_area(
                "Achievements",
                value=as_lines(profile.get("achievements")),
                placeholder="One achievement per line.",
                height=120,
                key="edit_achievements",
            )

        with col4:
            education = st.text_area(
                "Education",
                value=as_lines(profile.get("education")),
                placeholder="One education item per line.",
                height=120,
                key="edit_education",
            )
            collaboration_interests = st.text_area(
                "Collaboration Interests",
                value=as_lines(profile.get("collaboration_interests")),
                placeholder="What kinds of people/projects do you want to reach out to?",
                height=120,
                key="edit_collaboration_interests",
            )
            target_audience = st.text_area(
                "Target Audience",
                value=as_lines(profile.get("target_audience")),
                placeholder="e.g. professors, founders, recruiters, investors",
                height=120,
                key="edit_target_audience",
            )

        outreach_strengths = st.text_area(
            "Outreach Strengths",
            value=as_lines(profile.get("outreach_strengths")),
            placeholder="What credibility points should TOBI lean on? One per line.",
            height=105,
            key="edit_outreach_strengths",
        )
        missing_information = st.text_area(
            "Missing Information / Reminders",
            value=as_lines(profile.get("missing_information")),
            placeholder="Anything TOBI should ask you to fill later. One per line.",
            height=95,
            key="edit_missing_information",
        )

        st.markdown("#### Profile Links")
        col5, col6, col7 = st.columns(3)

        with col5:
            linkedin = st.text_input("LinkedIn", value=links.get("linkedin", ""), key="edit_linkedin")

        with col6:
            website = st.text_input("Website", value=links.get("website", ""), key="edit_website")

        with col7:
            github = st.text_input("GitHub", value=links.get("github", ""), key="edit_github")

        other_links = st.text_area(
            "Other Links",
            value=as_lines(links.get("other")),
            placeholder="One link per line.",
            height=95,
            key="edit_other_links",
        )

        save_clicked = st.form_submit_button("Save Profile")

    if save_clicked:
        edited_profile = {
            "full_name": full_name,
            "affiliation": affiliation,
            "location": location,
            "summary": summary,
            "current_focus": current_focus,
            "expertise": lines_to_list(expertise),
            "projects": lines_to_list(projects),
            "achievements": lines_to_list(achievements),
            "education": lines_to_list(education),
            "collaboration_interests": lines_to_list(collaboration_interests),
            "target_audience": lines_to_list(target_audience),
            "links": {
                "linkedin": linkedin,
                "website": website,
                "github": github,
                "other": lines_to_list(other_links),
            },
            "writing_style": writing_style,
            "outreach_strengths": lines_to_list(outreach_strengths),
            "signature": signature,
            "availability": availability,
            "missing_information": lines_to_list(missing_information),
        }

        st.session_state.current_user = save_user_profile(user["email"], edited_profile)
        st.session_state.editing_sender_profile = False
        st.success("Profile saved.")
        st.rerun()


def render_profile_page():
    if not st.session_state.current_user:
        render_auth_page()
        return

    render_nav(show_try=True)
    user = st.session_state.current_user
    saved_profile = user.get("profile") or {}
    has_saved_profile = bool(saved_profile)

    render_html(
        f"""
        <section class="profile-shell">
            <div class="eyebrow"><span class="eyebrow-dot"></span>Sender Profile</div>
            <h1 class="workflow-headline">Teach TOBI who you are.</h1>
            <p class="hero-sub">
                Add your CV, LinkedIn, website, GitHub, and supporting files. TOBI will build a reusable sender profile you can inspect and edit.
            </p>
            <div class="hero-stat">Signed in as {escape(user["email"])}</div>
        </section>
        """
    )

    render_profile_summary(saved_profile)

    if has_saved_profile and not st.session_state.get("editing_sender_profile", False):
        if st.button("Update Profile", type="primary"):
            st.session_state.editing_sender_profile = True
            st.rerun()

        return

    if has_saved_profile and st.session_state.get("editing_sender_profile", False):
        render_profile_editor(user, saved_profile)

        if st.button("Cancel"):
            st.session_state.editing_sender_profile = False
            st.rerun()

        return

    with st.form("profile_builder_form"):
        st.markdown("#### Core Details")
        col1, col2 = st.columns(2)

        with col1:
            full_name = st.text_input("Full Name", value=saved_profile.get("full_name", user.get("full_name", "")))
            affiliation = st.text_input("Affiliation (if any)", value=saved_profile.get("affiliation", ""))
            location = st.text_input("Location", value=saved_profile.get("location", ""))

        with col2:
            current_focus = st.text_area(
                "Current Focus",
                value=saved_profile.get("current_focus", ""),
                placeholder="What are you currently working on or exploring?",
                height=95,
            )
            profile_notes = st.text_area(
                "Profile Notes",
                placeholder="Anything TOBI should consider while building your profile from your sources.",
                height=110,
            )

        st.markdown("#### Links")
        col3, col4, col5 = st.columns(3)

        links = saved_profile.get("links", {}) if isinstance(saved_profile.get("links"), dict) else {}

        with col3:
            linkedin = st.text_input("LinkedIn", value=links.get("linkedin", ""))

        with col4:
            website = st.text_input("Website", value=links.get("website", ""))

        with col5:
            github = st.text_input("GitHub", value=links.get("github", ""))

        other_links_text = st.text_area(
            "Other Links",
            value="\n".join(links.get("other", [])) if isinstance(links.get("other"), list) else "",
            placeholder="Add one link per line.",
            height=110,
        )

        st.markdown("#### Uploads")
        cv_file = st.file_uploader("CV / Resume", type=["pdf", "docx", "txt", "md"])
        other_files = st.file_uploader(
            "Other files / folder contents",
            type=["pdf", "docx", "txt", "md", "csv"],
            accept_multiple_files=True,
            help="Streamlit cannot select folders directly, but you can select multiple files from a folder.",
        )

        build_clicked = st.form_submit_button("Build / Update Profile")

    if build_clicked:
        other_links = [line.strip() for line in other_links_text.splitlines() if line.strip()]
        link_map = {
            "linkedin": linkedin.strip(),
            "website": website.strip(),
            "github": github.strip(),
        }

        with st.spinner("Building your sender profile..."):
            try:
                link_sources = extract_link_sources(link_map, other_links)
                file_sources = extract_file_sources(cv_file, other_files)
            except Exception as exc:
                st.error(str(exc))
                st.stop()

            source_payload = {
                "manual_details": {
                    "full_name": full_name,
                    "affiliation": affiliation,
                    "location": location,
                    "current_focus": current_focus,
                    "profile_notes": profile_notes,
                },
                "links": {
                    "linkedin": linkedin,
                    "website": website,
                    "github": github,
                    "other": other_links,
                },
                "link_sources": link_sources,
                "file_sources": file_sources,
            }

            built_profile = build_user_profile(source_payload)

        if "error" in built_profile:
            st.error("TOBI could not parse the generated profile.")
            st.text_area("Raw output", built_profile.get("raw_output", ""), height=260)
            st.stop()

        built_profile["full_name"] = built_profile.get("full_name") or full_name
        built_profile["affiliation"] = built_profile.get("affiliation") or affiliation
        built_profile["location"] = built_profile.get("location") or location
        built_profile["current_focus"] = built_profile.get("current_focus") or current_focus

        st.session_state.current_user = save_user_profile(user["email"], built_profile)
        st.session_state.editing_sender_profile = False
        st.success("Profile updated.")
        st.rerun()


def run_retrieval_pipeline(website):
    st.session_state.workflow_status["Website Extraction"] = "running"
    homepage_text = extract_website_text(website)
    st.session_state.workflow_status["Website Extraction"] = "completed" if homepage_text else "failed"

    st.session_state.workflow_status["Link Discovery"] = "running"
    links = get_internal_links(website)
    filtered_links = filter_relevant_links(links)
    st.session_state.workflow_status["Link Discovery"] = "completed"

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

    st.session_state.workflow_status["Semantic Ranking"] = "running"
    ranked_pages = rank_pages_semantically(page_data)
    st.session_state.workflow_status["Semantic Ranking"] = "completed"

    combined_text = ""

    for page in ranked_pages[:SEMANTIC_TOP_K]:
        combined_text += f"\n\nPAGE: {page['url']}\n\n"
        combined_text += page["text"][:MAX_TEXT_PER_PAGE]

    st.session_state.workflow_status["Profile Generation"] = "running"
    profile = extract_recipient_profile(combined_text)
    st.session_state.workflow_status["Profile Generation"] = "completed" if profile else "failed"

    st.session_state.profile = profile
    st.session_state.combined_text = combined_text
    st.session_state.ranked_pages = ranked_pages

    return {
        "homepage_found": bool(homepage_text),
        "links_found": len(links),
        "relevant_links": len(filtered_links),
        "pages_ranked": len(ranked_pages),
    }


def progress_markup(active_step, error=None):
    steps = [
        ("01", "Extract website", "Crawling source pages"),
        ("02", "Build profile", "Ranking useful signal"),
        ("03", "Write draft", "Generating subject/body"),
        ("04", "Save to Gmail", "Creating draft"),
    ]

    rendered_steps = []

    for idx, (number, title, subtitle) in enumerate(steps):
        if error and idx == active_step:
            state = "active"
            subtitle = error
        elif active_step >= len(steps):
            state = "done"
            subtitle = "Completed"
        elif idx < active_step:
            state = "done"
            subtitle = "Completed"
        elif idx == active_step:
            state = "active"
        else:
            state = ""

        rendered_steps.append(
            f"""
            <div class="progress-step {state}">
                <div>{number}</div>
                <strong>{escape(title)}</strong>
                <span>{escape(subtitle)}</span>
            </div>
            """
        )

    title = "Creating your Gmail draft..." if not error else "TOBI needs your attention"
    ring = '<span class="progress-ring"></span>' if active_step < len(steps) and not error else ""

    return dedent(
        f"""
        <div class="progress-panel">
            <div class="progress-title">{ring}<span>{escape(title)}</span></div>
            <div class="progress-steps">
                {''.join(rendered_steps)}
            </div>
        </div>
        """
    ).strip()


def render_workflow():
    if not st.session_state.current_user:
        render_auth_page()
        return

    render_nav(show_try=False)
    user_profile = get_current_profile()

    if not user_profile:
        render_html(
            """
            <section class="draft-header">
                <div class="eyebrow"><span class="eyebrow-dot"></span>Profile Required</div>
                <h1 class="workflow-headline">Create your sender profile first.</h1>
                <p class="hero-sub">
                    TOBI now uses your saved profile to write stronger outreach. Build it once, edit it anytime, and reuse it for every draft.
                </p>
                <a href="?mode=profile" class="btn-primary">Create Profile</a>
            </section>
            """
        )
        return

    render_html(
        """
        <section class="draft-header">
            <div class="hero-layout">
                <div>
                    <div class="eyebrow"><span class="eyebrow-dot"></span>TOBI Draft Studio</div>
                    <h1 class="workflow-headline">Generate a Gmail draft<br>from a recipient's website.</h1>
                    <p class="hero-sub">
                        Add the recipient, your goal, and the context TOBI cannot infer. One click extracts, drafts, saves to Gmail, and hands you off to review before sending.
                    </p>
                </div>
                <div class="hero-preview">
                    <div class="preview-row"><span class="preview-label">Pipeline</span><span class="preview-value">6 stages</span></div>
                    <div class="preview-divider"></div>
                    <div class="preview-row"><span class="preview-label">01</span><span class="preview-value">Website Extraction</span></div>
                    <div class="preview-row"><span class="preview-label">02</span><span class="preview-value">Link Discovery</span></div>
                    <div class="preview-row"><span class="preview-label">03</span><span class="preview-value">Semantic Ranking</span></div>
                    <div class="preview-row"><span class="preview-label">04</span><span class="preview-value">Profile Generation</span></div>
                    <div class="preview-row"><span class="preview-label">05</span><span class="preview-value">Draft Creation</span></div>
                    <div class="preview-row"><span class="preview-label">06</span><span class="preview-value">Gmail Save</span></div>
                    <div class="preview-divider"></div>
                    <div class="preview-row"><span class="preview-value preview-ok">→ 1 click · ~15 seconds</span></div>
                </div>
            </div>
        </section>
        """
    )

    with st.form("draft_form"):
        col_left, col_right = st.columns([3, 2])

        with col_left:
            with st.expander("Recipient", expanded=True):
                col1, col2 = st.columns(2)

                with col1:
                    recipient_name = st.text_input("Recipient Name")
                    recipient_email = st.text_input("Recipient Email")

                with col2:
                    website = st.text_input("Website URL")
                    intent = st.selectbox("Outreach Intent", INTENTS)

            outreach_goal = st.text_area(
                "Outreach Goal",
                placeholder="What should this email accomplish?",
                height=110,
            )

            with st.expander("Draft Preferences", expanded=False):
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

            sender_affiliation = st.text_input(
                "Affiliation (if any)",
                value=user_profile.get("affiliation", ""),
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

        with col_right:

            status_placeholder = st.empty()

            def render_runtime_panel():
                status_map = st.session_state.get("workflow_status", {})

                pipeline_steps = [
                    "Website Extraction",
                    "Link Discovery",
                    "Semantic Ranking",
                    "Profile Generation",
                    "Draft Creation",
                    "Gmail Save",
                ]

                rows = ""

                for step in pipeline_steps:
                    state = status_map.get(step, "waiting")

                    if state == "completed":
                        icon, cls = "✓", "runtime-check"
                    elif state == "running":
                        icon, cls = "◉", "runtime-running"
                    elif state == "failed":
                        icon, cls = "✕", "runtime-failed"
                    else:
                        icon, cls = "○", "runtime-pending"

                    rows += f"""
                    <div class="runtime-step">
                        <span class="{cls}">{icon}</span>
                        {step}
                    </div>
                    """

                status_placeholder.markdown(
                    f"""
                    <div class="runtime-card">
                        <div class="runtime-card-header">Runtime Status</div>
                        {rows}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            render_runtime_panel()
    if generate_clicked:
        required_fields = {
            "recipient name": recipient_name,
            "recipient email": recipient_email,
            "website URL": website,
            "outreach goal": outreach_goal,
        }
        missing = [label for label, value in required_fields.items() if not value.strip()]

        if missing:
            st.error(f"Please add {', '.join(missing)} before generating the draft.")
            st.stop()

        details = {
            "recipient_name": recipient_name,
            "recipient_email": recipient_email,
            "website": website,
            "sender_name": user_profile.get("full_name", ""),
            "sender_affiliation": sender_affiliation,
            "sender_background": build_sender_context(user_profile),
            "user_profile": user_profile,
            "tone": tone,
            "intent": intent,
            "call_to_action": call_to_action,
            "length": length,
            "outreach_goal": outreach_goal,
            "extra_context": extra_context,
            "things_to_avoid": avoid,
        }

        progress_slot = st.empty()
        st.session_state.workflow_status = {}

        with progress_slot.container():
            render_html(progress_markup(0))

        extraction_summary = run_retrieval_pipeline(website)
        st.session_state.extraction_summary = extraction_summary

        progress_slot.empty()
        with progress_slot.container():
            render_html(progress_markup(1))

        st.session_state.workflow_status["Draft Creation"] = "running"
        draft = generate_email_draft(
            st.session_state.profile,
            st.session_state.combined_text,
            details,
        )

        if "error" in draft:
            st.session_state.workflow_status["Draft Creation"] = "failed"
            render_html(
                progress_markup(
                    2,
                    error="TOBI could not format the generated draft."
                )
            )

            st.session_state.email_draft = draft
            st.stop()

        st.session_state.email_draft = draft
        st.session_state.workflow_status["Draft Creation"] = "completed"

        progress_slot.empty()
        with progress_slot.container():
            render_html(progress_markup(2))

        st.session_state.workflow_status["Gmail Save"] = "running"
        gmail_result = create_gmail_draft(
            to_email=recipient_email,
            subject=draft["subject"],
            body=draft["body"],
        )

        st.session_state.gmail_result = gmail_result
        st.session_state.workflow_status["Gmail Save"] = "completed"

        progress_slot.empty()
        with progress_slot.container():
            render_html(progress_markup(3))

        add_outreach_record(
            details,
            draft,
            extraction_summary,
            gmail_result,
        )

        progress_slot.empty()
        with progress_slot.container():
            render_html(progress_markup(4))

        render_success(extraction_summary)
    elif st.session_state.email_draft:
        render_success()


def render_success(extraction_summary=None):
    draft = st.session_state.email_draft
    gmail_url = st.session_state.gmail_result.get("gmail_url", GMAIL_DRAFTS_URL)

    latest = st.session_state.outreach_history[0] if st.session_state.outreach_history else {}

    render_html(
        f"""
        <div class="runtime-card">
            <div class="runtime-card-header">✓ Draft Saved</div>
            {f'<div class="preview-row"><span class="preview-label">Recipient</span><span class="preview-value">{latest["recipient_name"]}</span></div>' if latest.get("recipient_name") else ''}
            {f'<div class="preview-row"><span class="preview-label">Website</span><span class="preview-value">{latest["website"]}</span></div>' if latest.get("website") else ''}
            {f'<div class="preview-row"><span class="preview-label">Generated</span><span class="preview-value">{latest["created_at"]}</span></div>' if latest.get("created_at") else ''}
        </div>
        """
    )

    if extraction_summary:
        render_html(
            f"""
            <div class="workspace-card" style="margin-top:1rem;margin-bottom:2rem">
                <div class="workspace-stat-grid">
                    <div class="workspace-stat-item">
                        <div class="workspace-stat-num"><span>{extraction_summary["links_found"]}</span></div>
                        <div class="workspace-stat-label">Links Found</div>
                    </div>
                    <div class="workspace-stat-item">
                        <div class="workspace-stat-num"><span>{extraction_summary["relevant_links"]}</span></div>
                        <div class="workspace-stat-label">Relevant Links</div>
                    </div>
                    <div class="workspace-stat-item">
                        <div class="workspace-stat-num"><span>{extraction_summary["pages_ranked"]}</span></div>
                        <div class="workspace-stat-label">Pages Ranked</div>
                    </div>
                </div>
            </div>
            """
        )

    if "gmail_opened" not in st.session_state:
        st.session_state.gmail_opened = True

        components.html(
            f"""
            <script>
            setTimeout(() => {{
                window.open("{gmail_url}", "_blank", "noopener,noreferrer");
            }}, 1600);
            </script>
            """,
            height=0,
        )

    to_name = latest.get("recipient_name", "")
    to_email = latest.get("recipient_email", "")
    to_display = f"{to_name} <{to_email}>" if to_name and to_email else (to_name or to_email or "Recipient")

    render_html(
        f"""
        <div class="workspace-card">
            <div class="window-bar">
                <span class="dot dot-r"></span><span class="dot dot-y"></span><span class="dot dot-g"></span>
                <span class="window-title">tobi - gmail draft</span>
            </div>
            <div class="workspace-card-body">
                <div class="email-field"><span class="email-field-label">from</span><span class="email-field-value">your@email.com</span></div>
                <div class="email-field"><span class="email-field-label">to</span><span class="email-field-value">{to_display}</span></div>
                <div class="email-subject">{draft.get("subject", "")}</div>
                <div class="email-content">{draft.get("body", "").replace(chr(10), "<br>")}</div>
                <div style="border-top:1px solid var(--border);padding-top:1rem;margin-top:1.5rem;text-align:center">
                    <a class="gmail-link" href="{gmail_url}" target="_blank" rel="noopener">Open Gmail Draft →</a>
                </div>
            </div>
        </div>
        """
    )

    profile = st.session_state.get("profile", {})

    def fmt(val):
        if isinstance(val, list):
            return [str(v) for v in val if v]
        return [str(val)] if val else []

    sections = []

    mapping = [
        ("Research Interests", "Research interests"),
        ("Current Topics", "Current topics"),
        ("Recent Work", "Notable achievements"),
        ("Outreach Hooks", "Personalization hooks"),
    ]

    for title, key in mapping:
        items = fmt(profile.get(key, ""))
        if items:
            bullets = "".join(
                f'<li style="color:var(--text-secondary);font-size:13px;line-height:1.7;margin-bottom:4px">{escape(i)}</li>'
                for i in items
            )
            sections.append(
                f'<div style="margin-bottom:1.2rem">'
                f'<div style="color:var(--text-muted);font-family:var(--font-mono);font-size:10px;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px">{title}</div>'
                f'<ul style="margin:0;padding-left:1.2rem;list-style:disc">{bullets}</ul>'
                f'</div>'
            )

    if sections:
        render_html(
            f"""
            <div class="profile-card" style="margin-top:1.5rem">
                <div class="profile-card-header">
                    <div class="profile-avatar">{escape(get_initials(latest.get("recipient_name", "")))}</div>
                    <div>
                        <div class="profile-name">{escape(latest.get("recipient_name", ""))}</div>
                        <div class="profile-role">{escape(latest.get("recipient_email", ""))}</div>
                    </div>
                    <div class="profile-source">tobi://profile</div>
                </div>
                {''.join(sections)}
            </div>
            """
        )

    render_outreach_board(st.session_state.outreach_history)


st.set_page_config(page_title="TOBI", layout="wide", initial_sidebar_state="collapsed")
initialize_state()
apply_styles()

if is_logout_mode():
    clear_remembered_user()
    st.session_state.current_user = None
    st.query_params["mode"] = "auth"
    st.rerun()
elif is_auth_mode():
    render_auth_page()
elif is_profile_mode():
    render_profile_page()
elif is_try_mode():
    render_workflow()
else:
    render_landing()
