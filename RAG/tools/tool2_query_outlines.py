import json
import os
from fastmcp import tool
from openai import OpenAI
from ...config import OPENAI_API_KEY, OPENAI_MODEL

# Absolute/relative JSON path
DATA_PATH = os.path.join(
    "RAG",
    "tools",
    "JSON's",
    "Updated_combined_content_With_Both(Slide_and_Presentation)_Summaries_V4.json"
)


@tool
def build_context_from_presentations() -> str:
    """
    Loads summaries from the JSON file and concatenates them into a single string.
    JSON format: list of objects with keys ['pptx_name', 'Presentation_Summary'].
    """
    if not os.path.exists(DATA_PATH):
        return f"❌ No presentation JSON file found at {DATA_PATH}"

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        json_data = json.load(f)

    summaries = []
    for file_obj in json_data or []:
        name = file_obj.get("pptx_name", "Unknown")
        summ = (file_obj.get("Presentation_Summary") or "").strip()
        if summ:
            summaries.append(f"{name}:\n{summ}")

    return "\n\n".join(summaries)


@tool
def generate_query_outlines(user_query: str) -> list[str]:
    """
    Generates 3–7 possible sub-topic query outlines based on a user_query and
    presentation summaries stored in the JSON file.
    Returns a list of concise outline strings.
    """
    all_summaries = build_context_from_presentations()

    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"""
You are a slide-retrieval assistant.

You are given:
1) A user query: "{user_query}"
2) A set of presentation summaries.

Task:
- Suggest 3–7 concise, keyword-rich query outlines for retrieving relevant slides.
- Each outline should be short and focused (<= 20 words).
- Prefer outlines that map to measurable slide content.

---
Presentation Summaries:
{all_summaries}
---
Generate bullet points only:
""".strip()

    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    content = resp.choices[0].message.content.strip()
    lines = [ln.strip() for ln in content.split("\n")]
    return [ln.lstrip("-•*0123456789. ").strip() for ln in lines if ln.strip()]
