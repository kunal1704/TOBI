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

'''
conda env create -f environment.yml
conda activate tobi
'''

## Environment Variables

Create .env

OPENROUTER_API_KEY = your_key_here

Optional Gmail settings:

GMAIL_CREDENTIALS_FILE = credentials.json
GMAIL_TOKEN_FILE = token.json

To save drafts to Gmail, enable the Gmail API in Google Cloud, create an
OAuth desktop client, download it as credentials.json, and run the app.
The first draft save opens a Google OAuth flow and stores token.json locally.

## Local Profiles

TOBI supports local sign up / login for development. Saved accounts, remembered
sessions, and editable sender profiles are stored in `.tobi_data/`, which is
ignored by git. Uploaded files are read in memory to build the profile and are
not committed to the repository.

## RUN

streamlit run app.py

## Future Work

Planned extensions:

- Multi-agent retrieval
- RAG memory layer
- Tone-conditioned email generation
- Persona-aware prompting
- Citation-aware retrieval
- Graph-based profile synthesis
- Autonomous outreach optimization
