"""Run deterministic offline checks without a model key.

Usage: python evals/evaluator.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.orchestrator import Orchestrator
from domain.models import ConversationState
from repositories.database import Database
from services.search import QueryUnderstandingService


def load(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def run() -> dict[str, float]:
    query_cases = load(ROOT / "query_cases.jsonl")
    conversation_cases = load(ROOT / "conversation_cases.jsonl")
    understanding = QueryUnderstandingService()
    category_correct = filter_correct = 0
    # Windows can briefly retain SQLite handles after a connection context exits.
    # The temporary directory is best-effort cleanup only and is never project data.
    with TemporaryDirectory(ignore_cleanup_errors=True) as directory:
        db = Database(Path(directory) / "eval.db"); db.initialize()
        for case in query_cases:
            parsed = understanding.extract(case["query"], db.load_state("none") or ConversationState(session_id="none"))
            category_correct += parsed.get("category") == case["category"]
            filter_correct += all(parsed["hard_filters"].get(key) == value for key, value in case["hard_filters"].items())
        state_correct = 0
        for index, case in enumerate(conversation_cases):
            agent = Orchestrator(db); reply = None
            for turn in case["turns"]: reply = agent.handle(turn, f"case-{index}")
            saved = db.load_state(f"case-{index}")
            assertions = case["assertions"]
            checks = [
                not assertions.get("category") or saved.category == assertions["category"],
                not assertions.get("excluded_brand") or assertions["excluded_brand"] in saved.exclusions,
                not assertions.get("weight_kg_max") or saved.hard_filters.get("weight_kg_max") == assertions["weight_kg_max"],
                not assertions.get("stage") or reply.stage == assertions["stage"],
                not assertions.get("intent") or reply.intent == assertions["intent"],
            ]
            state_correct += all(checks)
    return {
        "category_accuracy": category_correct / len(query_cases),
        "hard_filter_case_accuracy": filter_correct / len(query_cases),
        "conversation_state_accuracy": state_correct / len(conversation_cases),
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
