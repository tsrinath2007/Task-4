"""
src/memory/embeddings.py — Embedding Generation via SentenceTransformers

Uses sentence-transformers/all-MiniLM-L6-v2 (local CPU, free, no API key).
Configurable via EMBEDDING_BACKEND environment variable.
"""

import os
import numpy as np

_MODEL = None


def get_embedding_model():
    """
    Lazy-loads the SentenceTransformer model on CPU.
    """
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        backend = os.getenv("EMBEDDING_BACKEND", "sentence-transformers/all-MiniLM-L6-v2")
        print(f"Loading embedding model: {backend}...")
        _MODEL = SentenceTransformer(backend)
    return _MODEL


def embed_texts(texts, batch_size=64, show_progress_bar=False):
    """
    Encodes a list of strings into a numpy array of normalized embedding vectors.
    """
    model = get_embedding_model()
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=show_progress_bar,
        normalize_embeddings=True
    )
    return np.array(embeddings, dtype=np.float32)


def embed_query(text):
    """
    Encodes a single query string into a normalized 1D embedding vector.
    """
    model = get_embedding_model()
    emb = model.encode([text], normalize_embeddings=True)[0]
    return np.array(emb, dtype=np.float32)
