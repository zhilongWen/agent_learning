# HelloAgents API 总览

当前 API 文档对应 `/Users/wenzhilong/space/warehouse/agent_learning/hello-agents/HelloAgents` 的集成版代码。项目采用顶层包布局，常用导入方式如下：

```python
from agents import SimpleAgent, ReActAgent, ReflectionAgent, PlanSolveAgent
from core import HelloAgentsLLM, Config, Message
from tools import ToolRegistry, ToolResponse
```

## 快速导航

| 模块 | 文档 | 说明 |
| --- | --- | --- |
| LLM | [core/llm.md](./core/llm.md) | `HelloAgentsLLM`、三类 adapter、流式与 Function Calling |
| Agent | [agents/index.md](./agents/index.md) | `SimpleAgent`、`ReActAgent`、`ReflectionAgent`、`PlanSolveAgent` |
| Tools | [tools/index.md](./tools/index.md) | `Tool`、`ToolRegistry`、`ToolResponse`、内置工具 |
| Memory/RAG | [memory/index.md](./memory/index.md) | `mem` 包、`MemoryTool`、`RAGTool` |
| Protocols | [protocols/README.md](./protocols/README.md) | MCP、A2A、ANP |
| RL | [rl/README.md](./rl/README.md) | 数据集、奖励、训练器、训练工具 |

## 核心对象

| 对象 | 路径 | 作用 |
| --- | --- | --- |
| `HelloAgentsLLM` | `core.llm` | 统一 LLM 客户端 |
| `LLMResponse` | `core.llm_response` | 非流式响应对象 |
| `LLMToolResponse` | `core.llm_response` | Function Calling 响应对象 |
| `Agent` | `core.agent` | Agent 基类 |
| `Config` | `core.config` | 框架运行配置 |
| `Message` | `core.message` | 对话消息模型 |
| `Tool` | `tools.base` | 工具基类 |
| `ToolRegistry` | `tools.registry` | 工具注册与执行入口 |
| `ToolResponse` | `tools.response` | 工具标准返回协议 |
| `MemoryManager` | `mem.manager` | 统一记忆管理入口 |

## 最小示例

### 基础对话

```python
from agents import SimpleAgent
from core import HelloAgentsLLM

llm = HelloAgentsLLM()
agent = SimpleAgent("assistant", llm)

print(agent.run("你好，请介绍一下自己"))
```

### 工具调用

```python
from agents import ReActAgent
from core import HelloAgentsLLM
from tools import ToolRegistry
from tools.builtin import CalculatorTool

llm = HelloAgentsLLM()
registry = ToolRegistry()
registry.register_tool(CalculatorTool())

agent = ReActAgent("tool-agent", llm, tool_registry=registry)
print(agent.run("计算 123 * 456"))
```

### 带配置的 Agent

```python
from agents import SimpleAgent
from core import Config, HelloAgentsLLM

config = Config(
    trace_enabled=True,
    context_window=8000,
    compression_threshold=0.8,
    min_retain_rounds=3,
)

agent = SimpleAgent("assistant", HelloAgentsLLM(), config=config)
```

## 配置入口

LLM 推荐环境变量：

```bash
LLM_MODEL_ID=your-model
LLM_API_KEY=your-key
LLM_BASE_URL=https://your-openai-compatible-endpoint/v1
```

兼容旧变量：

```bash
MODEL_ID=your-model
API_KEY=your-key
BASE_URL=https://your-openai-compatible-endpoint/v1
```

更多配置见 [配置说明](../configuration.md)。

## 当前测试状态

完整测试目录：

```text
/Users/wenzhilong/space/warehouse/agent_learning/hello-agents/HelloAgents/test
```

最近一次验证：`270 passed, 6 skipped, 10 warnings`。详见 [测试与验证指南](../testing-and-validation.md)。
