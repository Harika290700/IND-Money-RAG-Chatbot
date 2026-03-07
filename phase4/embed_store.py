"""Phase 4: Embed and upsert chunks into the same Chroma collection as Phase 1 (with phase4_* ids)."""

from phase1.embed_store import get_chroma_client, get_embedding_model

from .config import CHROMADB_ID_PREFIX, CHROMA_COLLECTION_NAME


def embed_and_store(chunks: list[tuple[str, dict]], collection_name: str = CHROMA_COLLECTION_NAME):
    """
    Embed Phase 4 chunks and upsert into Chroma with ids phase4_0, phase4_1, ...
    So Phase 4 adds to the same collection without overwriting Phase 1 chunks.
    """
    if not chunks:
        return
    model = get_embedding_model()
    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "IndMoney fund pages and static content"},
    )
    texts = [c[0] for c in chunks]
    metadatas = [c[1] for c in chunks]

    def flatten_meta(m: dict) -> dict:
        return {k: (str(v) if v is not None else "") for k, v in m.items()}

    metadatas = [flatten_meta(m) for m in metadatas]
    ids = [f"{CHROMADB_ID_PREFIX}_{i}" for i in range(len(texts))]
    embeddings = model.encode(texts, show_progress_bar=len(texts) > 5).tolist()
    collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    print(f"Upserted {len(texts)} Phase 4 chunks into collection '{collection_name}'.")
