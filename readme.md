# TOBI

### Tonally Obliged, Bespoke Interface

Intelligent retrieval-augmented outreach generation system
for research, academic, and professional personalization.

## Overview

TOBI is a retrieval-augmented personalization system designed
for generating highly contextual outreach intelligence from
web-based professional profiles.

The system combines:

- website extraction
- semantic retrieval
- heuristic filtering
- LLM-based structured profiling

TOBI is intended for:

- academic outreach
- research collaboration discovery
- founder/investor personalization
- intelligent cold email generation
- AI-assisted prospect research

## Current Pipeline

1. Homepage extraction
2. Internal link discovery
3. Heuristic relevance filtering
4. Multi-page extraction
5. Semantic ranking
6. LLM-based profile synthesis
7. User-guided email drafting
8. Gmail draft creation

## Architecture

Website
↓
Extraction Layer
↓
Link Discovery
↓
Heuristic Filtering
↓
Semantic Ranking
↓
LLM Profile Extraction
↓
Structured Personalization Context

## Tech Stack

- Python 3.11
- Streamlit
- Sentence Transformers
- OpenRouter API
- Gmail API
- Trafilatura
- BeautifulSoup
- scikit-learn

## Installation

```bash
conda env create -f environment.yml
conda activate tobi
```

## Environment Variables

Create .env

```bash
OPENROUTER_API_KEY=your_key_here
TOBI_ENABLE_GMAIL_DRAFTS=false
```

Optional Gmail settings:

```bash
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.json
```

To save drafts to Gmail, enable the Gmail API in Google Cloud, create an
OAuth desktop client, download it as credentials.json, and run the app.
The first draft save opens a Google OAuth flow and stores token.json locally.
For public deployments, keep `TOBI_ENABLE_GMAIL_DRAFTS=false` unless TOBI has
production-safe per-user OAuth and encrypted token storage.

## Local Profiles

TOBI supports local sign up / login for development. Saved accounts, remembered
sessions, and editable sender profiles are stored in `.tobi_data/`, which is
ignored by git. Uploaded files are read in memory to build the profile and are
not committed to the repository.

## RUN

```bash
streamlit run app.py
```

## Public V1 Deployment

Recommended showcase setup:

1. Deploy the app behind Streamlit Community Cloud, Render, Railway, Fly.io, or another managed Python web host.
2. Set `OPENROUTER_API_KEY` in the host's secret manager, never in the repo.
3. Set `TOBI_ENABLE_GMAIL_DRAFTS=false` for the public demo so users can review/copy drafts without server-side Gmail tokens.
4. Do not upload `.env`, `credentials.json`, `token.json`, `.streamlit/`, or `.tobi_data/`.
5. Use a fresh production API key with usage limits and revoke/rotate it if exposed.

When Gmail draft saving is disabled, TOBI still shows an `Open in Gmail to Save
Draft` link after generation. That link opens Gmail compose in the user's own
browser with the recipient, subject, and body prefilled, without storing Gmail
OAuth tokens on the deployed server.

Public safety notes:

- TOBI rejects localhost, private IP, and internal metadata URLs before fetching website content.
- Generated/user-provided draft content is escaped before being rendered in the app.
- Fetched website text is treated as untrusted context in the drafting prompt.
- The local username/password store in `.tobi_data/` is for V1/demo use, not a production auth system.

## Future Work

Planned extensions:

- Multi-agent retrieval
- RAG memory layer
- Tone-conditioned email generation
- Persona-aware prompting
- Citation-aware retrieval
- Graph-based profile synthesis
- Autonomous outreach optimization
