from openai import OpenAI
from typing import List, Dict, Optional, Any
from langchain_core.tools import tool

import requests
import json
import os
import numpy as np
import faiss
from datetime import datetime, timezone
from tempfile import NamedTemporaryFile
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from dotenv import load_dotenv

# --- Config ---
load_dotenv()  # load variables from .env

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# --- Constants ---
OUTPUT_DIR = "Output_files"
METADATA_DIR = "C:\\Users\\Administrator\\Desktop\\AlgoCreator_Chatbot\\AlgoCreator_Chatbot\\frontend\\data"
METADATA_FILE = "retrieval.json"

# JSON paths
SLIDES_PATH = os.path.join("tools", "JSON's", "retrieved_slides.json")
DATA_PATH = os.path.join(
    "RAG",
    "tools",
    "JSON's",
    "Updated_combined_content_With_Both(Slide_and_Presentation)_Summaries_V4.json"
)

# ===================== Retrieval Tools =====================

@tool
def retrieve_slides_v4(
    queries: List[Dict[str, object]],
    file_name: Optional[str] ,
    tags: Optional[List[List[str]]] = None,
    folder_names: Optional[List[str]] = None,
    # date_range: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Calls the slide retrieval API to fetch presentation slides as a PDF.
    Returns a dictionary containing PDF URL and optional metadata.
    """
    url = "http://localhost:8081/retrieval/v4/retrieve_slides"
    payload = {
        "queries": queries,
        "tags": tags if tags is not None else [[]],
        "folder_names": folder_names if folder_names is not None else [],
    }

    if file_name: 
        payload["file_name"] = file_name

    # if date_range:
    #     formatted_date_range = {}
    #     for key, value in date_range.items():
    #         if value:
    #             try:
    #                 dt_obj = datetime.fromisoformat(value.replace('Z', '+00:00'))
    #                 formatted_date_range[key] = dt_obj.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    #             except ValueError:
    #                 formatted_date_range[key] = value
    #         else:
    #             formatted_date_range[key] = None
    #     payload["date_range"] = formatted_date_range
    # else:
    payload["date_range"] = {
        "creation_start": "2000-01-01T00:00:00Z",
        "creation_end": "2025-12-31T23:59:59Z",
        "modification_start": "2000-01-01T00:00:00Z",
        "modification_end": "2025-12-31T23:59:59Z",
    }

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        return {
            "pdf_url": result.get("pdf_url", ""),
            "slide_metadata": result.get("slide_metadata", []),
            "num_results": len(result.get("slide_metadata", [])),
            "message": "✅ Slides retrieved successfully."
        }
    except requests.exceptions.RequestException as req_err:
        return {"error": f"Request error: {str(req_err)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

# Add this new tool to your tools.py file

@tool
def tool_load_retrieval_json() -> Dict[str, Any]:
    """
    Loads the retrieval.json metadata file to fetch pre-defined
    parameters like folder_names.
    """
    try:
        # Construct the full path to the metadata file
        file_path = os.path.join(METADATA_DIR, METADATA_FILE)
        
        if not os.path.exists(file_path):
            return {"error": f"Metadata file not found: {file_path}"}
            
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Extract the required keys. You can add more if needed.
        folder_names = data.get("folder_names")
        print("Fetched files from frontend folder: ", folder_names)
        
        if folder_names is None:
            return {"error": "'folder_names' key not found in retrieval.json"}

        return {
            "folder_names": folder_names,
            "message": "✅ Successfully loaded folder_names from retrieval.json"
        }

    except Exception as e:
        return {"error": f"❌ Failed to load or parse retrieval.json: {str(e)}"}

@tool
def save_retrieval_call_json(
    queries: List[Dict[str, object]],
    tags: Optional[List[List[str]]] = None, # Add tags to arguments for saving
    folder_names: Optional[List[str]] = None, # Add folder_names to arguments for saving
    file_name: Optional[str] = None,
    # date_range: Optional[Dict[str, str]] = None # Add date_range to arguments for saving
) -> str:
    """
    Combines queries with provided metadata (tags, folder_names, date_range)
    and saves the final payload to Retrieval_call.json. This tool is intended
    to serialize the exact payload that would be sent to the retrieval API.
    """
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        final_payload = {
            "queries": queries,
            "tags": tags if tags is not None else [[]],
            "folder_names": folder_names if folder_names is not None else [],
            # "date_range": date_range if date_range is not None else {
            #     "creation_start": datetime.utcnow().isoformat(timespec='seconds') + 'Z',
            #     "creation_end": datetime.utcnow().isoformat(timespec='seconds') + 'Z',
            #     "modification_start": datetime.utcnow().isoformat(timespec='seconds') + 'Z',
            #     "modification_end": datetime.utcnow().isoformat(timespec='seconds') + 'Z',
            # }
        }
        print("Saving in retrieval call json: ", final_payload)
        print("file name: ", file_name)

        output_path = os.path.join(OUTPUT_DIR, "Retrieval_call.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_payload, f, indent=4)

        # return f"✅ Retrieval_call.json saved successfully to {output_path}"
        return {
            "status": "success",
            "message": "✅ Retrieval_call.json saved successfully",
            "output_path": output_path
        }

    except Exception as e:
        return f"❌ Failed to save Retrieval_call.json: {str(e)}"


@tool
def load_and_retrieve_slides_from_file() -> Dict[str, Any]:
    """
    Loads Retrieval_call.json and calls the retrieval API endpoint.
    Returns PDF URL and metadata from the response.
    """
    try:
        file_path = os.path.join(OUTPUT_DIR, "Retrieval_call.json")
        if not os.path.exists(file_path):
            return {"error": f"❌ File not found: {file_path}"}
        with open(file_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        url = "http://localhost:8081/retrieval/v4/retrieve_slides"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        return {
            "pdf_url": result.get("pdf_url", ""),
            "slide_metadata": result.get("slide_metadata", []),
            "message": "✅ Slides retrieved successfully from file."
        }
    except Exception as e:

        return {"error": f"❌ Exception occurred during file load and retrieval: {str(e)}"}


# ===================== Integrated Advanced Tools =====================

@tool
def tool_reorder_slides(query:str, file_name: str) -> str:
    """
    Reorders slides for storytelling flow using GPT.
    Input: list of slides with 'Text'.
    Output: plain-text numbered reordering.
    """
    json_file = SLIDES_PATH

    if not os.path.exists(json_file):
        return {"error": f"❌ File not found: {json_file}"}
    
    with open(json_file, "r") as f:
        data = json.load(f)
    
    slides = []
    for section_idx, section in enumerate(data):
        for slide in section["results"]:
            slides.append({
                "slide": slide,
                "query": section["query"]
            })

    total_slides = len(slides)

    prompt = f"""
    You are a slide reordering assistant.
    There are {total_slides} slides in the presentation, numbered from 1 to {total_slides}.
    The user request is: "{query}".

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
    content = response.choices[0].message.content.strip()
    new_order = json.loads(content)

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

    if current_section:
        reordered_json.append(current_section)

    with open(json_file, "w") as f:
        json.dump(reordered_json, f, indent=2)
    
    url = "http://localhost:8000/retrieval/reorder_slides"
    payload = {
        "file_name": file_name,
        "new_order": new_order
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        return {
            "message": result.get("message", "Slides reordered successfully.")
        }
    except requests.exceptions.RequestException as req_err:
        return {"error": f"Request error: {str(req_err)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


@tool
def tool_build_context_from_presentations() -> str:
    """
    Loads and concatenates presentation summaries into a single string
    from the JSON summaries file.
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

    # return "\n\n".join(summaries)
    return {
        "summaries": summaries,
        "num_presentations": len(summaries)
    }


@tool
def tool_generate_query_outlines(user_query: str) -> List[str]:
    """
    Generates 3-7 concise keyword-rich query outlines
    based on a user query and presentation summaries.
    """
    all_summaries = tool_build_context_from_presentations()

    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"""
You are a slide-retrieval assistant.

User query: "{user_query}"
Summaries:
{all_summaries}

Task:
- Suggest 3-7 concise, keyword-rich query outlines (<=20 words).
- Prefer outlines that map to measurable slide content.
""".strip()

    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    content = resp.choices[0].message.content.strip()
    lines = [ln.strip() for ln in content.split("\n")]
    return [ln.lstrip("-•*0123456789. ").strip() for ln in lines if ln.strip()]


# ---- Hybrid Search ----
_model = SentenceTransformer("intfloat/e5-large-v2")
_corpus_embeddings = None
_index = None
_bm25 = None
_documents = []
_meta_info = []

def _build_indexes(slides: List[Dict[str, Any]]):
    """Internal helper: builds BM25 + semantic indexes for hybrid search."""
    global _corpus_embeddings, _index, _bm25, _documents, _meta_info
    _documents = []
    _meta_info = []
    for slide in slides or []:
        txt = slide.get("Text")
        if txt:
            _documents.append(txt)
            _meta_info.append({
                "pptx_name": slide.get("pptx_name", "Unknown"),
                "slide_number": slide.get("slide_number", "?"),
            })
    if not _documents:
        _corpus_embeddings = np.zeros((0, 1024), dtype="float32")
        _index = faiss.IndexFlatIP(1024)
        _bm25 = BM25Okapi([[]])
        return
    _corpus_embeddings = _model.encode(_documents, normalize_embeddings=True)
    _index = faiss.IndexFlatIP(_corpus_embeddings.shape[1])
    _index.add(_corpus_embeddings)
    tokenized = [doc.lower().split() for doc in _documents]
    _bm25 = BM25Okapi(tokenized)

@tool
def tool_build_hybrid_index(slides: List[Dict[str, Any]]) -> str:
    """
    Builds or refreshes the hybrid BM25 + semantic index
    from a given list of slides.
    """
    _build_indexes(slides)
    # return f"Index built for {len(_documents)} slides."
    return {
        "message": "Hybrid index built",
        "documents": len(_documents)
    }

@tool
def tool_hybrid_search(query: str, neg_keywords: Optional[List[str]] = None, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Performs hybrid BM25 + semantic search over slides.
    Optionally penalizes slides containing negative keywords.
    Returns the top-k ranked results.
    """
    if _bm25 is None or _index is None or not _documents:
        return [{"error": "Index not built. Call tool_build_hybrid_index first."}]

    bm25_scores = _bm25.get_scores(query.lower().split())
    bm25_norm = (bm25_scores - np.min(bm25_scores)) / (np.max(bm25_scores) - np.min(bm25_scores) + 1e-9)

    q_emb = _model.encode([query], normalize_embeddings=True)
    sim_scores, _ = _index.search(q_emb, len(_documents))
    sim_norm = (sim_scores[0] - np.min(sim_scores[0])) / (np.max(sim_scores[0]) - np.min(sim_scores[0]) + 1e-9)

    alpha = 0.6
    pos_score = alpha * bm25_norm + (1 - alpha) * sim_norm

    if neg_keywords:
        neg_embs = _model.encode(neg_keywords, normalize_embeddings=True)
        mean_neg = np.mean(neg_embs, axis=0, keepdims=True)
        neg_scores, _ = _index.search(mean_neg, len(_documents))
        neg_norm = (neg_scores[0] - np.min(neg_scores[0])) / (np.max(neg_scores[0]) - np.min(neg_scores[0]) + 1e-9)

        bm25_neg_all = [_bm25.get_scores(k.lower().split()) for k in neg_keywords]
        bm25_neg = np.mean(bm25_neg_all, axis=0)
        bm25_neg_norm = (bm25_neg - np.min(bm25_neg)) / (np.max(bm25_neg) - np.min(bm25_neg) + 1e-9)

        beta = 0.7
        final_scores = beta * pos_score - (1 - beta) * (alpha * bm25_neg_norm + (1 - alpha) * neg_norm)
    else:
        final_scores = pos_score

    ranked = sorted(
        [{"text": t, "meta": m, "score": float(s)} for t, m, s in zip(_documents, _meta_info, final_scores)],
        key=lambda x: x["score"],
        reverse=True,
    )
    return ranked[:max(1, int(top_k))]


@tool
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
    # return response.choices[0].message.content.strip()
    return {
        "answer": response.choices[0].message.content.strip()
    }


@tool
def tool_get_presentation_instructions() -> str:
    """
    Generates a clear, concise ~5-minute presentation guide
    from retrieved_slides.json by grouping and sequencing slides.
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
    # return resp.choices[0].message.content.strip()
    return {
        "instructions": resp.choices[0].message.content.strip()
    }


# =========================== Toolkit Registry ===========================
toolkit = [
    retrieve_slides_v4,
    save_retrieval_call_json,
    load_and_retrieve_slides_from_file,
    tool_load_retrieval_json, 
    tool_reorder_slides,
    tool_build_context_from_presentations,
    tool_generate_query_outlines,
    tool_build_hybrid_index,
    tool_hybrid_search,
    tool_chat_with_json,
    tool_get_presentation_instructions
]
