from pathlib import Path
from agents.orchestrator import Orchestrator
from domain.models import ConversationState, Preference
from repositories.database import Database
from services.hybrid_retrieval import HybridRetrievalService
from services.rag import RagService


def make_db(tmp_path: Path) -> Database:
    db = Database(tmp_path / "test.db"); db.initialize(); return db


def test_seeds_120_products(tmp_path):
    assert len(make_db(tmp_path).all_products()) == 120


def test_hard_filters_never_violated(tmp_path):
    db = make_db(tmp_path)
    reply = Orchestrator(db).handle("5000 元以下、16GB 以上、适合编程的笔记本", "s1")
    assert reply.products
    assert all(x.product.price <= 5000 and x.product.attributes["memory_gb"] >= 16 for x in reply.products)


def test_multiturn_refinement_and_compare(tmp_path):
    agent = Orchestrator(make_db(tmp_path))
    first = agent.handle("5000 元以内适合编程的笔记本", "s2")
    refined = agent.handle("不要联想，最好 1.5kg 以下", "s2")
    compared = agent.handle("比较第1个和第2个", "s2")
    assert first.products and refined.products
    assert all(x.product.brand != "联想" and x.product.attributes["weight_kg"] <= 1.5 for x in refined.products)
    assert compared.comparison


def test_clarifies_missing_category(tmp_path):
    reply = Orchestrator(make_db(tmp_path)).handle("想买一个便宜好用的", "s3")
    assert reply.stage == "clarifying"


def test_knowledge_answer_has_evidence(tmp_path):
    reply = Orchestrator(make_db(tmp_path)).handle("IP68 是什么意思？", "s4")
    assert reply.evidence_ids == ["knowledge:ip68"]


def test_hybrid_retrieval_uses_two_recall_signals(tmp_path):
    db = make_db(tmp_path)
    state = ConversationState(session_id="hybrid", category="laptop", soft_preferences=[Preference(name="编程", weight=.8)])
    candidates = HybridRetrievalService(db).recall(state, "适合编程的轻薄笔记本")
    assert candidates
    _, rrf, lexical, semantic = candidates[0]
    assert rrf > 0 and lexical >= 0 and semantic >= 0


def test_rag_returns_citable_evidence():
    evidence = RagService().retrieve("IP68 是什么意思")
    assert evidence and evidence[0].id == "knowledge:ip68"
