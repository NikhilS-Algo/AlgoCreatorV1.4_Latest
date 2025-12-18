from fastmcp import tool
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import numpy as np
import faiss

# In-memory hybrid index
_model = SentenceTransformer("intfloat/e5-large-v2")
_corpus_embeddings = None
_index = None
_bm25 = None
_documents = []
_meta_info = []

def _build_indexes(slides: list[dict]):
    """Internal helper to (re)build semantic + BM25 indexes from slides."""
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
        # Create empty/no-op indexes
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
def build_hybrid_index(slides: list[dict]) -> str:
    """Build/refresh BM25 + semantic index from given slides."""
    _build_indexes(slides)
    return f"Index built for {len(_documents)} slides."

@tool
def hybrid_search(query: str, neg_keywords: list[str] | None = None, top_k: int = 5) -> list[dict]:
    """
    Hybrid BM25 + semantic search over slides. If neg_keywords provided, penalize matches.
    Returns top_k results each with text/meta/score.
    """
    if _bm25 is None or _index is None or not _documents:
        return [{"error": "Index not built. Call build_hybrid_index first."}]

    # BM25 positive
    bm25_scores = _bm25.get_scores(query.lower().split())
    bm25_norm = (bm25_scores - np.min(bm25_scores)) / (np.max(bm25_scores) - np.min(bm25_scores) + 1e-9)

    # Semantic positive
    q_emb = _model.encode([query], normalize_embeddings=True)
    sim_scores, _ = _index.search(q_emb, len(_documents))
    sim_norm = (sim_scores[0] - np.min(sim_scores[0])) / (np.max(sim_scores[0]) - np.min(sim_scores[0]) + 1e-9)

    alpha = 0.6
    pos_score = alpha * bm25_norm + (1 - alpha) * sim_norm

    if neg_keywords:
        # Penalize neg matches by blending their BM25 + semantic signals
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
