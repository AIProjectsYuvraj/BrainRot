from datetime import datetime, timezone

from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

SPLITTER = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)


def ingest(content_type: str, content: str) -> list[Document]:
    """Load content, chunk it, and attach metadata."""
    ingested_at = datetime.now(timezone.utc).isoformat()

    if content_type == "url":
        loader = WebBaseLoader(content)
        raw_docs = loader.load()
        source = content
    elif content_type == "pdf_path":
        loader = PyPDFLoader(content)
        raw_docs = loader.load()
        source = content
    elif content_type == "text":
        raw_docs = [Document(page_content=content, metadata={"source": "raw_text"})]
        source = "raw_text"
    else:
        raise ValueError(f"Unsupported content_type: {content_type}. Use 'url', 'pdf_path', or 'text'.")

    chunks = SPLITTER.split_documents(raw_docs)
    for chunk in chunks:
        chunk.metadata["source"] = source
        chunk.metadata["content_type"] = content_type
        chunk.metadata["ingested_at"] = ingested_at

    return chunks
