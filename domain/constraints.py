"""Validated DSL exchanged between query understanding and retrieval."""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class Constraint(BaseModel):
    field: str
    op: Literal["eq", "lte", "gte", "neq"]
    value: Any
    unit: str | None = None


class SearchConstraints(BaseModel):
    category: str | None = None
    must: list[Constraint] = Field(default_factory=list)
    should: list[dict[str, Any]] = Field(default_factory=list)
    must_not: list[Constraint] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)
    sort: Literal["price_asc", "rating_desc"] | None = None
    ambiguities: list[str] = Field(default_factory=list)

