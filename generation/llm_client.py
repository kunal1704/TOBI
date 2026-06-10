import os

"""
LLM Client Configuration
------------------------

Initializes OpenRouter/OpenAI-compatible API client
for downstream TOBI generation tasks.

Environment variables are loaded using python-dotenv.
"""


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

    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured for this deployment.")

    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )
