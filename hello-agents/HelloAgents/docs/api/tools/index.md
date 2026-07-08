# Tools API

工具系统由 `Tool`、`ToolRegistry` 和 `ToolResponse` 三个核心对象组成。

```python
from tools import Tool, ToolParameter, ToolRegistry, ToolResponse, ToolStatus
```

## Tool

所有标准工具继承 `tools.base.Tool`：

```python
class Tool:
    def __init__(self, name: str, description: str, expandable: bool = False)
    def run(self, parameters: dict) -> ToolResponse
    def get_parameters(self) -> list[ToolParameter]
    def run_with_timing(self, parameters: dict) -> ToolResponse
```

最小工具示例：

```python
from typing import Any

from tools import Tool, ToolParameter, ToolResponse


class EchoTool(Tool):
    def __init__(self):
        super().__init__(name="echo", description="原样返回输入")

    def get_parameters(self):
        return [
            ToolParameter(
                name="text",
                type="string",
                description="要返回的文本",
                required=True,
            )
        ]

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        return ToolResponse.success(
            text=parameters["text"],
            data={"echo": parameters["text"]},
        )
```

## ToolResponse

工具必须返回 `ToolResponse`：

```python
ToolResponse.success(text="完成", data={"value": 1})
ToolResponse.partial(text="输出已截断", data={"preview": "..."})
ToolResponse.error(code="INVALID_PARAM", message="参数错误")
```

字段：

| 字段 | 说明 |
| --- | --- |
| `status` | `success`、`partial`、`error` |
| `text` | 给 LLM 阅读的文本 |
| `data` | 结构化数据 |
| `error_info` | 错误码和错误消息 |
| `stats` | 运行统计，如 `time_ms` |
| `context` | 调试上下文，如输入参数和工具名 |

## ToolRegistry

```python
registry = ToolRegistry()
registry.register_tool(EchoTool())

response = registry.execute_tool("echo", '{"text": "hello"}')
print(response.status, response.text)
```

常用方法：

| 方法 | 说明 |
| --- | --- |
| `register_tool(tool, auto_expand=True)` | 注册标准工具 |
| `register_function(func, name=None, description=None)` | 注册函数工具 |
| `unregister(name)` | 注销工具 |
| `get_tool(name)` | 获取工具对象 |
| `execute_tool(name, input_text)` | 执行工具，返回 `ToolResponse` |
| `get_tools_description()` | 生成 prompt 用工具描述 |
| `list_tools()` | 列出工具名 |
| `get_all_tools()` | 获取工具对象列表 |

函数工具：

```python
def reverse_text(input_text: str) -> str:
    """反转文本"""
    return input_text[::-1]

registry = ToolRegistry()
registry.register_function(reverse_text)
print(registry.execute_tool("reverse_text", "abc").text)
```

## 可展开工具

`Tool` 支持 `expandable=True` 和 `@tool_action`，一个工具类可以展开为多个子工具：

```python
from tools import Tool, tool_action


class DatabaseTool(Tool):
    def __init__(self):
        super().__init__(
            name="database",
            description="数据库工具",
            expandable=True,
        )

    @tool_action("db_query", "查询数据库")
    def query(self, sql: str) -> str:
        return f"query: {sql}"
```

注册时默认会自动展开。

## 内置工具

| 工具类 | 工具名 | 说明 |
| --- | --- | --- |
| `CalculatorTool` | `python_calculator` | 安全 AST 数学计算 |
| `ReadTool` | `Read` | 文件读取，缓存元数据用于乐观锁 |
| `WriteTool` | `Write` | 文件写入，支持乐观锁字段 |
| `EditTool` | `Edit` | 精确替换 |
| `MultiEditTool` | `MultiEdit` | 批量精确替换 |
| `TodoWriteTool` | `TodoWrite` | 任务列表管理 |
| `DevLogTool` | `DevLog` | 开发日志和决策记录 |
| `TaskTool` | `Task` | 子代理任务工具 |
| `SkillTool` | `Skill` | Skills 知识加载 |
| `MemoryTool` | `memory` | 记忆系统工具 |
| `RAGTool` | `rag` | 文档索引与检索增强生成 |
| `SearchTool` | `search` | 搜索工具 |
| `WebBrowserTool` | `web_browser` | 网页读取工具 |
| `MCPTool` | 由实例配置 | MCP 工具包装 |
| `A2ATool` | 由实例配置 | A2A Agent 通信 |
| `ANPTool` | 由实例配置 | ANP 网络协议 |
| `BFCLEvaluationTool` | `bfcl_evaluation` | BFCL 评测 |
| `GAIAEvaluationTool` | `gaia_evaluation` | GAIA 评测 |
| `LLMJudgeTool` | `llm_judge_evaluation` | LLM Judge 评测 |
| `WinRateTool` | `win_rate_evaluation` | Win-rate 评测 |
| `RLTrainingTool` | `rl_training` | RL 训练入口 |

## 在 Agent 中使用

```python
from agents import ReActAgent
from core import HelloAgentsLLM
from tools import ToolRegistry
from tools.builtin import CalculatorTool, ReadTool

registry = ToolRegistry()
registry.register_tool(CalculatorTool())
registry.register_tool(ReadTool())

agent = ReActAgent(
    name="tool-agent",
    llm=HelloAgentsLLM(),
    tool_registry=registry,
)

print(agent.run("读取 README.md，并计算 12*12"))
```

## 熔断器

`ToolRegistry` 默认带 `CircuitBreaker`。连续失败后，工具会临时熔断并返回 `CIRCUIT_OPEN` 错误响应。

关闭或自定义熔断器见 [熔断器机制使用指南](../../circuit-breaker-guide.md)。

## 工具过滤

子代理可用 `ToolFilter` 限制工具集合：

```python
from tools.tool_filter import ReadOnlyFilter

result = agent.run_as_subagent(
    task="只读分析项目",
    tool_filter=ReadOnlyFilter(),
)
```

内置过滤器：

- `ReadOnlyFilter`
- `FullAccessFilter`
- `CustomFilter`
