# Agent API

当前 Agent 实现位于 `agents/`，公共基类位于 `core.agent.Agent`。

```python
from agents import SimpleAgent, ReActAgent, ReflectionAgent, PlanSolveAgent
from core import Agent, Config, HelloAgentsLLM, Message
```

## Agent 基类

```python
class Agent:
    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: str | None = None,
        config: Config | None = None,
        tool_registry: ToolRegistry | None = None,
    )

    def run(self, input_text: str, **kwargs) -> str
    def add_message(self, message: Message)
    def clear_history(self)
    def get_history(self) -> list[Message]
```

基类集成能力：

- `HistoryManager`：历史管理和自动压缩。
- `TokenCounter`：增量 token 统计。
- `ObservationTruncator`：长工具输出截断。
- `TraceLogger`：JSONL/HTML 轨迹。
- `SessionStore`：会话保存与恢复。
- `SkillLoader`：Skills 知识外化。
- `TaskTool`：子代理机制。
- `TodoWriteTool`、`DevLogTool`：进度和决策记录。

## SimpleAgent

基础对话 Agent，可选 Function Calling 工具调用。

```python
class SimpleAgent(Agent):
    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: str | None = None,
        config: Config | None = None,
        tool_registry: ToolRegistry | None = None,
        enable_tool_calling: bool = True,
        max_tool_iterations: int = 3,
    )
```

示例：

```python
from agents import SimpleAgent
from core import HelloAgentsLLM

agent = SimpleAgent(
    name="assistant",
    llm=HelloAgentsLLM(),
    system_prompt="你是一个简洁的中文助手。",
)

print(agent.run("解释一下什么是 Agent"))
```

带工具：

```python
from agents import SimpleAgent
from core import HelloAgentsLLM
from tools import ToolRegistry
from tools.builtin import CalculatorTool

registry = ToolRegistry()
registry.register_tool(CalculatorTool())

agent = SimpleAgent(
    "assistant",
    HelloAgentsLLM(),
    tool_registry=registry,
)

print(agent.run("计算 8 * 9"))
```

## ReActAgent

基于 Function Calling 的推理与行动 Agent。默认会使用结构化工具调用，不再依赖正则解析 `Action:` 文本。

```python
class ReActAgent(Agent):
    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        tool_registry: ToolRegistry | None = None,
        system_prompt: str | None = None,
        config: Config | None = None,
        max_steps: int = 5,
    )
```

示例：

```python
from agents import ReActAgent
from core import HelloAgentsLLM
from tools import ToolRegistry
from tools.builtin import ReadTool, CalculatorTool

registry = ToolRegistry()
registry.register_tool(ReadTool())
registry.register_tool(CalculatorTool())

agent = ReActAgent(
    name="react",
    llm=HelloAgentsLLM(),
    tool_registry=registry,
    max_steps=5,
)

print(agent.run("读取 README.md 并总结要点"))
```

## ReflectionAgent

适合代码生成、文档写作、分析报告等需要反思和优化的任务。支持可选工具调用。

```python
class ReflectionAgent(Agent):
    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: str | None = None,
        config: Config | None = None,
        max_iterations: int = 3,
        tool_registry: ToolRegistry | None = None,
        enable_tool_calling: bool = True,
        max_tool_iterations: int = 3,
    )
```

示例：

```python
from agents import ReflectionAgent
from core import HelloAgentsLLM

agent = ReflectionAgent(
    name="writer",
    llm=HelloAgentsLLM(),
    max_iterations=2,
)

print(agent.run("写一段项目介绍，并自我检查是否清晰"))
```

## PlanSolveAgent / PlanAndSolveAgent

先生成计划，再逐步执行计划。`PlanAndSolveAgent` 是兼容旧名称的别名。

```python
from agents import PlanSolveAgent, PlanAndSolveAgent

assert PlanAndSolveAgent is PlanSolveAgent
```

常用示例：

```python
from agents import PlanSolveAgent
from core import HelloAgentsLLM

agent = PlanSolveAgent("planner", HelloAgentsLLM())
print(agent.run("设计一个小型 RAG 系统的实施方案"))
```

## 子代理模式

任意继承 `Agent` 的对象都可以使用 `run_as_subagent()` 以隔离历史执行子任务：

```python
from tools.tool_filter import ReadOnlyFilter

result = agent.run_as_subagent(
    task="只读取代码并总结模块结构",
    tool_filter=ReadOnlyFilter(),
    return_summary=True,
)

print(result["summary"])
print(result["metadata"])
```

返回结构：

```python
{
    "success": True,
    "summary": "...",
    "metadata": {
        "steps": 2,
        "tokens": 120,
        "duration_seconds": 1.2,
        "tools_used": ["Read"],
    },
}
```

## 历史和压缩

```python
from core import Config

config = Config(
    context_window=8000,
    compression_threshold=0.8,
    min_retain_rounds=3,
    enable_smart_compression=False,
)
```

当历史 token 数超过 `context_window * compression_threshold` 后，Agent 会压缩旧历史并保留最近 `min_retain_rounds` 轮完整对话。

## 异步接口

基类提供：

```python
result = await agent.arun("任务")

async for event in agent.arun_stream("任务"):
    print(event.type, event.data)
```

具体 Agent 可根据自身能力覆盖异步和流式实现。
