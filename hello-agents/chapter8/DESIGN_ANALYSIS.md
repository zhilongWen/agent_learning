# HelloAgents 记忆系统设计解析

> 本文从认知科学根源、Agent Memory 行业范式、HelloAgents 自身实现三个层面，分析 `hello_agents/memory` 的设计取舍：为什么分四层、为什么记四种类型、Schema 字段为什么这样定、为什么按 memory_type 路由到不同存储后端。

---

## 1. 设计目标与问题域

LLM 本身是无状态的：每次推理只看到 context window 内的 token。要让 Agent 像人一样"记得"用户、积累经验、跨会话延续上下文，就必须在 LLM 之外构建一个外部记忆层。围绕这个目标，业界已形成几个共识：

- **短期 vs 长期分离**：短期(working)走上下文窗口，长期走外部存储 — 否则 token 成本随时间线性增长。
- **不同知识形态需要不同检索方式**：事实查相似度→向量；关系做多跳→图；事件按时间回放→文档/日志。
- **写入比读取更难**：何时写、写什么粒度、要不要总结 — 决定了系统能否长期稳定运行。
- **必须有遗忘机制**：无差别累积会让检索质量随时间退化。

HelloAgents 记忆系统就是围绕这四点做的工程实现，分四层把"记什么 / 怎么存 / 怎么找 / 何时忘"解耦开。

---

## 2. 认知科学依据：为什么是这四种记忆类型

`hello_agents/memory/types/` 下的四种类型并非随意挑的，对应认知心理学中 Tulving、Baddeley 等人提出的人类记忆分类：

| HelloAgents 类型 | 认知科学对应 | 人类例子 | Agent 中的作用 |
|------------------|--------------|----------|----------------|
| `WorkingMemory` | Working memory (Baddeley) | 心算时记住中间结果 | 当前会话上下文、推理中间状态 |
| `EpisodicMemory` | Episodic memory (Tulving) | "上周三和谁吃饭了" | 具体交互事件、带 session/时间戳 |
| `SemanticMemory` | Semantic memory (Tulving) | "巴黎是法国首都" | 概念、规则、跨场景通用知识 |
| `PerceptualMemory` | Perceptual representation system | 看到一张脸感到熟悉 | 多模态原始感知数据 |

**为什么必须分开？** 因为它们的访问模式根本不同：
- 工作记忆要求**毫秒级延迟、容量极小、自动衰减** → 内存堆 + 6 小时半衰期
- 情景记忆要求**按时间序列回放、保留完整上下文** → SQLite 文档存储 + session_id 索引
- 语义记忆要求**跨实例聚合成图、支持多跳推理** → NetworkX 知识图谱
- 感知记忆要求**跨模态比对** → 向量编码 + 余弦相似度

如果用单一存储和单一检索逻辑去硬塞所有信息，会得到一个"什么都查得不准"的系统 —— 这正是早期纯向量数据库方案在生产中暴露的问题。Mem0、Letta、Zep 等项目最终都走向了"按记忆类型选择存储"的混合架构，HelloAgents 的设计与这个行业趋势一致。

> **注**：经典认知科学还有一类 Procedural Memory（程序性记忆，"会骑自行车"），HelloAgents 没有把它做成独立类型 —— 因为 Agent 的"程序性知识"通常以工具/Skill 形式实现（见 `hello_agents/tools/`），不需要进记忆系统。这是一个合理的工程取舍。

---

## 3. 四层架构：为什么这样切分

```
hello_agents/memory/
├── base.py            ← MemoryItem / MemoryConfig / BaseMemory（数据契约）
├── core/              ← Manager / Store / Retriever（统一入口）
├── types/             ← Working / Episodic / Semantic / Perceptual（语义层）
├── storage/           ← Vector / Graph / Document（物理层）
└── rag/               ← Embeddings / Retriever / Document（外部知识检索）
```

### 3.1 为什么 Core 和 Types 要分开？

`MemoryManager` 不直接和具体记忆类型耦合，而是通过 `self.memory_types: dict` 持有它们 (`manager.py:45`)。这带来三个好处：

1. **可插拔**：通过 `enable_working / enable_episodic / ...` 控制启用哪些类型，不需要时不付出初始化成本。
2. **统一 API**：`add_memory / retrieve_memories / forget_memories` 是用户面向的入口，不暴露具体类型差异 —— 用户给一段文本，Manager 用 `_classify_memory_type()` 启发式分类后路由。
3. **跨类型协调**：`consolidate_memories()` 这样的"工作记忆 → 情景记忆"迁移操作，必须在 Manager 层做，单个类型自己看不到全局。

### 3.2 为什么 Types 和 Storage 要分开？

这是整个设计最关键的解耦。Types 层管"语义"，Storage 层管"物理"，中间通过 `MemoryStore.store_memory()` (`store.py:39`) 路由：

```python
if memory.memory_type in ["working", "episodic"]:
    success = self.document_store.store(memory)         # 主存：文档
    if memory.embedding is not None:
        self.vector_store.store(memory)                 # 副存：向量（可搜）
elif memory.memory_type == "semantic":
    success = self.vector_store.store(memory)           # 主存：向量
    if success:
        self.graph_store.store(memory)                  # 副存：图（可推理）
elif memory.memory_type == "perceptual":
    success = self.vector_store.store(memory)           # 仅向量
```

**为什么这样路由？** 行业经验：

- **向量存储**赢在"语义相似 + 召回率"，输在"多跳关系 + 精确时间过滤"。所以语义/感知记忆首选向量。
- **图存储**赢在"实体关系 + 多跳推理"，输在"插入开销 + 模糊匹配"。所以语义记忆 + 副存图，用于关系推理。
- **文档存储**赢在"结构化字段过滤 + 时间范围查询 + 持久化稳定"，输在"语义模糊匹配"。所以情景记忆首选文档，以 session_id / timestamp 索引。

工作记忆主存设为文档而非纯内存，是为了支持持久化场景；但 `WorkingMemory` 类内部仍维护 `self.memories: List[MemoryItem]` 内存副本以保证延迟（`working.py:36`）—— 这是工程上的取舍。

### 3.3 RAG 为什么作为独立子模块？

`memory/rag/` 处理的是**外部知识库**（用户上传的 PDF/文档），不是 Agent 自己的"经验"。两者虽然都用向量检索，但语义边界不同：

- Memory：Agent 的主观经验，有 user_id、importance、可遗忘
- RAG：客观外部知识，无主观属性，永久存在

放在同一个 package 下共享 `Embedding` 和 `VectorStore` 实现，又通过独立子模块表达语义差异 —— 是合理的折中。

---

## 4. Schema 设计：为什么 MemoryItem 长这样

`base.py:22` 定义的核心数据契约：

```python
class MemoryItem(BaseModel):
    id: str
    content: str
    memory_type: str          # "working" / "episodic" / "semantic" / "perceptual"
    user_id: str
    timestamp: datetime
    importance: float = 0.5
    metadata: Dict[str, Any] = {}
```

**逐字段分析：**

| 字段 | 作用 | 为什么必须有 |
|------|------|--------------|
| `id` | 唯一标识 | 跨多个存储后端定位同一条记忆（向量+图+文档） |
| `content` | 原始文本 | LLM 最终消费的格式；任何检索结果都要能还原成文本 |
| `memory_type` | 类型标签 | **路由依据** —— Store/Retriever/Forget 都按它分支 |
| `user_id` | 用户隔离 | 多租户场景的硬隔离边界；任何检索都应过滤 |
| `timestamp` | 时间戳 | 时间衰减计算、按时间过滤、生成 timeline |
| `importance` | 重要性 0-1 | 排序、遗忘、整合的核心信号 |
| `metadata` | 扩展槽 | 类型特定字段（session_id / context / outcome / modality / encoding）走这里，避免污染主 schema |

**这个 schema 的妙处在于"骨架统一 + 扩展开放"**：

- 主字段是所有记忆类型的最大公约数 → 存储后端可以不关心具体类型，统一处理增删改查。
- 类型特定字段进 `metadata`：
  - `EpisodicMemory` 用 `metadata["session_id"]`、`metadata["context"]`、`metadata["outcome"]`
  - `SemanticMemory` 用 `metadata["extracted_concepts"]`
  - `PerceptualMemory` 用 `metadata["modality"]`、`metadata["encoding"]`、`metadata["raw_data"]`
  
  这种"主表 + JSON 扩展列"模式与生产级系统的做法一致 —— 既保留了关系型存储的索引能力，又有 NoSQL 的灵活性。

**为什么不给每种类型独立 schema？** 早期版本可能这样做，但实际上：
- 跨类型查询会变成 union 多张表
- `MemoryStore.search_memories()` 这种通用接口写不出来
- 类型迁移（`consolidate_memories`）需要字段映射，复杂度上升

把差异下沉到 `metadata` 是最务实的选择。

**`importance: float = 0.5` 为什么默认 0.5？** 这是个有意思的细节：默认中性，让自动启发式（关键词、长度、metadata.priority）只在有明确信号时才偏移评分（`manager.py:319`）。如果默认 0，所有记忆都得依赖显式打分；如果默认 1，遗忘机制几乎无用。0.5 是"将信将疑"的合理起点。

---

## 5. 检索策略：为什么提供三种

`MemoryRetriever` (`core/retriever.py:223`) 提供 keyword / vector / hybrid 三种策略，默认 hybrid，权重 keyword 0.3 + vector 0.7。

**为什么不只用向量？** 行业血泪经验：

- 向量擅长"语义相似"，但对**专有名词、ID、时间字符串**等精确匹配信号不敏感 —— 用户问"订单 ORD-1234 怎么了"，向量可能召回"订单查询流程"这种语义相近但答非所问的内容。
- 关键词擅长"精确命中"，但对**同义改写**完全无效 —— 用户问"我的请假记录"，记忆里写的是"年假申请"，纯关键词漏召。
- Hybrid 用加权组合规避两边的失效模式，是 Mem0、Zep 等系统的默认配置。

权重 0.7/0.3 偏向向量是合理的：现代 embedding 模型质量高于 BM25 类关键词，但也不能完全砍掉关键词通道。

**时间衰减** (`_apply_time_decay`, `retriever.py:322`) 在排序后再乘一个衰减因子。这模拟了"近期发生的事更可能相关"的认知规律，对话场景下尤其重要。

---

## 6. 写入策略：分类、重要性、整合、遗忘

这是记忆系统最容易出问题的地方。HelloAgents 的设计：

### 6.1 自动分类 `_classify_memory_type` (`manager.py:296`)

```python
if "昨天/今天/上次/记得/经历" in content: return "episodic"
elif "定义/概念/规则/原理/方法" in content: return "semantic"
else: return "working"
```

朴素关键词启发式 —— 优点是零成本、可解释；缺点是中文为主，对英文/混合内容失效。这是个**已知的妥协**：
- 用 LLM 分类太贵（每次写入都要一次推理）
- 训练专门的小分类器太重
- 用户可显式指定 `memory_type` 或 `metadata["type"]` 兜底

合理的做法是把这层放在最外层，便于将来替换成 LLM judge。

### 6.2 重要性计算 (`manager.py:319` / `base.py:167`)

```python
importance = 0.5 (基础)
+ 0.1  if len(content) > 100         # 长内容更重要？这是个启发式假设
+ 0.2  if 含"重要/关键/必须/警告"    # 用户元话语
+ 0.3  if metadata.priority == "high"  # 显式信号最强
- 0.2  if metadata.priority == "low"
clamp [0, 1]
```

这个公式的精度有限，但**它的存在比它的精度更重要** —— 给遗忘和整合机制提供了排序信号。生产系统通常会把它替换成 LLM 评分或学习模型，但骨架不变。

### 6.3 整合 `consolidate_memories` (`manager.py:223`)

```
working memory 中 importance ≥ 0.7 的项 → 迁移到 episodic memory（importance ×1.1）
```

这是仿照人类**睡眠期记忆巩固**机制 —— 短期记忆中重要的会"沉淀"为长期记忆。Mem0 的 "memory consolidation"、MemGPT 的 "main memory → archival memory" 是同样的思路。

### 6.4 遗忘 `forget_memories` (`manager.py:197`)

三种策略：
- `importance_based`：低于阈值的删 —— 适合主动清理
- `time_based`：超过 N 天的删 —— 适合周期性维护
- `capacity_based`：超过容量的按优先级删 —— 适合工作记忆

**为什么必须遗忘？** 三个原因：
1. 容量爆炸 → 检索性能下降
2. 旧信息冲淡新信息 → 召回质量退化
3. 用户隐私合规 → 必须支持定期删除

---

## 7. 与业界方案的对比

| 维度 | HelloAgents | Mem0 | MemGPT/Letta | Zep |
|------|-------------|------|--------------|-----|
| 记忆分类 | working/episodic/semantic/perceptual | 单层 + extraction | main/recall/archival | session/episode/fact |
| 默认存储 | Chroma + NetworkX + SQLite | Vector + 可选 Graph | LLM-managed paging | Graph(Graphiti) |
| 检索 | keyword + vector + hybrid | vector + graph hop | OS-style 分页 | temporal graph |
| 写入决策 | 关键词分类 + 启发式打分 | LLM extraction | LLM 自主调用工具 | 时间图谱自动构建 |
| 遗忘 | 三策略可选 | 软删除 + 衰减 | 主动 archive | 时间衰减 |
| 多模态 | ✅ Perceptual | 有限 | ❌ | ❌ |

**HelloAgents 的定位**：

- 偏教学/原型友好：分类清晰、代码结构对应教材章节（"第8章"）
- 实现深度中等：四种类型 + 三种存储覆盖了主流范式，但启发式逻辑较朴素，未引入 LLM-as-judge
- 扩展性好：四层解耦让任何一层都可独立替换（换 embedding、换图后端、加 LLM 分类）

如果是面向生产，需要在三处加强：
1. `_classify_memory_type` 替换为 LLM judge 或学习模型
2. `_calculate_importance` 引入更细粒度的信号（用户反馈、被引用次数）
3. 增加去重/合并逻辑 —— 当前同一事实重复说会写多条

---

## 8. 关键文件速查

| 设计点 | 位置 |
|--------|------|
| 数据契约 `MemoryItem` | `hello_agents/memory/base.py:22` |
| 配置 `MemoryConfig` | `hello_agents/memory/base.py:36` |
| 抽象基类 `BaseMemory` | `hello_agents/memory/base.py:71` |
| 统一管理 `MemoryManager` | `hello_agents/memory/core/manager.py:18` |
| 路由策略 `store_memory` | `hello_agents/memory/core/store.py:39` |
| 三种检索策略 | `hello_agents/memory/core/retriever.py:41,96,164` |
| 工作记忆容量控制 | `hello_agents/memory/types/working.py:282` |
| 情景记忆模式识别 | `hello_agents/memory/types/episodic.py:252` |
| 语义记忆图谱构建 | `hello_agents/memory/types/semantic.py:331` |
| 感知记忆跨模态搜索 | `hello_agents/memory/types/perceptual.py:205` |
| 整合机制 | `hello_agents/memory/core/manager.py:223` |
| 遗忘机制 | `hello_agents/memory/core/manager.py:197` |

---

## 参考资料

- [Types of AI Agent Memory — Atlan](https://atlan.com/know/types-of-ai-agent-memory/)
- [Memory Architectures for Production AI Agents — tianpan.co](https://tianpan.co/blog/2025-10-21-memory-architectures-for-production-ai-agents)
- [Vector vs Graph vs Episodic — Digital Applied](https://www.digitalapplied.com/blog/agent-memory-architectures-vector-graph-episodic)
- [Mem0: Building Production-Ready AI Agents — arXiv 2504.19413](https://arxiv.org/html/2504.19413)
- [Mem0 Graph-Based Memory Solutions](https://mem0.ai/blog/graph-memory-solutions-ai-agents)
- [State of AI Agent Memory 2026 — Mem0](https://mem0.ai/blog/state-of-ai-agent-memory-2026)
- [Memory Retrieval Strategies for AI Agents — Mem0](https://mem0.ai/blog/memory-retrieval-strategies-for-ai-agents)
- [Designing Agent Memory: Summaries, Episodic Logs, Semantic Facts — Paul Serban](https://paulserban.eu/blog/post/designing-agent-memory-summaries-episodic-logs-and-semantic-facts/)
- [AI Agent Memory Compared 2026 — Vectorize](https://vectorize.io/articles/mem0-vs-letta)
- [How to Design Efficient Memory Architectures for Agentic AI Systems — TowardsAI](https://pub.towardsai.net/how-to-design-efficient-memory-architectures-for-agentic-ai-systems-81ed456bb74f)
