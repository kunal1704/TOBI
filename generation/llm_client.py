import os

from openai import OpenAI
from dotenv import load_dotenv

"""
LLM Client Configuration
------------------------

Initializes OpenRouter/OpenAI-compatible API client
for downstream TOBI generation tasks.

Environment variables are loaded using python-dotenv.
"""

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)