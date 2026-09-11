"""Prevents candidate-outside facts from being returned as product facts."""
from __future__ import annotations

from domain.models import AgentResponse, Product


class ResponseValidator:
    def validate(self, response: AgentResponse, snapshots: list[Product]) -> None:
        allowed = {product.id for product in snapshots} | {e for e in response.evidence_ids if e.startswith("knowledge:")}
        if not set(response.evidence_ids).issubset(allowed):
            raise ValueError("response contains evidence outside current snapshots")
        for hit in response.products:
            if hit.product.id not in {p.id for p in snapshots}:
                raise ValueError("response contains a product outside current snapshots")
