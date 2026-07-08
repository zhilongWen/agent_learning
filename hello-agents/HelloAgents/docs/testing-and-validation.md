# 测试与验证指南

本文说明当前 `HelloAgents/test` 目录的运行方式、依赖配置和常见失败处理。

## 测试环境

当前验证使用的 Python：

```bash
/Users/wenzhilong/miniconda3/envs/myenv3.12/bin/python
```

运行前建议设置 `PYTHONPATH`：

```bash
export PYTHONPATH=/Users/wenzhilong/space/warehouse/agent_learning/hello-agents/HelloAgents
```

测试目录：

```text
/Users/wenzhilong/space/warehouse/agent_learning/hello-agents/HelloAgents/test
```

## 完整测试命令

```bash
PYTHONPATH=/Users/wenzhilong/space/warehouse/agent_learning/hello-agents/HelloAgents \
/Users/wenzhilong/miniconda3/envs/myenv3.12/bin/python -m pytest \
/Users/wenzhilong/space/warehouse/agent_learning/hello-agents/HelloAgents/test -q
```

最近一次完整结果：

```text
270 passed, 6 skipped, 10 warnings
```

## 环境变量

`test/conftest.py` 会向上查找最近的 `.env` 并加载。推荐使用：

```bash
LLM_MODEL_ID=your-model
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://your-openai-compatible-endpoint/v1
LLM_TIMEOUT=60
```

也兼容旧变量：

```bash
MODEL_ID=your-model
API_KEY=your-api-key
BASE_URL=https://your-openai-compatible-endpoint/v1
```

如果只运行不依赖真实 LLM 的测试，可以选择更小的子集，例如：

```bash
PYTHONPATH=/Users/wenzhilong/space/warehouse/agent_learning/hello-agents/HelloAgents \
/Users/wenzhilong/miniconda3/envs/myenv3.12/bin/python -m pytest \
/Users/wenzhilong/space/warehouse/agent_learning/hello-agents/HelloAgents/test/test_tool_response_protocol.py \
/Users/wenzhilong/space/warehouse/agent_learning/hello-agents/HelloAgents/test/test_file_tools.py -q
```

## 测试覆盖地图

| 测试文件 | 覆盖能力 |
| --- | --- |
| `test_all_agents.py` | Simple/ReAct/Reflection/PlanSolve Agent 基本真实 LLM 行为 |
| `test_llm_function_calling.py` | Function Calling、工具调用响应 |
| `test_llm_streaming.py` | LLM 流式调用 |
| `test_async_lifecycle.py` | 异步执行、生命周期钩子、流式事件 |
| `test_context_engineering.py` | 历史压缩、Token 计数、工具输出截断 |
| `test_smart_summary.py` | 智能摘要与摘要回退 |
| `test_tool_response_protocol.py` | `ToolResponse` 三态协议 |
| `test_custom_tools.py` | 函数工具、标准工具、可展开工具 |
| `test_file_tools.py` | 文件读写编辑、乐观锁 |
| `test_circuit_breaker.py` | 工具熔断器 |
| `test_subagent_mechanism.py` | `TaskTool`、工具过滤、上下文隔离 |
| `test_todowrite.py` | TodoWrite 工具 |
| `test_devlog_tool.py` | DevLog 工具 |
| `test_session_persistence.py` | 会话保存与恢复 |
| `test_observability.py`、`test_trace_integration.py` | Trace JSONL/HTML |
| `test_skills.py` | Skills 加载与 SkillTool |
| `test_qdrant_store_compat.py` | Qdrant 兼容层 |
| `test_perceptual_memory_optional_models.py` | 感知记忆可选模型加载策略 |
| `test_mcp_protocols.py` | MCP 协议支持 |
| `test_bfcl_benchmark.py`、`test_gaia_benchmark.py`、`test_data_generation_benchmark.py` | 评测模块 |

## 常见失败

### 1. `ModuleNotFoundError`

通常是未设置 `PYTHONPATH`。使用完整命令或先执行：

```bash
export PYTHONPATH=/Users/wenzhilong/space/warehouse/agent_learning/hello-agents/HelloAgents
```

### 2. LLM 连接失败

典型错误：

```text
openai.APIConnectionError: Connection error.
```

检查：

- `.env` 是否已加载。
- `LLM_BASE_URL` 或 `BASE_URL` 是否可访问。
- 当前环境是否允许网络访问。
- 模型名是否仍可用。

### 3. 摘要模型不可用

智能摘要默认配置里有 `summary_llm_model="deepseek-chat"`。如果服务端不再支持该模型，`_generate_smart_summary()` 会回退到简单摘要，并保持摘要格式契约。

如需指定摘要模型：

```python
from core import Config

config = Config(
    enable_smart_compression=True,
    summary_llm_provider="openai",
    summary_llm_model="your-summary-model",
)
```

### 4. 运行产物污染工作区

默认会产生：

```text
memory/traces/
memory/sessions/
memory/todos/
memory/devlogs/
tool-output/
```

测试时可以通过 `Config` 关闭或改写目录：

```python
from core import Config

config = Config(
    trace_enabled=False,
    session_enabled=False,
    auto_save_enabled=False,
    todowrite_persistence_dir="/tmp/hello-agents-todos",
    devlog_persistence_dir="/tmp/hello-agents-devlogs",
)
```

## 当前已知 warnings

- `mem/base.py` 使用 Pydantic v1 风格 `class Config`，在 Pydantic v2 下会有 deprecation warning。
- `tools/builtin/calculator.py` 使用 `ast.Num` 兼容旧 Python，在 Python 3.14 前会提示 deprecation warning。

这两个 warning 不影响当前测试通过。
