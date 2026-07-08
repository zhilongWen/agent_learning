# 导入路径迁移说明

当前目标项目采用顶层包布局，不再保留 upstream 的独立 `hello_agents/` 包目录。部分历史教程、恢复文档或上游 API 示例仍可能出现 `hello_agents.*` 导入；在当前工作区中运行时，请按本文映射。

## 运行前提

将当前项目根目录加入 `PYTHONPATH`：

```bash
export PYTHONPATH=/Users/wenzhilong/space/warehouse/agent_learning/hello-agents/HelloAgents
```

## 常用映射

| 旧写法 | 当前写法 |
| --- | --- |
| `from hello_agents import SimpleAgent` | `from agents import SimpleAgent` |
| `from hello_agents import ReActAgent` | `from agents import ReActAgent` |
| `from hello_agents import ReflectionAgent` | `from agents import ReflectionAgent` |
| `from hello_agents import PlanAndSolveAgent` | `from agents import PlanAndSolveAgent` |
| `from hello_agents import HelloAgentsLLM` | `from core import HelloAgentsLLM` |
| `from hello_agents import Config` | `from core import Config` |
| `from hello_agents import Message` | `from core import Message` |
| `from hello_agents import ToolRegistry` | `from tools import ToolRegistry` |
| `from hello_agents.tools import Tool` | `from tools import Tool` |
| `from hello_agents.tools.builtin import ReadTool` | `from tools.builtin import ReadTool` |
| `from hello_agents.core.lifecycle import AgentEvent` | `from core.lifecycle import AgentEvent` |
| `from hello_agents.context import HistoryManager` | `from context.history import HistoryManager` |
| `from hello_agents.observability import TraceLogger` | `from observability import TraceLogger` |
| `from hello_agents.skills import SkillLoader` | `from skills import SkillLoader` |
| `from hello_agents.protocols.mcp.client import MCPClient` | `from protocols.mcp.client import MCPClient` |
| `from hello_agents.rl import ...` | `from rl import ...` |
| `from hello_agents.memory import ...` | `from mem import ...` |

## 示例迁移

旧示例：

```python
from hello_agents import ReActAgent, HelloAgentsLLM, ToolRegistry
from hello_agents.tools.builtin import ReadTool

llm = HelloAgentsLLM()
registry = ToolRegistry()
registry.register_tool(ReadTool())
agent = ReActAgent("assistant", llm, registry)
```

当前写法：

```python
from agents import ReActAgent
from core import HelloAgentsLLM
from tools import ToolRegistry
from tools.builtin import ReadTool

llm = HelloAgentsLLM()
registry = ToolRegistry()
registry.register_tool(ReadTool())
agent = ReActAgent("assistant", llm, tool_registry=registry)
```

## 记忆包迁移

当前项目已将 upstream `hello_agents/memory` 合并到本地 `mem` 包：

```python
from mem import MemoryManager, MemoryConfig
from tools.builtin import MemoryTool, RAGTool
```

不要再新增运行时代码到 `memory/` 包。`memory/` 目录如果出现，通常是测试或示例产生的运行产物，例如 `memory/traces`。

## 文档状态说明

- `docs/README.md`、`docs/current-architecture.md`、`docs/configuration.md`、`docs/testing-and-validation.md` 和 `docs/api/**` 的入口页已按当前布局更新。
- `docs/post-v0.2.3-*` 是集成记录，里面出现的 `hello_agents/*` 多数表示 upstream 原始路径，不应机械替换。
- `docs/v1.md`、`docs/v2.md` 和部分教程页保留较多 upstream 示例，运行前请按本文映射导入路径。
