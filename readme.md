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

API_KEY = your_key_here
