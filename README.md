# BrainRot

BrainRot is a personality-driven RAG chatbot that ingests URLs, PDFs, or raw text and answers questions with one of three distinct AI personas — each delivering accurate answers wrapped in character-specific roasts, hype, or deadpan exhaustion. Every response includes a structured bonus (follow-up question, hot take, or related fact) and cites the sources it retrieved.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Streamlit Frontend                          │
│  (frontend/app.py)                                              │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │ Sidebar  │  │ Chat UI      │  │ Bonus boxes + Sources     │  │
│  │ Ingest   │  │ st.chat_msg  │  │ (follow-up / hot take)    │  │
│  └────┬─────┘  └──────┬───────┘  └───────────────────────────┘  │
└───────┼───────────────┼─────────────────────────────────────────┘
        │  HTTP         │  HTTP
        ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                             │
│  (backend/main.py)                                              │
│  POST /ingest  POST /chat  GET /health  GET /sources  DELETE /reset
└───────┬─────────────────────────────┬───────────────────────────┘
        │                             │
        ▼                             ▼
┌───────────────┐            ┌────────────────────────────────────┐
│  ingestor.py  │            │  rag_chain.py (LangGraph)          │
│  WebBaseLoader│            │  ┌──────────┐    ┌──────────────┐  │
│  PyPDFLoader  │            │  │ retrieve │───▶│ agent (GPT-4o│  │
│  TextSplitter │            │  │  node    │    │ structured)  │  │
└───────┬───────┘            │  └────┬─────┘    └──────────────┘  │
        │                    │       │         MemorySaver          │
        ▼                    │       ▼                              │
┌───────────────┐            │  vectorstore.py                    │
│ vectorstore.py│◀───────────┤  ChromaDB (./chroma_db)            │
│ ChromaDB      │            │  text-embedding-3-small            │
│ Embeddings    │            └────────────────────────────────────┘
└───────────────┘                          │
                                           ▼
                                    LangSmith Tracing
```

## Run Locally

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env` and add your API keys:

```
OPENAI_API_KEY=sk-...
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=brainrot
```

### 3. Start the backend

```bash
uvicorn backend.main:app --reload --port 8000
```

### 4. Start the frontend (separate terminal)

```bash
streamlit run frontend/app.py
```

Open the Streamlit URL (usually `http://localhost:8501`), ingest content via the sidebar, pick a personality, and start chatting.

## Example Questions

After ingesting a technical blog post or PDF:

- "What are the main arguments in this document?"
- "Summarize the key takeaways in three bullet points."
- "What does the author say about [specific topic]?"
- "How does this compare to industry best practices?"
- "What are the limitations mentioned?"

After ingesting raw text about a project:

- "What tech stack is being used?"
- "What are the open questions or TODOs?"
- "Explain the architecture described here."

## Tech Stack

| Technology | Why |
|---|---|
| **FastAPI** | Lightweight async API server with automatic OpenAPI docs |
| **Streamlit** | Rapid chat UI with session state and file upload support |
| **LangChain** | Unified interface for loaders, embeddings, and LLM calls |
| **LangGraph** | Stateful RAG pipeline with checkpointed conversation memory |
| **ChromaDB** | Persistent local vector store — survives restarts |
| **OpenAI GPT-4o** | Strong reasoning with native structured output support |
| **text-embedding-3-small** | Fast, cost-effective embeddings for retrieval |
| **LangSmith** | End-to-end tracing of every chat turn for debugging |
