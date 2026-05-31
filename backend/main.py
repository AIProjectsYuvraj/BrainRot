from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.ingestor import ingest
from backend.models import BrainRotResponse, ChatRequest, IngestRequest, IngestResponse
from backend.rag_chain import chat
from backend.vectorstore import add_documents, get_document_count, get_sources_summary, reset_collection

load_dotenv()

app = FastAPI(title="BrainRot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/ingest", response_model=IngestResponse)
def ingest_content(request: IngestRequest) -> IngestResponse:
    try:
        if request.content_type == "pdf_path":
            path = Path(request.content)
            if not path.exists():
                raise HTTPException(status_code=400, detail=f"PDF file not found: {request.content}")

        docs = ingest(request.content_type, request.content)
        if not docs:
            return IngestResponse(
                success=False,
                chunks_created=0,
                message="No content could be extracted from the provided input.",
            )

        add_documents(docs)
        return IngestResponse(
            success=True,
            chunks_created=len(docs),
            message=f"Successfully ingested {len(docs)} chunks.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        return IngestResponse(success=False, chunks_created=0, message=f"Ingestion failed: {exc}")


@app.post("/chat", response_model=BrainRotResponse)
def chat_endpoint(request: ChatRequest) -> BrainRotResponse:
    if request.personality not in ("brutal", "hype", "tired"):
        raise HTTPException(status_code=400, detail="personality must be 'brutal', 'hype', or 'tired'")

    try:
        return chat(request.question, request.personality, request.session_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}") from exc


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "documents_stored": get_document_count()}


@app.get("/sources")
def sources() -> list[dict]:
    return get_sources_summary()


@app.delete("/reset")
def reset() -> dict:
    reset_collection()
    return {"status": "ok", "message": "Collection cleared."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
