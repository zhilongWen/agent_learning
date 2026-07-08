# Memory 与 RAG API

当前集成版只保留 `mem` 作为记忆系统包。原 upstream `memory/` 包已合并进 `mem/`，运行时代码和文档示例都应使用 `mem.*` 或工具入口 `MemoryTool`、`RAGTool`。

```python
from mem import MemoryManager, MemoryConfig
from tools.builtin import MemoryTool, RAGTool
```

## 架构

```text
mem/
├── base.py             # MemoryItem、MemoryConfig、BaseMemory
├── manager.py          # MemoryManager 统一入口
├── types/
│   ├── working.py      # 工作记忆
│   ├── episodic.py     # 情景记忆
│   ├── semantic.py     # 语义记忆
│   └── perceptual.py   # 感知记忆
├── storage/
│   ├── document_store.py
│   ├── qdrant_store.py
│   └── neo4j_store.py
└── rag/
    ├── document.py
    └── pipeline.py
```

## MemoryManager

```python
from mem import MemoryManager, MemoryConfig

manager = MemoryManager(
    config=MemoryConfig(),
    user_id="default_user",
    enable_working=True,
    enable_episodic=True,
    enable_semantic=True,
    enable_perceptual=False,
)

memory_id = manager.add_memory(
    content="用户偏好 Python 示例",
    memory_type="working",
    importance=0.8,
)

items = manager.retrieve_memories(
    query="用户喜欢什么语言？",
    limit=5,
)
```

主要方法：

| 方法 | 说明 |
| --- | --- |
| `add_memory()` | 添加记忆，可自动分类 |
| `retrieve_memories()` | 跨类型检索 |
| `update_memory()` | 更新已有记忆 |
| `remove_memory()` | 删除记忆 |
| `forget_memories()` | 按策略遗忘 |
| `consolidate_memories()` | 记忆整合 |
| `get_memory_stats()` | 统计信息 |

## 记忆类型

| 类型 | 类 | 适合内容 | 默认存储 |
| --- | --- | --- | --- |
| `working` | `WorkingMemory` | 当前任务短期上下文 | 内存 |
| `episodic` | `EpisodicMemory` | 事件、会话、操作轨迹 | SQLite + Qdrant |
| `semantic` | `SemanticMemory` | 概念、事实、实体关系 | SQLite + Qdrant + Neo4j |
| `perceptual` | `PerceptualMemory` | 文本、图像、音频、视频元数据 | 按模态的向量存储 |

感知记忆中的 CLIP/CLAP 默认不主动联网下载。需要显式开启：

```bash
PERCEPTUAL_ENABLE_CLIP=1
PERCEPTUAL_ENABLE_CLAP=1
PERCEPTUAL_MODEL_LOCAL_ONLY=0
```

## MemoryTool

`MemoryTool` 是给 Agent 使用的工具化入口：

```python
from tools.builtin import MemoryTool

tool = MemoryTool(user_id="user-1")

resp = tool.run({
    "action": "add",
    "content": "用户正在学习 RAG",
    "memory_type": "working",
    "importance": 0.7,
})

print(resp.text)
```

常用 action：

| action | 说明 |
| --- | --- |
| `add` | 添加记忆 |
| `search` | 检索记忆 |
| `update` | 更新记忆 |
| `remove` | 删除记忆 |
| `forget` | 遗忘低价值或过期记忆 |
| `consolidate` | 记忆整合 |
| `stats` | 查看统计 |

## RAGTool

`RAGTool` 是文档索引和检索增强生成入口：

```python
from tools.builtin import RAGTool

rag = RAGTool(
    knowledge_base_path="./knowledge_base",
    collection_name="hello_agents_rag",
    rag_namespace="default",
)

rag.run({
    "action": "add_text",
    "text": "Python 由 Guido van Rossum 创建。",
    "document_id": "python-history",
    "namespace": "demo",
})

resp = rag.run({
    "action": "search",
    "query": "Python 是谁创建的？",
    "namespace": "demo",
    "limit": 3,
})

print(resp.text)
```

常用 action：

| action | 说明 |
| --- | --- |
| `add_document` | 添加本地文档 |
| `add_text` | 添加文本 |
| `search` | 检索片段 |
| `ask` | 检索后生成回答 |
| `stats` | 查看知识库统计 |
| `clear` | 清空命名空间或集合 |

## 外部服务配置

Qdrant：

```bash
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=hello_agents_vectors
QDRANT_DISTANCE=cosine
```

Neo4j：

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=hello-agents-password
```

Embedding：

```bash
EMBED_MODEL_TYPE=local
EMBED_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBED_API_KEY=
EMBED_BASE_URL=
```

`QdrantVectorStore` 兼容新旧 `qdrant-client` 查询 API，并在已有 collection 维度不一致时切换到带 `_dim{size}` 后缀的新 collection，避免误写旧向量空间。

## 在 Agent 中使用

```python
from agents import ReActAgent
from core import HelloAgentsLLM
from tools import ToolRegistry
from tools.builtin import MemoryTool, RAGTool

registry = ToolRegistry()
registry.register_tool(MemoryTool(user_id="user-1"))
registry.register_tool(RAGTool(knowledge_base_path="./knowledge_base"))

agent = ReActAgent("memory-agent", HelloAgentsLLM(), tool_registry=registry)
print(agent.run("记住我正在学习 Agent，然后查询相关知识。"))
```

## 与旧文档的差异

- 使用 `mem`，不要新建 `memory` 包。
- 示例使用顶层包导入，如 `from tools.builtin import RAGTool`。
- 当前版本号为 `1.0.0`，不是旧文档中的 `0.2.x`。
