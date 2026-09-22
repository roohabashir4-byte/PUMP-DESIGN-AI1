from __future__ import annotations

from pathlib import Path
import pickle

from standards.rag_store import RAGStore, INDEX


def build() -> str:
    store = RAGStore()
    try:
        import faiss
        vectors = store.matrix.toarray().astype("float32")
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        INDEX.mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, str(INDEX / "chunks.faiss"))
        return f"FAISS index built: {len(store.chunks)} chunks"
    except ImportError:
        return "FAISS is not installed; TF-IDF fallback index was built. Install faiss-cpu and rerun this builder for the production FAISS index."


if __name__ == "__main__":
    print(build())
