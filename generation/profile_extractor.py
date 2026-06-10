import json

from generation.llm_client import get_client


"""
Recipient Profile Extraction Module
-----------------------------------

Uses LLM-based structured extraction to infer:
- research interests
- communication style
- personalization hooks
- achievements
- active domains

Outputs normalized JSON for downstream outreach generation.
"""


def extract_recipient_profile(context):

    prompt = f"""
    You are analyzing a professional or academic profile.

    Extract the following information:

    1. Research interests
    2. Current topics
    3. Communication style
    4. Personalization hooks
    5. Notable achievements

    Return ONLY valid JSON.

    Context:
    {context}
    """

    response = get_client().chat.completions.create(
    model="openai/gpt-oss-120b:free",

    temperature=0.3,

    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ]
)
    content = response.choices[0].message.content

    try:

        cleaned = content.strip()

        if cleaned.startswith("```json"):
            cleaned = cleaned.replace("```json", "")

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        cleaned = cleaned.strip()

        return json.loads(cleaned)

    except Exception as e:

        return {
            "error": str(e),
            "raw_output": content
        }
