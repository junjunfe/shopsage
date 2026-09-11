"""Deterministic BM25-style + local vector recall with Reciprocal Rank Fusion."""
from __future__ import annotations

import hashlib
import math
from collections import defaultdict

from domain.models import ConversationState, Product
from repositories.database import Database
from services.search import RetrievalService


def _vector(text: str, dimensions: int = 96) -> list[float]:
    values = [0.0] * dimensions
    normalized = "".join(text.lower().split())
    for index in range(max(0, len(normalized) - 1)):
        token = normalized[index:index + 2]
        bucket = int(hashlib.sha256(token.encode()).hexdigest(), 16) % dimensions
        values[bucket] += 1.0
    length = math.sqrt(sum(x * x for x in values)) or 1.0
    return [x / length for x in values]


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


class HybridRetrievalService:
    """Uses local hashed embeddings so the project works without external model keys."""
    def __init__(self, db: Database):
        self.db, self.filters = db, RetrievalService(db)

    def recall(self, state: ConversationState, query: str, limit: int = 30) -> list[tuple[Product, float, float, float]]:
        eligible = [p for p in self.db.all_products() if self.filters._passes(p, state)]
        lexical = self.db.lexical_scores(query)
        query_vector = _vector(" ".join([query, *[p.name for p in state.soft_preferences]]))
        semantic = {
            p.id: _cosine(query_vector, _vector(" ".join([p.title, p.description, *p.tags])))
            for p in eligible
        }
        lexical_rank = sorted(eligible, key=lambda p: lexical.get(p.id, 0), reverse=True)
        semantic_rank = sorted(eligible, key=lambda p: semantic[p.id], reverse=True)
        rrf: dict[str, float] = defaultdict(float)
        for ranked in (lexical_rank, semantic_rank):
            for rank, product in enumerate(ranked, 1):
                rrf[product.id] += 1 / (60 + rank)
        by_id = {p.id: p for p in eligible}
        return [(by_id[pid], rrf[pid], lexical.get(pid, 0), semantic[pid]) for pid in sorted(rrf, key=rrf.get, reverse=True)[:limit]]

