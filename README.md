# ShopGuide Agent

ShopGuide Agent is a conversational ecommerce search assistant. It turns a shopper's natural-language request into product constraints, maintains context across turns, retrieves eligible products, and returns grounded recommendations with prices, availability, and evidence.

The application can run against an OpenAI-compatible inference API for structured query understanding and embeddings. It also includes an offline fallback so the demo remains usable when a model endpoint is unavailable.

## What Users Can Do

- Search across laptops, phones, and headphones using budget, brand, specifications, and shopping intent.
- Refine a previous result set with instructions such as “make it cheaper” or “exclude this brand”.
- Receive one focused clarification question when a missing preference would materially improve the result.
- Compare two to four previously displayed products in a structured table.
- Ask evidence-backed product and terminology questions.
- View a browser demo or call the REST and streaming APIs directly.

## Product Architecture

The conversation orchestrator routes each turn to search, refinement, comparison, product Q&A, feedback, or reset handling. Search combines structured eligibility filters, BM25 retrieval, embedding-based semantic retrieval, Reciprocal Rank Fusion, and explainable ranking. Product facts only come from catalog snapshots; knowledge answers include evidence identifiers.

For the full product specification, Agent flow, constraint DSL, RAG guardrails, API contract, delivery milestones, and acceptance criteria, read [Agent Architecture](docs/agent_architecture.md). For evaluation strategy and interview framing, read [Evaluation and Interview Guide](docs/evaluation_and_interview.md).

## AI Application Stack

| Capability | Technology |
| --- | --- |
| Model inference | OpenAI-compatible Chat Completions API; compatible with OpenAI, Azure-style gateways, and vLLM endpoints |
| Structured output | Pydantic schemas for validated search constraints and Agent responses |
| Embeddings | OpenAI-compatible Embeddings API, with an offline vector fallback |
| RAG | Evidence chunks, constrained knowledge tool, and response validation |
| Agent orchestration | Stateful conversation router with explicit search, comparison, and Q&A paths |
| Retrieval | SQLite FTS5/BM25, vector similarity, and Reciprocal Rank Fusion |
| Streaming | FastAPI Server-Sent Events |
| Evaluation | Pytest plus deterministic query and multi-turn evaluation datasets |

## Project Layout

```text
shopsage/
├── app.py                 # API application and streaming endpoints
├── agents/                # Conversation orchestration
├── config/                # Model provider configuration
├── domain/                # Product, conversation, and constraint schemas
├── services/              # Understanding, retrieval, ranking, RAG, and validation
├── tools/                 # Bounded catalog and knowledge tools
├── repositories/          # SQLite catalog, session, event, and preference storage
├── web/                   # Browser demo
├── evals/                 # Offline datasets and evaluator
├── tests/                 # Automated tests
└── docs/                  # Architecture and evaluation documentation
```

## Run Locally

Requirements: Python 3.11 or newer.

```powershell
python -m pip install -e ".[dev]"
python -m uvicorn app:app --reload
```

On first launch, the application creates `shopguide.db` and loads 120 demonstration products. Open these URLs:

- Demo: <http://127.0.0.1:8000>
- API documentation: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>

## Configure a Model API

Copy `.env.example` to `.env` and set an OpenAI-compatible endpoint, key, chat model, and embedding model. The endpoint should include the API version prefix when required, for example `https://api.openai.com/v1`.

```dotenv
SHOPGUIDE_MODEL_BASE_URL=https://api.openai.com/v1
SHOPGUIDE_MODEL_API_KEY=your-api-key
SHOPGUIDE_MODEL_NAME=your-chat-model
SHOPGUIDE_EMBEDDING_MODEL=your-embedding-model
```

When configured, the query-understanding service requests JSON output and validates it with Pydantic before applying constraints. If a request fails validation or the provider is unavailable, the application safely falls back to deterministic local parsing.

## Test and Evaluate

```powershell
python -m pytest -q
$env:PYTHONIOENCODING = "utf-8"
python evals/evaluator.py
```

## Run with Docker

```powershell
docker build -t shopguide-agent .
docker run --rm -p 8000:8000 shopguide-agent
```
