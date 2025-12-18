import json
import os
from openai import OpenAI

OPENAI_API_KEY = "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"
OPENAI_MODEL = "gpt-4o-mini"
SLIDES_PATH = "C:\\Users\\Administrator\\Desktop\\AlgoCreator_Chatbot\\AlgoCreator_Chatbot\\RAG\\tools\\JSON's\\retrieved_slides.json"

def tool_chat_with_json(question: str) -> str:
    """
    Answers a user question strictly from the retrieved_slides.json file.
    If the answer is not present, politely indicate lack of information.
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

def reorder_slides_with_llm(user_query: str, json_file: str = "slides.json") -> list[dict]:
    """
    Reads the JSON of slides, flattens them, reorders based on a natural language query using GPT-4o-mini,
    and returns the reordered flat JSON list.

    :param user_query: str, natural language request (e.g. "move slide 3 before slide 2")
    :param json_file: str, path to JSON file storing slides
    :return: reordered list of dicts (flattened)
    """

    # Step 1: Load JSON
    with open(json_file, "r") as f:
        data = json.load(f)

    # Step 2: Flatten all slides into a single list
    slides = []
    for section_idx, section in enumerate(data):
        for slide in section["results"]:
            slides.append({
                "slide": slide,
                "query": section["query"]
            })

    total_slides = len(slides)

    # Step 3: Ask LLM for new order
    prompt = f"""
    You are a slide reordering assistant.
    There are {total_slides} slides in the presentation, numbered from 1 to {total_slides}.
    The user request is: "{user_query}".

    Please output ONLY the new slide order as a JSON list of integers (0-based indices).
    Example: [0, 2, 1, 3]
    """

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You only return valid JSON arrays of integers, no explanation."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    # return response.choices[0].message
    content = response.choices[0].message.content.strip()
    # return content
    new_order = json.loads(content)
    print(new_order)

    return new_order

    # Step 4: Apply order
    reordered_json = []
    current_section = None
    current_query = None

    for idx in new_order:
        slide_entry = slides[idx]
        slide = slide_entry["slide"]
        query = slide_entry["query"]

        if query != current_query:
            # Start a new section
            if current_section:
                reordered_json.append(current_section)
            current_section = {"query": query, "results": [slide]}
            current_query = query
        else:
            current_section["results"].append(slide)

    # Append the last section
    if current_section:
        reordered_json.append(current_section)

    # Step 5: Save reordered JSON
    with open("slides_reordered.json", "w") as f:
        json.dump(reordered_json, f, indent=2)

    return reordered_json


if __name__ == "__main__":
    path = "C:\\Users\\Administrator\\Desktop\\AlgoCreator_Chatbot\\AlgoCreator_Chatbot\\RAG\\tools\\JSON's\\retrieved_slides.json"
    query = input("Enter you query: ")
    while (query != ''):
        reordered_slides = reorder_slides_with_llm(query, path)
        print(reordered_slides)
        query = input("Enter you query: ")
    # reordered_slides = reorder_slides_with_llm(query, path)
    # print(reordered_slides)

