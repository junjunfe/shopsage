from typing import Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str | None = None
    user_id: str | None = None
    message: str = Field(min_length=1, max_length=2000)
    stream: bool = False


class SearchRequest(BaseModel):
    query: str = ""
    category: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    top_k: int = Field(default=5, ge=1, le=20)


class CompareRequest(BaseModel):
    product_ids: list[str] = Field(min_length=2, max_length=4)


class EventRequest(BaseModel):
    request_id: str
    event_type: str
    product_id: str
    session_id: str | None = None
    user_id: str | None = None

