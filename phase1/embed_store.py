"""Phase 1: Embed chunks and store in Chroma."""

from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from .config import CHROMA_COLLECTION_NAME, CHROMA_PERSIST_DIR


def get_embedding_model():
    """Lazy-load a small, fast embedding model."""
    return SentenceTransformer("all-MiniLM-L6-v2")


def get_chroma_client():
    """Chroma client with persistence. Works with chromadb 0.4.x and 1.5.x+."""
    path = Path(CHROMA_PERSIST_DIR)
    path.mkdir(parents=True, exist_ok=True)
    try:
        from chromadb.config import Settings
        return chromadb.PersistentClient(
            path=str(path),
            settings=Settings(anonymized_telemetry=False),
        )
    except (ImportError, TypeError, Exception):
        return chromadb.PersistentClient(path=str(path))


def embed_and_store(chunks: list[tuple[str, dict]], collection_name: str = CHROMA_COLLECTION_NAME):
    """
    Embed each chunk text and store in Chroma. Replaces the collection so the vector store
    matches the current scraped data (no stale chunks from previous runs).
    chunks: list of (text, metadata). Metadata must include source_url for answers.
    """
    if not chunks:
        return
    model = get_embedding_model()
    client = get_chroma_client()
    try:
        client.delete_collection(name=collection_name)
    except Exception:
        pass
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "IndMoney fund pages and static content"},
    )

    texts = [c[0] for c in chunks]
    metadatas = [c[1] for c in chunks]

    def flatten_meta(m: dict) -> dict:
        return {k: (str(v) if v is not None else "") for k, v in m.items()}

    metadatas = [flatten_meta(m) for m in metadatas]

    ids = [f"chunk_{i}" for i in range(len(texts))]
    embeddings = model.encode(texts, show_progress_bar=len(texts) > 5).tolist()

    collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    print(f"Stored {len(texts)} chunks in collection '{collection_name}'.")


def get_collection(collection_name: str = CHROMA_COLLECTION_NAME):
    """Get existing collection (for querying)."""
    client = get_chroma_client()
    return client.get_collection(name=collection_name)


def query_collection(
    query: str,
    n_results: int = 5,
    collection_name: str = CHROMA_COLLECTION_NAME,
    where: dict | None = None,
):
    """
    Run vector search. Returns list of (document, metadata, distance).
    metadata contains source_url for each chunk.
    On any error (missing collection, sqlite, etc.) returns [] so the app can fall back to scraped_funds.json.
    """
    try:
        model = get_embedding_model()
        client = get_chroma_client()
        collection = client.get_collection(name=collection_name)
        q_embedding = model.encode([query]).tolist()
        res = collection.query(
            query_embeddings=q_embedding,
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        docs = res["documents"][0] if res["documents"] else []
        metas = res["metadatas"][0] if res["metadatas"] else []
        dists = res["distances"][0] if res["distances"] else []
        return list(zip(docs, metas, dists))
    except Exception:
        return []
