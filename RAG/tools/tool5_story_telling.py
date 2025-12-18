import json
import os
from fastmcp import tool
from openai import OpenAI
from ...config import OPENAI_API_KEY, OPENAI_MODEL

# Path to retrieved slides JSON
SLIDES_PATH = os.path.join(
    "RAG",
    "tools",
    "JSON's",
    "retrieved_slides.json"
)


@tool
def get_presentation_instructions() -> str:
    """
    Generates a clear, concise ~5-minute presentation guide from retrieved_slides.json.
    Groups related slides and gives sequence instructions only (no style advice).
    """
    if not os.path.exists(SLIDES_PATH):
        return f"❌ No retrieved slides JSON found at {SLIDES_PATH}"

    with open(SLIDES_PATH, "r", encoding="utf-8") as f:
        slides_json = json.load(f)

    if not slides_json:
        return "⚠️ No slides available in retrieved_slides.json."

    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"""
You are an expert presentation coach.

Below is a presentation in JSON.
Task:
1) Group related slides into thematic clusters.
2) For each group, give step-by-step guidance to present them in ~5 minutes total.
3) Focus ONLY on sequence and content (no delivery tips or style).

---
Presentation JSON:
{json.dumps(slides_json, indent=2, ensure_ascii=False)}
""".strip()

    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1000,
    )
    return resp.choices[0].message.content.strip()
