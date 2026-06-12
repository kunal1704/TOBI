import os

"""
LLM Client Configuration
------------------------

Initializes OpenRouter/OpenAI-compatible API client
for downstream TOBI generation tasks.

Environment variables are loaded using python-dotenv.
"""


def _get_secret(name):
    value = os.getenv(name)

    if value:
        return value

    try:
        import streamlit as st
    except ImportError:
        return None

    try:
        value = st.secrets.get(name)
    except Exception:
        value = None

    if value:
        return str(value)

    try:
        openrouter = st.secrets.get("openrouter", {})
        value = openrouter.get("api_key")
    except Exception:
        value = None

    return str(value) if value else None


def get_client():
    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "The OpenAI Python package is not installed. "
            "Redeploy after Streamlit installs requirements.txt."
        ) from exc

    if load_dotenv is not None:
        load_dotenv()

    api_key = _get_secret("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not configured. Add it in Streamlit Cloud "
            "under Manage app -> Settings -> Secrets, then reboot the app."
        )

    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )
