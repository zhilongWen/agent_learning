# HelloAgentsLLM API

`HelloAgentsLLM` 是框架的统一 LLM 客户端，位于 `core.llm`。它通过 adapter 层支持 OpenAI 兼容接口、Anthropic Claude 和 Google Gemini，并向 Agent 层提供同步、异步、流式和 Function Calling 能力。

```python
from core import HelloAgentsLLM
```

## 初始化

```python
llm = HelloAgentsLLM(
    model=None,
    api_key=None,
    base_url=None,
    app_id=None,
    provider=None,
    temperature=0.7,
    max_tokens=None,
    timeout=None,
)
```

参数优先级：显式参数 > 环境变量。

| 参数 | 说明 |
| --- | --- |
| `model` | 模型名，默认读取 `LLM_MODEL_ID` 或 `MODEL_ID` |
| `api_key` | API Key，默认读取 `LLM_API_KEY` 或 `API_KEY` |
| `app_id` | `api_key` 的兼容别名 |
| `base_url` | API 地址，默认读取 `LLM_BASE_URL` 或 `BASE_URL` |
| `provider` | 兼容旧调用的提供商标识；实际 adapter 主要由 `base_url` 判断 |
| `temperature` | 默认温度 |
| `max_tokens` | 默认最大输出 token |
| `timeout` | 超时时间，默认读取 `LLM_TIMEOUT`，否则 60 秒 |

## 环境变量

推荐：

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

## Adapter

| Adapter | 选择条件 | 依赖 |
| --- | --- | --- |
| `OpenAIAdapter` | 默认，适用于 OpenAI 兼容接口 | `openai` |
| `AnthropicAdapter` | `base_url` 指向 Anthropic/Claude 服务 | `anthropic` |
| `GeminiAdapter` | `base_url` 指向 Google Gemini 服务 | `google-genai` |

OpenAI 兼容接口覆盖 OpenAI、DeepSeek、Qwen、Kimi、智谱、vLLM、Ollama、SGLang 等提供 Chat Completions 兼容格式的服务。

## 非流式调用

```python
response = llm.invoke([
    {"role": "user", "content": "你好"}
])

print(response.content)
print(response.usage)
print(response.latency_ms)
```

返回 `LLMResponse`：

| 字段 | 说明 |
| --- | --- |
| `content` | 回复正文 |
| `model` | 实际模型名 |
| `usage` | token 使用量 |
| `latency_ms` | 调用耗时 |
| `reasoning_content` | thinking model 的推理内容，可为空 |

`LLMResponse.__str__()` 返回 `content`，因此旧代码中 `str(response)` 仍可得到正文。

## 流式调用

```python
for chunk in llm.stream_invoke([
    {"role": "user", "content": "讲一个短故事"}
]):
    print(chunk, end="", flush=True)

print(llm.last_call_stats)
```

`think()` 是流式调用的便捷方法，会在终端打印调用提示和响应片段：

```python
for chunk in llm.think([{"role": "user", "content": "解释 RAG"}]):
    ...
```

## Function Calling

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "执行数学计算",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"}
                },
                "required": ["expression"]
            }
        }
    }
]

response = llm.invoke_with_tools(
    messages=[{"role": "user", "content": "计算 2+3"}],
    tools=tools,
    tool_choice="auto",
)

for call in response.tool_calls:
    print(call.name, call.arguments)
```

返回 `LLMToolResponse`：

| 字段 | 说明 |
| --- | --- |
| `content` | 模型文本输出，可为空 |
| `tool_calls` | 工具调用列表 |
| `model` | 实际模型名 |
| `usage` | token 使用量 |
| `latency_ms` | 调用耗时 |

## 异步接口

```python
response = await llm.ainvoke([
    {"role": "user", "content": "你好"}
])

async for chunk in llm.astream_invoke([
    {"role": "user", "content": "流式回答"}
]):
    print(chunk, end="")

tool_response = await llm.ainvoke_with_tools(messages, tools)
```

## 异常

配置缺失或调用失败会抛出 `HelloAgentsException`：

```python
from core import HelloAgentsException

try:
    llm = HelloAgentsLLM()
except HelloAgentsException as exc:
    print(exc)
```

常见原因：

- 未配置模型名、API Key 或 Base URL。
- Base URL 不可达。
- 模型名已经下线或无权限。
- 对应 adapter 的可选依赖未安装。
