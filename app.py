"""Expose the ShopGuide web experience, APIs, streaming events, and health checks."""

from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from agents.orchestrator import Orchestrator
from api.schemas import ChatRequest, CompareRequest, EventRequest, SearchRequest
from domain.models import ConversationState
from repositories.database import Database, build_demo_products
from services.search import RetrievalService

BASE = Path(__file__).parent
db = Database(os.getenv("SHOPGUIDE_DATABASE", str(BASE / "shopguide.db")))


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.initialize()
    yield


app = FastAPI(title="ShopGuide Agent", version="0.1.0", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (BASE / "web" / "index.html").read_text(encoding="utf-8")


@app.get("/health")
def health(): return {"status": "ok"}


@app.get("/ready")
def ready():
    try: count = len(db.all_products())
    except Exception as exc: raise HTTPException(503, str(exc)) from exc
    return {"status": "ready", "products": count}


@app.post("/api/v1/chat")
def chat(body: ChatRequest):
    session_id = body.session_id or str(uuid.uuid4())
    response = Orchestrator(db).handle(body.message, session_id, body.user_id)
    if not body.stream: return response
    payload = response.model_dump(mode="json")
    def events():
        yield f"event: status\ndata: {json.dumps({'stage': response.stage}, ensure_ascii=False)}\n\n"
        if response.products: yield f"event: products\ndata: {json.dumps({'items': payload['products']}, ensure_ascii=False)}\n\n"
        yield f"event: delta\ndata: {json.dumps({'text': response.text}, ensure_ascii=False)}\n\n"
        yield f"event: suggestions\ndata: {json.dumps({'items': response.suggestions}, ensure_ascii=False)}\n\n"
        yield f"event: done\ndata: {json.dumps({'trace_id': response.trace_id, 'session_id': session_id})}\n\n"
    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/api/v1/sessions/{session_id}")
def session(session_id: str):
    state = db.load_state(session_id)
    if not state: raise HTTPException(404, "session not found")
    return state


@app.delete("/api/v1/sessions/{session_id}")
def delete_session(session_id: str): return {"deleted": db.delete_state(session_id)}


@app.post("/api/v1/products/search")
def search(body: SearchRequest):
    state = ConversationState(session_id="debug", category=body.category, hard_filters=body.filters)
    return RetrievalService(db).search(state, body.query, body.top_k)


@app.post("/api/v1/products/compare")
def compare(body: CompareRequest):
    products = db.get_products(body.product_ids)
    if len(products) != len(body.product_ids): raise HTTPException(404, "one or more products not found")
    dimensions = sorted(set().union(*(p.attributes for p in products)))
    return {"products": products, "dimensions": [{"name": d, "values": {p.id: p.attributes.get(d) for p in products}} for d in dimensions]}


@app.post("/api/v1/events", status_code=202)
def event(body: EventRequest):
    return {"accepted": db.record_event(body.request_id, body.event_type, body.product_id, body.session_id, body.user_id), "request_id": body.request_id}


@app.post("/api/v1/admin/products/import")
def import_demo(request: Request):
    expected = os.getenv("SHOPGUIDE_ADMIN_TOKEN")
    if expected and request.headers.get("x-admin-token") != expected: raise HTTPException(401, "invalid admin token")
    return {"imported": db.import_products(build_demo_products())}


@app.post("/api/v1/admin/index/rebuild")
def rebuild_index(request: Request):
    expected = os.getenv("SHOPGUIDE_ADMIN_TOKEN")
    if expected and request.headers.get("x-admin-token") != expected: raise HTTPException(401, "invalid admin token")
    return {"reindexed": db.import_products(db.all_products())}
