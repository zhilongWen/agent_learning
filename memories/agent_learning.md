# agent_learning

## Project Shape

- Root project is a Python learning/workshop repository for agent patterns, based on Datawhale Hello-Agents.
- Main framework code lives under `hello-agents/HelloAgents`.
- Chapter examples live under `hello-agents/chapter1`, `chapter3`, `chapter4`, `chapter6`, `chapter7`, and `chapter8`.
- `hello_agent/main.py` is only a tiny placeholder that prints `Hello Agent!`; it is not the main framework.
- Top-level README files are sparse. `hello-agents/HelloAgents/README.md` describes a broader planned architecture, but the real code uses `core`, `agents`, `tools`, `mem`, `utils`, `docs`, and `test`.

## Core Framework

- `hello-agents/HelloAgents/core/llm.py` defines `HelloAgentsLLM`, the central OpenAI-compatible chat client.
- `HelloAgentsLLM` supports providers `openai`, `deepseek`, `qwen`, `modelscope`, `kimi`, `zhipu`, `ollama`, `vllm`, `local`, and `auto`.
- LLM config is mostly environment-driven: `LLM_MODEL_ID`, `LLM_API_KEY`, `LLM_BASE_URL`, provider-specific API keys, and `LLM_TIMEOUT`.
- `HelloAgentsLLM.invoke()` is non-streaming; `think()` and `stream_invoke()` stream chat completions.
- `hello-agents/HelloAgents/core/agent.py` defines abstract `Agent` with `run()`, `_history`, and message history helpers.
- `hello-agents/HelloAgents/core/message.py` defines Pydantic `Message` with roles `user`, `assistant`, `system`, and `tool`.
- `hello-agents/HelloAgents/core/config.py` defines lightweight runtime config via Pydantic.

## Agent Implementations

- `agents/simple_agent.py`: conversational agent with optional text-marker tool calls using `[TOOL_CALL:{tool}:{parameters}]`; when a `memory` tool is registered it also calls `memory.auto_record_conversation()` after successful responses.
- `agents/react_agent.py`: ReAct loop using `Thought:` and `Action:` lines, dispatching tools via `ToolRegistry.execute_tool`.
- `agents/plan_solve_agent.py`: `Planner` parses an LLM-produced Python list with `ast.literal_eval`; `Executor` runs steps sequentially.
- `agents/reflection_agent.py`: iterative initial/reflect/refine loop with an internal short-term `Memory` trajectory.
- `agents/__init__.py` imports optional external classes from `autogen_core` and `langchain_classic`, so importing `agents` can fail if those packages are absent.

## Tool System

- `tools/base.py` defines abstract `Tool` and `ToolParameter`.
- `tools/registry.py` defines `ToolRegistry`, supporting both `Tool` objects and direct function tools.
- `ToolRegistry.execute_tool(name, input_text)` wraps object tools by passing `{"input": input_text}`.
- `tools/chain.py` supports sequential tool chains using string templates over prior outputs.
- `tools/async_executor.py` runs tool calls in a `ThreadPoolExecutor` via asyncio wrappers.
- Built-in tools:
  - `tools/builtin/calculator.py`: safe-ish AST math calculator named `python_calculator`.
  - `tools/builtin/search.py`: Tavily/SerpApi hybrid web search using `TAVILY_API_KEY` and/or `SERPAPI_API_KEY`.
  - `tools/builtin/web_browser.py`: requests + BeautifulSoup text extraction from a URL.
  - `tools/builtin/memory_tool.py`: tool facade over the memory subsystem.
  - `tools/builtin/rag_tool.py`: tool facade over the RAG pipeline.

## Memory Architecture

- Memory subsystem root is `hello-agents/HelloAgents/mem`.
- `mem/base.py` defines `MemoryItem`, `MemoryConfig`, and abstract `BaseMemory`.
- `mem/manager.py` coordinates enabled memory types and exposes add/retrieve/update/remove/forget/consolidate/stats.
- Working memory (`mem/types/working.py`) is in-memory only, capacity and TTL bounded, and retrieves via TF-IDF/keyword scoring.
- Episodic memory (`mem/types/episodic.py`) uses an in-memory episode cache, SQLite authoritative store, and Qdrant vector index.
- Semantic memory (`mem/types/semantic.py`) combines embeddings, Qdrant vector search, spaCy entity extraction, and Neo4j graph storage.
- Perceptual memory (`mem/types/perceptual.py`) supports text/image/audio/video metadata; text embeddings use the unified embedder, images/audio use deterministic hash vectors by default. CLIP/CLAP are opt-in via `PERCEPTUAL_ENABLE_CLIP=1` / `PERCEPTUAL_ENABLE_CLAP=1`, and `PERCEPTUAL_MODEL_LOCAL_ONLY` defaults to local-only loading.
- `mem/storage/document_store.py` implements SQLite storage for users, memories, concepts, and relationships.
- `mem/storage/qdrant_store.py` implements Qdrant vector storage and a connection manager keyed by URL/collection/dimension. Its search path supports both older `client.search(...)` and newer `client.query_points(...)` qdrant-client APIs. If an existing Qdrant collection has a different vector dimension from the active embedder, it automatically switches to a dimension-suffixed collection such as `rag_knowledge_base_dim384`.
- `mem/storage/neo4j_store.py` implements Neo4j entity and relationship storage.
- `mem/embedding.py` provides global embedding model selection: `EMBED_MODEL_TYPE` (`dashscope`, `local`, `tfidf`), `EMBED_MODEL_NAME`, `EMBED_API_KEY`, and `EMBED_BASE_URL`.

## RAG Architecture

- `mem/rag/document.py` defines simple `Document`, `DocumentChunk`, and `DocumentProcessor`.
- `mem/rag/pipeline.py` is the main RAG implementation:
  - Converts supported documents through MarkItDown when installed.
  - Has enhanced PDF cleanup before chunking.
  - Splits markdown-aware chunks with heading paths and character offsets.
  - Indexes chunks into Qdrant with metadata tags such as `memory_type=rag_chunk`, `is_rag_data=True`, and `rag_namespace`.
  - Supports query embedding, vector search, expanded search via MQE/HyDE, optional cross-encoder reranking, graph-like neighbor/proximity signals, and snippet merging.
- `tools/builtin/rag_tool.py` exposes RAG actions: `add_document`, `add_text`, `ask`, `search`, `stats`, and `clear`.

## Configuration And External Services

- `.env` is loaded by several examples and by `core/database_config.py`.
- LLM calls require OpenAI-compatible API credentials unless using local providers.
- Embeddings may require DashScope API, local sentence-transformers/transformers, or TF-IDF setup.
- Qdrant defaults to `localhost:6333` unless `QDRANT_URL` / `QDRANT_API_KEY` are configured.
- Neo4j defaults to `bolt://localhost:7687`, username `neo4j`, password `hello-agents-password`.
- Search tools require Tavily and/or SerpApi API keys plus dependencies.

## Known Codebase Risks

- There is no dependency manifest (`requirements.txt`, `pyproject.toml`, etc.) in the inspected tree.
- `mem/manager.py` imports `mem.core.store.MemoryStore` and `mem.core.retriever.MemoryRetriever`, but no `mem/core` directory exists; those imports currently look unused but can break importing `mem`.
- Several tests/examples pass `app_id=os.getenv("API_KEY")` into `HelloAgentsLLM`; current constructor expects `api_key`, so `app_id` is ignored as an extra kwarg.
- `RAGTool._init_components()` also passes `app_id` and uses env names `MODEL_ID/API_KEY/BASE_URL`, while `HelloAgentsLLM` primarily expects `LLM_MODEL_ID/LLM_API_KEY/LLM_BASE_URL` or explicit `api_key`.
- `agents/simple_agent.py` convenience methods reference `ToolRegistry.unregister_tool` and `self.tool_registry.tools`, but the registry currently has `unregister()` and private `_tools`.
- `EpisodicMemory.get_all()` references `episode.metadata`, but `Episode` instances define `context`, not `metadata`.
- `PerceptualMemory.update()` has a stale `self.vector_store.add_vectors` reference even though stores are kept in `self.vector_stores` by modality.
- `core/database_config.py validate_connections()` imports from `..memory.storage...`, but this repo uses `mem.storage`.
- `build_graph_from_chunks()` in `mem/rag/pipeline.py` calls `neo4j.add_relationship(from_id=..., to_id=..., rel_type=...)`, but `Neo4jGraphStore.add_relationship()` expects `from_entity_id`, `to_entity_id`, and `relationship_type`.
- Importing `tools.builtin.calculator` currently triggers `tools/__init__.py` and `tools/builtin/__init__.py`, which eagerly import memory/RAG tools; this can cause circular/import failures even for lightweight calculator usage.
