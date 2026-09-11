# ShopGuide Agent

一个离线优先的电商商品检索对话系统。它把自然语言需求转成结构化约束，维护多轮状态，并通过 SQLite FTS5、硬过滤和可解释排序返回真实商品快照。

## 已实现

- 120 条确定性演示商品，覆盖笔记本、手机和耳机
- 搜索、条件修改、澄清、零结果恢复、商品对比和术语问答
- 价格、品牌、内存、重量、续航、耳机形态和降噪硬过滤
- SQLite FTS5 关键词召回、规则语义匹配、可解释排序和品牌多样性
- FastAPI、SSE 协议、会话状态、幂等行为事件和管理端导入
- 无 API Key 可运行的中文 Web Demo

## 本地启动

```powershell
python -m pip install -e ".[dev]"
python -m uvicorn app:app --reload
```

打开 <http://127.0.0.1:8000>，API 文档位于 <http://127.0.0.1:8000/docs>。

测试：

```powershell
python -m pytest
```

Docker：

```powershell
docker build -t shopguide .
docker run --rm -p 8000:8000 shopguide
```

## 示例

1. `5000 元以内、适合写代码的轻薄笔记本`
2. `不要联想，最好 1.5kg 以下`
3. `比较第 1 个和第 2 个`
4. `IP68 是什么意思？`

价格和库存来自每轮返回的商品快照。未知商品事实会明确说明数据不足。
