"""Explainable second-stage ranking and result diversity control."""
from __future__ import annotations

from domain.models import ConversationState, SearchHit


class RankingService:
    def rank(self, candidates, state: ConversationState) -> list[SearchHit]:
        hits: list[SearchHit] = []
        for product, rrf, lexical, semantic in candidates:
            reasons: list[str] = []
            preference_matches = 0
            haystack = " ".join([product.description, *product.tags])
            for preference in state.soft_preferences:
                if preference.name in haystack:
                    preference_matches += 1
                    reasons.append(f"符合“{preference.name}”需求")
            if "price_max" in state.hard_filters:
                reasons.append(f"价格 ¥{product.price:.0f} 在预算内")
            if "weight_kg_max" in state.hard_filters:
                reasons.append(f"重量 {product.attributes.get('weight_kg')}kg 符合要求")
            attribute = preference_matches / max(1, len(state.soft_preferences))
            quality = max(0, min(1, (product.rating - 4) / .9))
            popularity = min(1, product.review_count / 5000)
            inventory = min(1, product.stock / 20)
            score = .20 * min(1, rrf * 100) + .20 * semantic + .15 * lexical + .20 * attribute + .10 * quality + .10 * popularity + .05 * inventory
            hits.append(SearchHit(product=product, score=round(score, 4), match_reasons=reasons or [f"{product.rating} 分，当前有货"]))
        return sorted(hits, key=lambda hit: (-hit.score, hit.product.price, hit.product.id))

    def diversify(self, hits: list[SearchHit], top_k: int) -> list[SearchHit]:
        selected: list[SearchHit] = []
        for hit in hits:
            if sum(x.product.brand == hit.product.brand for x in selected) < 2:
                selected.append(hit)
            if len(selected) >= top_k:
                break
        return selected

