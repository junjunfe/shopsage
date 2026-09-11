"""One-question clarification chosen by candidate impact and business relevance."""
from __future__ import annotations

from domain.models import ConversationState


class ClarificationService:
    def select_question(self, state: ConversationState, candidate_count: int) -> dict | None:
        if not state.category:
            return {"field": "category", "question": "你想找哪类商品？", "options": ["笔记本", "手机", "蓝牙耳机"]}
        if candidate_count > 15 and "price_max" not in state.hard_filters:
            return {"field": "price_max", "question": "你的预算大约是多少？", "options": ["2000 元以内", "5000 元以内", "8000 元以内"]}
        if state.category == "laptop" and candidate_count > 10 and not state.soft_preferences:
            return {"field": "priority", "question": "更看重便携、性能，还是续航？", "options": ["便携", "性能", "续航"]}
        return None

