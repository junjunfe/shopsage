# ShopGuide Agent Product Design

## Overview

ShopGuide Agent is an AI shopping assistant for product discovery and purchase decisions. Instead of requiring users to master filters and product names, it accepts conversational requests such as: “I need a lightweight laptop for programming under 5,000 RMB.”

The assistant identifies intent, understands requirements, asks only useful follow-up questions, retrieves products, explains recommendations, compares shortlisted items, and learns from explicit feedback. It supports search and decision assistance; payments, fulfilment, advertising auctions, and order management are outside the scope.

## User Experience

The product is designed around six high-value shopping moments:

1. Exploring a vague need, such as choosing a camera-focused phone for a parent.
2. Searching with clear constraints, such as an ANC headset under a fixed budget.
3. Refining an existing search without starting over.
4. Comparing previously recommended products.
5. Asking product or terminology questions with cited evidence.
6. Recovering from an empty result set by proposing the smallest useful relaxation.

## Agent Responsibilities

The Conversation Orchestrator selects the next action from search, refinement, comparison, product Q&A, feedback, reset, and out-of-scope handling. The Search Agent owns requirements, clarifications, retrieval, and recommendation presentation. The Comparison Agent explains trade-offs across the shopper's priorities. The Product Q&A Agent uses catalog facts and knowledge evidence. The Preference Agent records session and long-term signals without overriding an explicit current request.

## Product Principles

- The model coordinates decisions; retrieval systems provide product truth.
- Hard constraints and semantic preferences are separate.
- Each recommendation is grounded in a time-bound product snapshot.
- The assistant asks one high-value question at a time rather than presenting a form.
- A response never introduces a product or product fact that is absent from the current evidence.
- The system remains useful if a model provider is unavailable.

## Delivery Scope

The shipped application includes conversational product search, refinement, clarification, comparison, terminology Q&A, event capture, browser demo, REST API, streaming output, automated tests, and an offline evaluator. The reference architecture and product acceptance plan are maintained in [Agent Architecture](docs/agent_architecture.md); the evaluation plan and portfolio narrative are in [Evaluation and Interview Guide](docs/evaluation_and_interview.md).
