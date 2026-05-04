import faiss
import numpy as np
from typing import List, Tuple
from pathlib import Path
from backend.embedding import embed_texts, embed_query

INDEX_DIR = Path("data/faiss_index")
INDEX_DIR.mkdir(parents=True, exist_ok=True)

class VectorStore:
    def __init__(self):
        self.index = None
        self.chunks: List[str] = []
        self.dimension = 384  # all-MiniLM-L6-v2 output dim

    def build(self, chunks: List[str]):
        """Embed chunks and build FAISS index."""
        self.chunks = chunks
        embeddings = embed_texts(chunks).astype("float32")

        self.index = faiss.IndexFlatL2(self.dimension)
        self.index.add(embeddings)
        print(f"[VectorStore] Index built with {len(chunks)} chunks.")

    def search(self, query: str, top_k: int = 5) -> List[str]:
        """Search top_k relevant chunks for a query."""
        if self.index is None or len(self.chunks) == 0:
            return []

        query_vec = embed_query(query).astype("float32").reshape(1, -1)
        distances, indices = self.index.search(query_vec, min(top_k, len(self.chunks)))

        results = [self.chunks[i] for i in indices[0] if i < len(self.chunks)]
        return results

    def save(self, name: str = "meeting"):
        faiss.write_index(self.index, str(INDEX_DIR / f"{name}.faiss"))
        with open(INDEX_DIR / f"{name}_chunks.txt", "w", encoding="utf-8") as f:
            f.write("\n---CHUNK---\n".join(self.chunks))
        print(f"[VectorStore] Saved index: {name}")

    def load(self, name: str = "meeting"):
        index_path = INDEX_DIR / f"{name}.faiss"
        chunks_path = INDEX_DIR / f"{name}_chunks.txt"
        if index_path.exists() and chunks_path.exists():
            self.index = faiss.read_index(str(index_path))
            with open(chunks_path, "r", encoding="utf-8") as f:
                self.chunks = f.read().split("\n---CHUNK---\n")
            print(f"[VectorStore] Loaded index: {name} ({len(self.chunks)} chunks)")
        else:
            print("[VectorStore] No saved index found.")


def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks by word count."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks
