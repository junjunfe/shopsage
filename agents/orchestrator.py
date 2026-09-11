from __future__ import annotations

import re
import uuid

from domain.models import AgentResponse, ConversationState, Route
from repositories.database import Database
from services.search import QueryUnderstandingService, RetrievalService


class Orchestrator:
    def __init__(self, db: Database):
        self.db, self.understanding, self.retrieval = db, QueryUnderstandingService(), RetrievalService(db)

    def route(self, message: str, state: ConversationState) -> Route:
        low = message.lower()
        if any(x in low for x in ["重新开始", "清空条件", "重置"]): return Route(intent="RESET", confidence=1, target_agent="orchestrator", should_preserve_search_state=False)
        if any(x in low for x in ["比较", "对比", "哪个好"]): return Route(intent="COMPARE", confidence=.98, target_agent="comparison")
        if any(x in low for x in ["是什么意思", "什么意思", "能用吗", "是什么"]): return Route(intent="PRODUCT_QA", confidence=.9, target_agent="product_qa")
        if state.displayed_product_ids and any(x in low for x in ["一点", "不要", "改成", "只看", "以上", "以下"]): return Route(intent="REFINE", confidence=.9, target_agent="product_search")
        return Route(intent="SEARCH", confidence=.8, target_agent="product_search")

    def handle(self, message: str, session_id: str, user_id: str | None = None) -> AgentResponse:
        state = self.db.load_state(session_id) or ConversationState(session_id=session_id, user_id=user_id)
        state.turn_count += 1; state.query_text = message
        route = self.route(message, state); state.intent = route.intent
        trace = str(uuid.uuid4())
        if route.intent == "RESET":
            state = ConversationState(session_id=session_id, user_id=user_id, turn_count=state.turn_count, intent="RESET")
            self.db.save_state(state)
            return AgentResponse(session_id=session_id, intent="RESET", stage="understanding", text="已清空条件。你这次想买什么？", trace_id=trace)
        if route.intent == "COMPARE":
            response = self._compare(message, state, trace); self.db.save_state(state); return response
        if route.intent == "PRODUCT_QA":
            response = self._qa(message, state, trace); self.db.save_state(state); return response
        parsed = self.understanding.extract(message, state)
        state = self.understanding.merge(state, parsed)
        if not state.category:
            state.stage = "clarifying"; state.pending_question = {"field": "category"}; self.db.save_state(state)
            return AgentResponse(session_id=session_id, intent=route.intent, stage=state.stage, text="你想找哪类商品？", suggestions=["笔记本", "手机", "蓝牙耳机"], trace_id=trace)
        state.stage = "retrieving"; hits = self.retrieval.search(state, message)
        if not hits:
            state.stage = "recovering"; self.db.save_state(state)
            return AgentResponse(session_id=session_id, intent=route.intent, stage=state.stage, text=self.retrieval.relaxation(state), suggestions=["提高预算", "减少一个条件", "重新开始"], trace_id=trace)
        state.stage = "presenting"; state.candidate_product_ids = [h.product.id for h in hits]; state.displayed_product_ids = state.candidate_product_ids; state.pending_question = None
        self.db.save_state(state)
        return AgentResponse(session_id=session_id, intent=route.intent, stage=state.stage, text=f"找到 {len(hits)} 款符合当前需求的商品，推荐理由均来自商品快照。", products=hits, suggestions=["更便宜一点", "比较第 1 和第 2 个", "重新开始"], evidence_ids=[h.product.id for h in hits], trace_id=trace)

    def _compare(self, message: str, state: ConversationState, trace: str) -> AgentResponse:
        nums = [int(n) - 1 for n in re.findall(r"第?([一二三四1234])个?", message.translate(str.maketrans("一二三四", "1234")))]
        ids = [state.displayed_product_ids[n] for n in nums if 0 <= n < len(state.displayed_product_ids)]
        if len(ids) < 2: ids = state.displayed_product_ids[:2]
        products = self.db.get_products(ids[:4])
        if len(products) < 2:
            return AgentResponse(session_id=state.session_id, intent="COMPARE", stage="clarifying", text="请先搜索商品，或说明要比较结果中的哪两款。", trace_id=trace)
        dimensions = sorted(set().union(*(p.attributes.keys() for p in products)))
        rows = [{"dimension": d, **{p.id: p.attributes.get(d, "未提供") for p in products}} for d in ["price", *dimensions]]
        rows[0].update({p.id: p.price for p in products})
        state.stage = "presenting"
        return AgentResponse(session_id=state.session_id, intent="COMPARE", stage=state.stage, text=f"已按价格和关键参数对比 {products[0].title} 与 {products[1].title}。价格来自当前快照。", comparison=rows, evidence_ids=ids, trace_id=trace)

    def _qa(self, message: str, state: ConversationState, trace: str) -> AgentResponse:
        knowledge = {"ip68": "IP68 表示设备具备规定条件下的防尘和防水能力；实际水深、时长及保修范围应以厂商说明为准。", "oled": "OLED 是像素自发光显示技术，通常有较高对比度和深黑表现。", "主动降噪": "主动降噪通过麦克风采集环境声并生成反向声波，主要降低持续的低频噪声。"}
        key = next((k for k in knowledge if k in message.lower()), None)
        if key:
            return AgentResponse(session_id=state.session_id, intent="PRODUCT_QA", stage="presenting", text=knowledge[key], evidence_ids=[f"knowledge:{key}"], trace_id=trace)
        products = self.db.get_products(state.displayed_product_ids[:1])
        text = "当前知识库没有足够证据回答这个问题。"
        evidence = []
        if products:
            text = f"当前商品数据提供的信息是：{products[0].description}。未列出的参数无法确认。"; evidence = [products[0].id]
        return AgentResponse(session_id=state.session_id, intent="PRODUCT_QA", stage="presenting", text=text, evidence_ids=evidence, trace_id=trace)

