from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    content_type: str  # "url", "pdf_path", or "text"
    content: str  # the URL, file path, or raw text


class ChatRequest(BaseModel):
    question: str
    personality: str  # "brutal", "hype", or "tired"
    session_id: str  # for conversation memory


class BrainRotResponse(BaseModel):
    answer: str
    bonus_type: str = Field(description='One of "follow_up", "hot_take", or "related_fact"')
    bonus_content: str
    sources: list[str] = Field(description="Source URLs or filenames used")


class IngestResponse(BaseModel):
    success: bool
    chunks_created: int
    message: str
