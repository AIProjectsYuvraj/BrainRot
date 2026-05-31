from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

COLLECTION_NAME = "brainrot_collection"
PERSIST_DIR = "./chroma_db"

_embeddings = None
_vectorstore = None


def _get_embeddings() -> OpenAIEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return _embeddings


def _get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=_get_embeddings(),
            persist_directory=PERSIST_DIR,
        )
    return _vectorstore


def add_documents(docs: list[Document]) -> None:
    store = _get_vectorstore()
    store.add_documents(docs)


def get_retriever(k: int = 4):
    store = _get_vectorstore()
    return store.as_retriever(search_kwargs={"k": k})


def get_document_count() -> int:
    store = _get_vectorstore()
    return store._collection.count()


def get_sources_summary() -> list[dict]:
    store = _get_vectorstore()
    result = store._collection.get(include=["metadatas"])
    metadatas = result.get("metadatas") or []

    sources: dict[str, dict] = {}
    for meta in metadatas:
        if not meta:
            continue
        source = meta.get("source", "unknown")
        ingested_at = meta.get("ingested_at", "unknown")
        key = f"{source}|{ingested_at}"
        if key not in sources:
            sources[key] = {
                "source": source,
                "ingested_at": ingested_at,
                "content_type": meta.get("content_type", "unknown"),
                "chunk_count": 0,
            }
        sources[key]["chunk_count"] += 1

    return sorted(sources.values(), key=lambda s: s["ingested_at"], reverse=True)


def reset_collection() -> None:
    global _vectorstore
    store = _get_vectorstore()
    data = store._collection.get()
    ids = data.get("ids") or []
    if ids:
        store._collection.delete(ids=ids)
    _vectorstore = None
