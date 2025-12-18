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
def reorder_slides() -> str:
    """
    Reads retrieved slides from JSON file and reorders them based on storytelling flow.
    JSON must be a list of dicts with at least a 'Text' key.
    Returns a plain-text numbered list indicating the new order.
    """
    if not os.path.exists(SLIDES_PATH):
        return f"❌ No retrieved slides JSON found at {SLIDES_PATH}"

    with open(SLIDES_PATH, "r", encoding="utf-8") as f:
        slides = json.load(f)

    if not slides:
        return "⚠️ No slides provided in retrieved_slides.json."

    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = [
        {
            "role": "system",
            "content": (
                "You are a presentation structure expert. Given slides, reorder them for the "
                "best storytelling flow:\n"
                "1) Title 2) Intro/Agenda 3) Background/Problem 4) Methods/Approach "
                "5) Features/Implementation 6) Results/Case studies 7) Conclusion/Future work\n"
                "Do NOT remove any slide — just reorder.\n"
                "Return a plain-text numbered list with original slide identifiers if present."
            ),
        },
        {
            "role": "user",
            "content": "\n".join(
                f"Slide {i+1}: {s.get('Text','').strip().replace(chr(10), ' ')}"
                for i, s in enumerate(slides)
            ),
        },
    ]

    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=prompt,
        temperature=0.2,
    )

    return resp.choices[0].message.content.strip()
