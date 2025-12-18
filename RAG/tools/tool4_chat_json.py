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
def chat_with_json(question: str) -> str:
    """
    Answers a question strictly based on the retrieved_slides.json content.
    If answer is not present in the context, politely say so.
    """
    if not os.path.exists(SLIDES_PATH):
        return f"❌ No retrieved slides JSON found at {SLIDES_PATH}"

    with open(SLIDES_PATH, "r", encoding="utf-8") as f:
        json_data = json.load(f)

    if not json_data:
        return "⚠️ No content available in retrieved_slides.json."

    client = OpenAI(api_key=OPENAI_API_KEY)
    context = f"Here is the content:\n\n{json.dumps(json_data, indent=2, ensure_ascii=False)}"

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": (
                "You are a helpful assistant that ONLY answers from the JSON context. "
                "If the answer is not clearly contained, reply: "
                "\"Sorry, but for this topic I don't have enough information in the provided JSON.\""
            )},
            {"role": "user", "content": context},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )
    return response.choices[0].message.content.strip()
