from __future__ import annotations

import re
from typing import Any

from config.model_provider import ModelProvider
from domain.constraints import SearchConstraints
from domain.models import ConversationState, Preference, Product, SearchHit
from repositories.database import Database


CATEGORY_WORDS = {"laptop": ["笔记本", "电脑", "轻薄本", "游戏本"], "phone": ["手机"], "headphone": ["耳机", "蓝牙耳机"]}
BRAND_ALIASES = {"苹果": "Apple", "apple": "Apple", "索尼": "索尼", "联想": "联想", "小米": "小米", "华为": "华为", "荣耀": "荣耀", "bose": "Bose", "oppo": "OPPO", "vivo": "vivo", "华硕": "华硕", "惠普": "惠普", "漫步者": "漫步者", "jbl": "JBL"}


class QueryUnderstandingService:
    """Convert shopping language into validated constraints and merge multi-turn updates."""

    def __init__(self, provider: ModelProvider | None = None) -> None:
        self.provider = provider or ModelProvider()

    def extract(self, text: str, state: ConversationState) -> dict[str, Any]:
        model_result = self.provider.complete(
            "Extract ecommerce search constraints from this user message. "
            "Use only catalog fields: price_max, memory_gb_min, weight_kg_max, "
            "battery_hours_min, brand, form, noise_cancelling. "
            f"Message: {text}",
            SearchConstraints,
        )
        if model_result:
            parsed = {"hard_filters": {}, "soft": [], "exclusions": [], "use_cases": model_result.use_cases}
            parsed["category"] = model_result.category
            for constraint in model_result.must:
                key = {"price": "price_max", "memory_gb": "memory_gb_min", "weight_kg": "weight_kg_max", "battery_hours": "battery_hours_min"}.get(constraint.field, constraint.field)
                parsed["hard_filters"][key] = constraint.value
            for constraint in model_result.must_not:
                if constraint.field == "brand": parsed["exclusions"].append(str(constraint.value))
            parsed["soft"] = [Preference(name=item.get("concept", ""), weight=float(item.get("weight", .7))) for item in model_result.should if item.get("concept")]
            return parsed
        low = text.lower()
        result: dict[str, Any] = {"hard_filters": {}, "soft": [], "exclusions": [], "use_cases": []}
        for category, words in CATEGORY_WORDS.items():
            if any(w in low for w in words): result["category"] = category
        prices = re.search(r"(\d+(?:\.\d+)?)\s*(?:元|块)?\s*(以内|以下|不超过|左右)", low)
        if prices:
            value = float(prices.group(1)); result["hard_filters"]["price_max"] = value * 10000 if "万" in prices.group(0) else value
        weight = re.search(r"(\d+(?:\.\d+)?)\s*(kg|公斤|千克)\s*(?:以内|以下)?", low)
        if weight: result["hard_filters"]["weight_kg_max"] = float(weight.group(1))
        memory = re.search(r"(\d+)\s*g(?:b)?\s*(?:内存|运行内存)?\s*(?:以上|起)", low)
        if memory: result["hard_filters"]["memory_gb_min"] = int(memory.group(1))
        battery = re.search(r"续航\s*(\d+)\s*(?:小时|h)\s*(?:以上|起)?", low)
        if battery: result["hard_filters"]["battery_hours_min"] = int(battery.group(1))
        for alias, brand in BRAND_ALIASES.items():
            if alias in low:
                if re.search(rf"(?:不要|不看|排除|除了).{{0,4}}{re.escape(alias)}", low): result["exclusions"].append(brand)
                else: result["hard_filters"]["brand"] = brand
        if "不要入耳" in low or "非入耳" in low: result["hard_filters"]["form_not"] = "入耳式"
        if "入耳式" in low and "不要" not in low: result["hard_filters"]["form"] = "入耳式"
        if "降噪" in low: result["hard_filters"]["noise_cancelling"] = True
        concepts = {"编程": "编程", "写代码": "编程", "剪视频": "剪视频", "便携": "便携", "轻薄": "便携", "拍照": "拍照", "操作简单": "操作简单", "续航": "长续航", "性能": "性能"}
        for word, concept in concepts.items():
            if word in low and concept not in [p.name for p in result["soft"]]: result["soft"].append(Preference(name=concept, weight=.8))
        if "便宜一点" in low and state.displayed_product_ids:
            result["relative_cheaper"] = True
        return result

    def merge(self, state: ConversationState, parsed: dict[str, Any]) -> ConversationState:
        if parsed.get("category") and state.category and parsed["category"] != state.category:
            state.hard_filters = {}; state.soft_preferences = []; state.exclusions = []; state.displayed_product_ids = []
        state.category = parsed.get("category", state.category)
        state.hard_filters.update(parsed["hard_filters"])
        state.exclusions = list(dict.fromkeys(state.exclusions + parsed["exclusions"]))
        prefs = {p.name: p for p in state.soft_preferences}
        prefs.update({p.name: p for p in parsed["soft"]})
        state.soft_preferences = list(prefs.values())
        if parsed.get("relative_cheaper"):
            current = state.hard_filters.get("price_max")
            state.hard_filters["price_max"] = round(current * .85, -1) if current else 4000
        return state


class RetrievalService:
    def __init__(self, db: Database): self.db = db

    @staticmethod
    def _passes(p: Product, state: ConversationState) -> bool:
        f = state.hard_filters
        if state.category and p.category != state.category: return False
        if p.brand in state.exclusions: return False
        if f.get("brand") and p.brand != f["brand"]: return False
        if p.price > f.get("price_max", float("inf")): return False
        if f.get("memory_gb_min") and p.attributes.get("memory_gb", 0) < f["memory_gb_min"]: return False
        if f.get("weight_kg_max") and p.attributes.get("weight_kg", float("inf")) > f["weight_kg_max"]: return False
        if f.get("battery_hours_min") and p.attributes.get("battery_hours", 0) < f["battery_hours_min"]: return False
        if f.get("form") and p.attributes.get("form") != f["form"]: return False
        if f.get("form_not") and p.attributes.get("form") == f["form_not"]: return False
        if f.get("noise_cancelling") is True and not p.attributes.get("noise_cancelling"): return False
        return p.stock > 0

    def search(self, state: ConversationState, query: str, top_k: int = 5) -> list[SearchHit]:
        lexical = self.db.lexical_scores(query)
        hits: list[SearchHit] = []
        for p in self.db.all_products():
            if not self._passes(p, state): continue
            reasons, semantic = [], 0.0
            haystack = " ".join([p.description, *p.tags]).lower()
            for pref in state.soft_preferences:
                if pref.name.lower() in haystack:
                    semantic += pref.weight; reasons.append(f"符合“{pref.name}”需求")
            if p.price <= state.hard_filters.get("price_max", -1): reasons.append(f"价格 ¥{p.price:.0f} 在预算内")
            if state.hard_filters.get("weight_kg_max"): reasons.append(f"重量 {p.attributes.get('weight_kg')}kg 符合要求")
            attribute = min(1, len(reasons) / max(1, len(state.soft_preferences) + len(state.hard_filters)))
            quality = (p.rating - 4) / 1
            popularity = min(1, p.review_count / 5000)
            lexical_score = lexical.get(p.id, 0)
            score = .30 * min(1, semantic) + .20 * lexical_score + .20 * attribute + .10 * quality + .10 * popularity + .10 * min(1, p.stock / 20)
            hits.append(SearchHit(product=p, score=round(score, 4), match_reasons=reasons or [f"{p.rating} 分，当前有货"]))
        hits.sort(key=lambda h: (-h.score, h.product.price, h.product.id))
        selected: list[SearchHit] = []
        for hit in hits:
            same_brand = sum(x.product.brand == hit.product.brand for x in selected)
            if same_brand < 2: selected.append(hit)
            if len(selected) == top_k: break
        return selected

    def relaxation(self, state: ConversationState) -> str:
        if "price_max" in state.hard_filters: return f"当前条件无结果。可将预算从 ¥{state.hard_filters['price_max']:.0f} 上调 20% 后重试。"
        if state.exclusions: return f"当前条件无结果。可先取消品牌排除：{state.exclusions[-1]}。"
        return "当前条件无结果，可以减少一个硬性条件后重试。"
