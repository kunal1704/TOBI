import json

from generation.llm_client import client


def _parse_json_response(content):
    cleaned = content.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned.replace("```json", "", 1)

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```", "", 1)

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    return json.loads(cleaned.strip())


def build_user_profile(source_payload):
    prompt = f"""
    You are building a structured sender profile for TOBI.

    Use the supplied links, uploaded document text, and user-entered notes.
    Extract only what is supported by the source material. Do not invent.

    Return ONLY valid JSON with this schema:
    {{
      "full_name": "string",
      "affiliation": "string",
      "location": "string",
      "summary": "string",
      "current_focus": "string",
      "expertise": ["string"],
      "projects": ["string"],
      "achievements": ["string"],
      "education": ["string"],
      "collaboration_interests": ["string"],
      "target_audience": ["string"],
      "links": {{
        "linkedin": "string",
        "website": "string",
        "github": "string",
        "other": ["string"]
      }},
      "writing_style": "string",
      "outreach_strengths": ["string"],
      "signature": "string",
      "availability": "string",
      "missing_information": ["string"]
    }}

    Source payload:
    {json.dumps(source_payload, indent=2)[:18000]}
    """

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b:free",
        temperature=0.25,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    content = response.choices[0].message.content

    try:
        return _parse_json_response(content)

    except Exception as exc:
        return {
            "error": str(exc),
            "raw_output": content,
        }
