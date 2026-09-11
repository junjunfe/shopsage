# 评测、工程化与面试讲解

## 11. 测试与离线评测方案

测试分为四层：

| 层级 | 覆盖对象 | 当前位置/后续产物 |
| --- | --- | --- |
| 单元测试 | 价格单位、DSL 校验、约束合并、硬过滤、RRF、排序、证据校验 | `tests/test_shopguide.py`，继续拆分到 `tests/unit/` |
| 集成测试 | 理解 → 合并 → 混合检索 → 重排；QA → RAG → 验证 | `tests/integration/` |
| E2E 测试 | 搜索、追问、条件修正、比较、零结果恢复 | `tests/e2e/`，固定 20 组对话用例 |
| 离线评测 | 路由、Slot F1、Recall@20、NDCG@5、硬条件违规率、Grounded Fact Rate | `evals/query_cases.jsonl`、`evals/conversation_cases.jsonl`、`evals/evaluator.py` |

关键门禁：硬条件违规率必须为 0；商品事实必须来自 ProductSnapshot 或 EvidenceChunk；模型结构化输出校验失败时最多重试一次，随后降级到规则解析。

建议在接入真实模型后，建立以下对照实验：纯 BM25、BM25 + Embedding、BM25 + Embedding + RRF、加/不加重排、固定追问/信息增益追问。每次提交记录版本、数据集、模型版本、Prompt 版本、延迟和指标。

## 12. 创新点与面试讲解

可用以下叙事解释项目：

1. “我把大模型定位为需求理解和流程决策组件，不把它当商品数据库。商品价格、库存和参数永远由 Tool 返回的快照提供。”
2. “多 Agent 的核心不是堆 Prompt，而是由 Orchestrator 管理多轮 `ConversationState`，在搜索、澄清、对比和 RAG 问答之间路由。”
3. “我使用 Pydantic DSL 约束模型输出，结构化约束和语义偏好分层：前者硬过滤，后者参与召回和排序。”
4. “检索采用 BM25、向量和 RRF；重排给出 match reasons，并通过 ResponseValidator 阻止候选外商品和无证据事实。”
5. “模型不可用时系统仍可通过规则、SQLite FTS5 和本地哈希向量运行，因此 Demo 可复现，也容易做基线评测。”

大模型应用技术栈的关键词：Prompt/Schema Design、OpenAI-compatible Provider、Structured Output、Pydantic Validation、Embedding、Vector Retrieval、RAG Evidence、Tool Calling、Agent Orchestration、SSE Streaming、Fallback、Offline Eval、Trace 与 Guardrails。
