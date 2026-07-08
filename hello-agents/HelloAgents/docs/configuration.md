# 配置说明

HelloAgents 的配置分为两层：

- LLM 连接配置：由 `HelloAgentsLLM` 读取构造参数或环境变量。
- 框架运行配置：由 `core.config.Config` 控制 Agent、工具、上下文、Trace、Session 等行为。

## LLM 连接配置

推荐 `.env`：

```bash
LLM_MODEL_ID=your-model
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://your-openai-compatible-endpoint/v1
LLM_TIMEOUT=60
```

兼容旧变量：

```bash
MODEL_ID=your-model
API_KEY=your-api-key
BASE_URL=https://your-openai-compatible-endpoint/v1
```

代码中也可以显式传入：

```python
from core import HelloAgentsLLM

llm = HelloAgentsLLM(
    model="your-model",
    api_key="your-api-key",
    base_url="https://your-openai-compatible-endpoint/v1",
    provider="openai",
)
```

`app_id` 是 `api_key` 的兼容别名：

```python
llm = HelloAgentsLLM(
    model="your-model",
    app_id="your-api-key",
    base_url="https://your-openai-compatible-endpoint/v1",
    provider="openai",
)
```

## Adapter 选择

`HelloAgentsLLM` 根据 `base_url` 创建适配器：

| 适配器 | 适用接口 | 说明 |
| --- | --- | --- |
| `OpenAIAdapter` | OpenAI 兼容接口 | 默认适配器，适用于 OpenAI、DeepSeek、Qwen、Kimi、智谱、vLLM、Ollama 等兼容服务 |
| `AnthropicAdapter` | Anthropic Claude | 需要安装 `anthropic` 可选依赖 |
| `GeminiAdapter` | Google Gemini | 需要安装 `google-genai` 可选依赖 |

`provider` 当前主要用于兼容旧调用和记录，不是强制路由开关；实际适配器以 `base_url` 检测为主。

## Config 总览

```python
from core import Config

config = Config(
    trace_enabled=True,
    session_enabled=True,
    skills_enabled=True,
    subagent_enabled=True,
    todowrite_enabled=True,
    devlog_enabled=True,
)
```

### 上下文压缩

```python
config = Config(
    context_window=128000,
    compression_threshold=0.8,
    min_retain_rounds=10,
    enable_smart_compression=False,
)
```

- `context_window`：估算上下文窗口大小。
- `compression_threshold`：达到窗口比例后触发压缩。
- `min_retain_rounds`：压缩后保留最近几轮完整对话。
- `enable_smart_compression`：是否调用 LLM 生成结构化摘要。

智能摘要配置：

```python
config = Config(
    enable_smart_compression=True,
    summary_llm_provider="openai",
    summary_llm_model="your-summary-model",
    summary_max_tokens=800,
    summary_temperature=0.3,
)
```

### 工具输出截断

```python
config = Config(
    tool_output_max_lines=2000,
    tool_output_max_bytes=51200,
    tool_output_dir="tool-output",
    tool_output_truncate_direction="head",
)
```

当工具输出过长时，Agent 会把完整输出保存到 `tool_output_dir`，并将截断摘要放回上下文。

### Trace 与可观测性

```python
config = Config(
    trace_enabled=True,
    trace_dir="memory/traces",
    trace_sanitize=True,
    trace_html_include_raw_response=False,
)
```

默认产物：

```text
memory/traces/trace-*.jsonl
memory/traces/trace-*.html
```

### 会话持久化

```python
config = Config(
    session_enabled=True,
    session_dir="memory/sessions",
    auto_save_enabled=False,
    auto_save_interval=10,
)
```

手动保存：

```python
agent.save_session("my-session")
agent.load_session("memory/sessions/my-session.json")
```

### Skills

```python
config = Config(
    skills_enabled=True,
    skills_dir="skills",
    skills_auto_register=True,
)
```

当 Agent 有 `tool_registry` 时，`SkillTool` 可自动注册。

### 子代理

```python
config = Config(
    subagent_enabled=True,
    subagent_max_steps=15,
    subagent_use_light_llm=False,
    subagent_light_llm_provider="openai",
    subagent_light_llm_model="your-light-model",
)
```

当 Agent 有 `tool_registry` 时，`TaskTool` 可自动注册。

### TodoWrite 与 DevLog

```python
config = Config(
    todowrite_enabled=True,
    todowrite_persistence_dir="memory/todos",
    devlog_enabled=True,
    devlog_persistence_dir="memory/devlogs",
)
```

这两个工具会在传入 `tool_registry` 时自动注册。测试某个固定工具集合时，可以显式关闭它们：

```python
config = Config(
    todowrite_enabled=False,
    devlog_enabled=False,
)
```

### 异步与流式

```python
config = Config(
    async_enabled=True,
    max_concurrent_tools=3,
    hook_timeout_seconds=5.0,
    llm_async_timeout=120,
    tool_async_timeout=30,
    stream_enabled=True,
    stream_buffer_size=100,
    stream_include_thinking=True,
    stream_include_tool_calls=True,
)
```

## Memory/RAG 环境变量

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

感知记忆可选模型默认不主动下载：

```bash
PERCEPTUAL_ENABLE_CLIP=0
PERCEPTUAL_ENABLE_CLAP=0
PERCEPTUAL_MODEL_LOCAL_ONLY=1
```

## 推荐开发配置

本地调试时，如果不需要持久化和 trace，可降低运行产物：

```python
config = Config(
    trace_enabled=False,
    session_enabled=False,
    auto_save_enabled=False,
    todowrite_enabled=False,
    devlog_enabled=False,
)
```

做真实 Agent 验证时，保留 Trace 更方便排查：

```python
config = Config(
    trace_enabled=True,
    trace_dir="memory/traces",
    trace_sanitize=True,
)
```
