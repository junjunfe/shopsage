from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class Product(BaseModel):
    id: str
    sku_id: str
    title: str
    category: Literal["laptop", "phone", "headphone"]
    brand: str
    description: str
    price: float
    list_price: float
    stock: int
    rating: float
    review_count: int
    attributes: dict[str, Any]
    tags: list[str]
    updated_at: str


class Preference(BaseModel):
    name: str
    weight: float = Field(ge=0, le=1)


class ConversationState(BaseModel):
    session_id: str
    user_id: str | None = None
    intent: str = "SEARCH"
    stage: str = "understanding"
    query_text: str | None = None
    category: str | None = None
    hard_filters: dict[str, Any] = Field(default_factory=dict)
    soft_preferences: list[Preference] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)
    sort_preference: str | None = None
    candidate_product_ids: list[str] = Field(default_factory=list)
    displayed_product_ids: list[str] = Field(default_factory=list)
    pending_question: dict[str, Any] | None = None
    turn_count: int = 0
    version: int = 0


class Route(BaseModel):
    intent: str
    confidence: float
    target_agent: str
    referenced_product_ids: list[str] = Field(default_factory=list)
    should_preserve_search_state: bool = True


class SearchHit(BaseModel):
    product: Product
    score: float
    match_reasons: list[str]
    snapshot_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AgentResponse(BaseModel):
    session_id: str
    intent: str
    stage: str
    text: str
    products: list[SearchHit] = Field(default_factory=list)
    comparison: list[dict[str, Any]] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    trace_id: str

