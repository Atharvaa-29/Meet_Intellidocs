from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np

MODEL_NAME = "all-MiniLM-L6-v2"

_embedder = None

def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        print(f"[Embedding] Loading model: {MODEL_NAME}")
        _embedder = SentenceTransformer(MODEL_NAME)
    return _embedder


def embed_texts(texts: List[str]) -> np.ndarray:
    """Convert list of strings to numpy array of embeddings."""
    embedder = get_embedder()
    embeddings = embedder.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return embeddings


def embed_query(query: str) -> np.ndarray:
    """Embed a single query string."""
    return embed_texts([query])[0]
