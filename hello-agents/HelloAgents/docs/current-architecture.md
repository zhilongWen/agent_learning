# 当前架构总览

本文描述 `/Users/wenzhilong/space/warehouse/agent_learning/hello-agents/HelloAgents` 当前集成版的模块结构和运行关系。

## 项目形态

当前项目是一个顶层包布局的 Python Agent 框架，主要模块直接位于项目根目录：

```text
HelloAgents/
├── agents/          # Agent 范式实现
├── core/            # LLM、Agent 基类、配置、消息、生命周期、会话
├── context/         # 历史压缩、Token 计数、上下文构建、工具输出截断
├── tools/           # 工具协议、注册表、内置工具、熔断器、工具过滤
├── mem/             # 记忆系统与 RAG，已合并原 upstream memory 包
├── observability/   # TraceLogger，可输出 JSONL 和 HTML
├── skills/          # SkillLoader 与内置 Skills 目录
├── protocols/       # MCP/A2A/ANP 协议实现与工具包装
├── evaluation/      # BFCL、GAIA、数据生成等评测模块
├── rl/              # RL 数据集、奖励函数、训练器和工具
├── examples/        # 示例脚本
├── test/            # 当前测试目录
└── docs/            # 文档
```

当前目标项目不再保留单独的 `hello_agents/` 包目录。运行本地代码时通常需要将项目根加入 `PYTHONPATH`：

```bash
export PYTHONPATH=/Users/wenzhilong/space/warehouse/agent_learning/hello-agents/HelloAgents
```

## 核心数据流

典型 `Agent.run()` 流程如下：

```text
用户输入
  ↓
Agent 构造 messages
  ↓
HelloAgentsLLM 调用模型
  ↓
可选 Function Calling 工具调用
  ↓
ToolRegistry 执行 Tool.run_with_timing()
  ↓
ToolResponse 写回模型上下文
  ↓
Agent 保存历史、Trace、Session 元数据
  ↓
最终答案
```

## Core 层

- `core/llm.py`：`HelloAgentsLLM`，统一 LLM 入口。
- `core/llm_adapters.py`：OpenAI 兼容、Anthropic、Gemini 三类适配器。
- `core/llm_response.py`：`LLMResponse`、`LLMToolResponse`、`ToolCall`、`StreamStats`。
- `core/agent.py`：`Agent` 基类，集成历史压缩、工具 schema、子代理、Session、Trace、Skills、TodoWrite、DevLog。
- `core/config.py`：`Config`，集中配置上下文、工具、会话、Trace、Skills、流式和异步行为。
- `core/message.py`：`Message`，支持 `user/assistant/system/tool/summary` 角色。
- `core/session_store.py`：会话保存、恢复和一致性检查。
- `core/lifecycle.py`、`core/streaming.py`：异步生命周期和流式事件。

## Agent 层

- `SimpleAgent`：基础对话 Agent，支持可选 Function Calling 工具调用。
- `ReActAgent`：基于 Function Calling 的推理与行动 Agent，内置 `Thought` 和 `Finish` 语义。
- `ReflectionAgent`：初稿、反思、优化的迭代 Agent，可选工具调用。
- `PlanSolveAgent` / `PlanAndSolveAgent`：先规划再逐步执行。
- `FunctionCallAgent`、`ToolAwareAgent`：保留的历史/兼容实现。
- `agents/factory.py`：子代理工厂，供 `TaskTool` 使用。

## Tool 层

工具系统以 `ToolResponse` 为统一协议：

- `tools/base.py`：`Tool`、`ToolParameter`、`tool_action`。
- `tools/registry.py`：`ToolRegistry`，负责注册、执行、熔断保护、函数工具兼容。
- `tools/response.py`：`success/partial/error` 三态响应。
- `tools/errors.py`：标准错误码。
- `tools/circuit_breaker.py`：按工具维度熔断连续失败。
- `tools/tool_filter.py`：子代理场景下的工具访问控制。

常用内置工具包括：

- 文件：`Read`、`Write`、`Edit`、`MultiEdit`
- 任务：`Task`、`TodoWrite`、`DevLog`
- 知识：`Skill`、`memory`、`rag`
- 搜索与浏览：`search`、`web_browser`
- 协议：`MCPTool`、`A2ATool`、`ANPTool`
- 评测与训练：`bfcl_evaluation`、`gaia_evaluation`、`llm_judge_evaluation`、`win_rate_evaluation`、`rl_training`

## Context 层

`context/` 负责让长任务可控：

- `HistoryManager`：按轮次压缩历史，生成 `summary` 消息并保留最近 N 轮。
- `TokenCounter`：缓存消息 Token 数，支持增量统计。
- `ObservationTruncator`：截断超长工具输出，并将完整输出保存到 `tool-output/`。
- `ContextBuilder`：整理系统提示词、历史、工具结果和额外上下文。

压缩触发条件来自：

```python
Config.context_window * Config.compression_threshold
```

超过阈值后，`Agent.add_message()` 会触发 `_compress_history()`。

## Memory 与 RAG

当前只保留 `mem/` 作为记忆系统包：

- `mem/manager.py`：统一管理工作记忆、情景记忆、语义记忆、感知记忆。
- `mem/types/working.py`：短期工作记忆。
- `mem/types/episodic.py`：情景记忆，结合 SQLite 与向量检索。
- `mem/types/semantic.py`：语义记忆，结合 Qdrant 与 Neo4j。
- `mem/types/perceptual.py`：多模态感知记忆，CLIP/CLAP 默认不自动下载。
- `mem/storage/`：SQLite、Qdrant、Neo4j 存储适配。
- `mem/rag/`：文档处理、分块、向量索引、扩展查询、重排和片段合并。

工具入口是 `tools.builtin.MemoryTool` 和 `tools.builtin.RAGTool`。

## 外部依赖与配置

基础 LLM 配置：

```bash
LLM_MODEL_ID=your-model
LLM_API_KEY=your-key
LLM_BASE_URL=https://your-openai-compatible-endpoint/v1
LLM_TIMEOUT=60
```

兼容旧变量：

```bash
MODEL_ID=your-model
API_KEY=your-key
BASE_URL=https://your-openai-compatible-endpoint/v1
```

可选服务：

- Qdrant：`QDRANT_URL`、`QDRANT_API_KEY`
- Neo4j：`NEO4J_URI`、`NEO4J_USER`、`NEO4J_PASSWORD`
- Embedding：`EMBED_MODEL_TYPE`、`EMBED_MODEL_NAME`、`EMBED_API_KEY`、`EMBED_BASE_URL`
- 搜索：`TAVILY_API_KEY`、`SERPAPI_API_KEY`

## 默认运行产物

- Trace：`memory/traces/*.jsonl`、`memory/traces/*.html`
- Session：`memory/sessions/*.json`
- TodoWrite：`memory/todos/*`
- DevLog：`memory/devlogs/*`
- 长工具输出：`tool-output/*`

如不希望测试或示例写入这些目录，可以在 `Config` 中关闭对应能力或改写目录。

## 关键兼容点

- `PlanAndSolveAgent` 是 `PlanSolveAgent` 的兼容别名。
- `HelloAgentsLLM` 支持 `app_id` 作为 `api_key` 的兼容参数。
- `test/conftest.py` 会加载最近的 `.env`，并将 `MODEL_ID/API_KEY/BASE_URL` 映射到 `LLM_MODEL_ID/LLM_API_KEY/LLM_BASE_URL`。
- `mem` 是当前记忆系统包；不要再新增 `memory` 运行时代码路径。
