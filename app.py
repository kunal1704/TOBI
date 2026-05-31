from datetime import datetime
from html import escape
from textwrap import dedent

import streamlit as st
import streamlit.components.v1 as components

from configs import *
from extraction.link_extractor import get_internal_links
from extraction.website_extractor import extract_website_text
from generation.email_generator import generate_email_draft
from generation.profile_extractor import extract_recipient_profile
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
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def is_try_mode():
    return st.query_params.get("mode") == "try"


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
        }

        .hero-grid-bg {
            position: absolute;
            inset: 0;
            background-image:
                linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px);
            background-size: 60px 60px;
            mask-image: radial-gradient(ellipse 70% 60% at 50% 50%, black 20%, transparent 100%);
            -webkit-mask-image: radial-gradient(ellipse 70% 60% at 50% 50%, black 20%, transparent 100%);
        }

        .hero::before,
        .section.accented::before,
        .draft-header::before {
            content: '';
            position: absolute;
            inset: 0;
            background:
                linear-gradient(110deg, rgba(200,245,66,0.07), transparent 36%),
                linear-gradient(245deg, rgba(84,214,255,0.08), transparent 38%),
                linear-gradient(0deg, rgba(255,122,182,0.05), transparent 44%);
            border-radius: 18px;
            pointer-events: none;
            -webkit-mask-image: linear-gradient(to bottom, black 70%, transparent 100%);
            mask-image: linear-gradient(to bottom, black 70%, transparent 100%);
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
            border: 1px solid var(--border-bright);
            border-radius: 12px;
            padding: 1.5rem;
            min-width: 280px;
            flex-shrink: 0;
            position: relative;
            z-index: 1;
        }

        .hero-preview::before {
            content: '';
            position: absolute;
            inset: -30px;
            border-radius: 42px;
            background: radial-gradient(ellipse 60% 50% at 50% 40%, rgba(200,245,66,0.08), rgba(84,214,255,0.04), transparent 70%);
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

        div[data-testid="stForm"] {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
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
            background: #050709 !important;
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
            {action}
        </div>
        """
    )


def render_landing():
    render_nav(show_try=True)
    render_html(
        """
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
                    <div class="preview-row"><span class="preview-label">Recipient</span><span class="preview-value">Prof. Aditya Rao</span></div>
                    <div class="preview-row"><span class="preview-label">Website</span><span class="preview-value">rai-lab.edu</span></div>
                    <div class="preview-row"><span class="preview-label">Intent</span><span class="preview-value">Research Collaboration</span></div>
                    <div class="preview-divider"></div>
                    <div class="preview-row"><span class="preview-label">Links Found</span><span class="preview-value">21</span></div>
                    <div class="preview-row"><span class="preview-label">Relevant</span><span class="preview-value">7</span></div>
                    <div class="preview-row"><span class="preview-label">Ranked</span><span class="preview-value">5</span></div>
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
                    <div class="email-field"><span class="email-field-label">from</span><span class="email-field-value">you@yourdomain.com</span></div>
                    <div class="email-field"><span class="email-field-label">to</span><span class="email-field-value">prof.aditya@lab.edu <span class="email-tag">RETRIEVED</span></span></div>
                    <div class="email-subject">Re: Your recent work on <span class="highlight">multi-modal RAG pipelines</span></div>
                    <div class="email-content">
                        <p>Dear Prof. Aditya,</p>
                        <p>I came across your group's work on <span class="highlight">retrieval-augmented generation for scientific literature</span>, especially the recent paper on cross-document reasoning, and it maps closely to what I am exploring.</p>
                        <p>Would a 20-minute conversation make sense to ask a few focused questions and see if there is common ground?</p>
                        <p>Best,<br>Kunal</p>
                    </div>
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
            <span>open-source - github.com/kunal1704/TOBI</span>
        </div>
        """
    )


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
    render_nav(show_try=False)
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

            with st.expander("Sender", expanded=False):
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
                    icon, cls = "◎", "runtime-running"
                elif state == "failed":
                    icon, cls = "✕", "runtime-failed"
                else:
                    icon, cls = "○", "runtime-pending"
                rows += f'<div class="runtime-step"><span class="{cls}">{icon}</span> {step}</div>'
            st.markdown(f"""
            <div class="runtime-card">
                <div class="runtime-card-header">Runtime Status</div>
                {rows}
            </div>
            """, unsafe_allow_html=True)

            summary = st.session_state.get("extraction_summary")
            if st.session_state.get("email_draft") and summary:
                st.markdown(f"""
                <div class="runtime-card" style="margin-top:1rem">
                    <div class="runtime-card-header">Signals Identified</div>
                    <div class="preview-row"><span class="preview-label">Pages Ranked</span><span class="preview-value">{summary["pages_ranked"]}</span></div>
                    <div class="preview-row"><span class="preview-label">Relevant Links</span><span class="preview-value">{summary["relevant_links"]}</span></div>
                    <div class="preview-row"><span class="preview-label">Links Found</span><span class="preview-value">{summary["links_found"]}</span></div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="runtime-card" style="margin-top:1rem">
                    <div class="runtime-card-header">Signals Identified</div>
                    <div class="runtime-step" style="color:var(--text-muted)">Waiting for website analysis...</div>
                </div>
                """, unsafe_allow_html=True)

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
            "website": website,
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

    with st.expander("Recipient intelligence"):
        st.json(st.session_state.profile)

    with st.expander("Source context"):
        st.text_area(
            "Combined extracted context",
            st.session_state.combined_text[:FINAL_CONTEXT_LIMIT],
            height=320,
            label_visibility="collapsed",
        )

    render_outreach_board(st.session_state.outreach_history)


st.set_page_config(page_title="TOBI", layout="wide", initial_sidebar_state="collapsed")
initialize_state()
apply_styles()

if is_try_mode():
    render_workflow()
else:
    render_landing()
