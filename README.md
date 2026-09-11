# ShopGuide Agent

ShopGuide Agent 是一个离线优先的电商导购对话系统。用户可以使用自然语言描述预算、品类、使用场景和偏好；系统会提取结构化条件、保留多轮会话状态、检索商品并给出可追溯的推荐依据。

例如，用户输入“5000 元以内、适合写代码的轻薄笔记本”，系统会按预算、内存、重量等硬条件过滤商品，再结合“编程”“便携”等软偏好进行排序。用户还可以继续说“不要联想，最好 1.5kg 以下”或“比较第 1 个和第 2 个”，系统会在同一会话中更新条件并返回结果。

## 项目简介

当前版本实现了一个无需模型 API Key 即可运行的 MVP，包含：

- 120 条演示商品，覆盖笔记本、手机和蓝牙耳机三个品类；
- 搜索、条件修改、品类澄清、零结果恢复、商品对比和术语问答；
- 价格、品牌、内存、重量、续航、耳机形态和降噪等硬过滤；
- SQLite FTS5 关键词召回、规则化语义匹配、可解释排序和品牌多样性控制；
- 商品快照、证据 ID、会话状态和幂等的用户行为事件；
- REST API、SSE 流式对话协议和中文 Web Demo。

项目按大模型应用的生产架构预留了 Provider、Structured Output、Embedding、RAG、Tool Calling、流式响应与离线评测边界。当前默认使用本地规则、哈希向量和内置知识，让项目在没有 API Key 时仍可运行；配置 OpenAI-compatible Provider 后可将需求理解和向量化替换为真实模型服务。

详细的 Agent 架构、DSL、RRF、RAG 防幻觉与五阶段实施计划见 [Agent 架构文档](docs/agent_architecture.md)；测试、评测与面试讲解见 [评测与面试文档](docs/evaluation_and_interview.md)。

## 项目结构

```text
shopsage/
├── app.py                     # FastAPI 入口、路由与 SSE 响应
├── agents/
│   └── orchestrator.py         # 意图路由、搜索、对比和知识问答编排
├── api/
│   └── schemas.py              # HTTP 请求 Schema
├── domain/
│   └── models.py               # 商品、会话、路由和响应领域模型
├── repositories/
│   └── database.py             # SQLite、FTS5、商品种子和会话持久化
├── services/
│   └── search.py               # 条件提取、状态合并、过滤、检索和排序
├── web/
│   └── index.html              # 原生 JavaScript 中文演示前端
├── tests/
│   └── test_shopguide.py       # 核心搜索、多轮和知识问答测试
├── ecommerce_product_search_agent_design.md  # 项目设计规格
├── pyproject.toml              # Python 依赖与测试配置
├── Dockerfile                  # 容器化启动配置
└── .env.example                # 可配置环境变量示例
```

## 技术栈

| 分层 | 技术 | 用途 |
| --- | --- | --- |
| 后端 | Python 3.11、FastAPI、Uvicorn | API、OpenAPI 文档与流式响应 |
| 数据校验 | Pydantic v2 | 请求、会话、商品和 Agent 响应 Schema |
| 数据存储 | SQLite | 商品、会话状态和用户行为事件持久化 |
| 搜索 | SQLite FTS5、结构化过滤 | 关键词召回与硬条件筛选 |
| 排序 | 可解释规则打分 | 语义标签、关键词、属性、评分、热度和库存综合排序 |
| 前端 | HTML、CSS、原生 JavaScript | 对话页面和商品卡片展示 |
| 测试 | Pytest | 商品初始化、过滤、多轮修改、对比和问答验证 |
| 部署 | Docker | 容器化运行 |

### 大模型应用开发能力映射

| 能力 | 当前实现 | 生产化接入方式 |
| --- | --- | --- |
| 模型 Provider | `config/model_provider.py` 的 OpenAI-compatible 抽象 | OpenAI、Azure OpenAI、vLLM 或企业模型网关 |
| Structured Output | Pydantic DSL 与响应 Schema | 模型 JSON Schema/Function Calling 输出后校验与重试 |
| Embedding | 本地哈希向量，保证离线可运行 | OpenAI/BGE Embedding + pgvector、FAISS 或 Chroma |
| RAG | EvidenceChunk、KnowledgeTool、ResponseValidator | 文档切块、向量检索、重排序和带出处生成 |
| Agent Tool Calling | CatalogTool、KnowledgeTool、Event Repository | 通过受限输入输出 Schema 接入商品、价格和库存服务 |
| 流式交互 | FastAPI SSE：status/products/delta/done | 模型 token 流、工具状态和可观测 trace 联动 |

## 运行方式

### 前置要求

- Python 3.11 或更高版本
- 可选：Docker Desktop，用于容器运行

### 本地运行

在项目根目录执行：

```powershell
python -m pip install -e ".[dev]"
python -m uvicorn app:app --reload
```

首次启动时，系统会自动在项目目录创建 `shopguide.db` 并导入 120 条演示商品。随后可访问：

- Web Demo：<http://127.0.0.1:8000>
- OpenAPI 文档：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/health>
- 就绪检查：<http://127.0.0.1:8000/ready>

### 运行测试

```powershell
python -m pytest -q
```

### Docker 运行

```powershell
docker build -t shopguide-agent .
docker run --rm -p 8000:8000 shopguide-agent
```

打开 <http://127.0.0.1:8000> 即可使用。

## 对话示例

```text
用户：5000 元以内、适合写代码的轻薄笔记本
用户：不要联想，最好 1.5kg 以下
用户：比较第 1 个和第 2 个
用户：IP68 是什么意思？
```

每个推荐结果都会返回商品 ID、价格、库存、评分和匹配理由；商品数据未提供的事实会明确说明无法确认。
