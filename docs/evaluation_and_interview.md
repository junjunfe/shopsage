# Evaluation and Interview Guide

This guide defines the quality gates, evaluation layers, and portfolio narrative for ShopGuide Agent.

## Quality Strategy

| Test level | Focus |
| --- | --- |
| Unit tests | Constraint validation, parsing, state updates, filtering, retrieval fusion, ranking, and evidence validation |
| Integration tests | Requirement understanding through retrieval and ranking; Q&A through evidence validation |
| End-to-end tests | Search, clarification, refinement, comparison, recovery, and session isolation |
| Offline evaluation | Intent accuracy, constraint F1, Recall@20, NDCG@5, hard-constraint violation rate, grounding rate, and state update accuracy |

The core quality gates are simple: hard-constraint violation rate must remain zero, and any product fact must be traceable to a product snapshot or evidence chunk. A model response that fails schema validation must be retried once or replaced by deterministic fallback behaviour.

The repository includes deterministic query and multi-turn datasets with an executable evaluator. Model-enabled deployments should compare keyword-only retrieval, semantic retrieval, RRF fusion, and re-ranking against the same fixed evaluation set.

## Interview Narrative

1. The model is used for requirement understanding and workflow decisions, not as a product database.
2. Multi-Agent design is expressed through a stateful orchestrator that selects search, clarification, comparison, and Q&A paths.
3. Structured constraints separate strict eligibility rules from semantic preferences, which makes the assistant testable and safe.
4. Hybrid retrieval combines keyword and embedding signals before explainable ranking, while evidence validation prevents unsupported product claims.
5. The system remains runnable without provider credentials, which makes demos reproducible and supplies a useful baseline for model evaluation.

## AI Application Competencies

Prompt and schema design, OpenAI-compatible model integration, structured output validation, embeddings, vector retrieval, RAG evidence, bounded tool calling, Agent orchestration, SSE streaming, deterministic fallback, offline evaluation, and grounded-response guardrails.
