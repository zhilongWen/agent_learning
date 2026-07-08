# HelloAgents upstream integration

## Current Project Shape

- Runtime project lives at `hello-agents/HelloAgents`.
- It uses a top-level package layout: modules such as `core`, `agents`, `tools`, `context`, `mem`, `observability`, `skills`, `protocols`, `evaluation`, and `rl` sit directly under the project root.
- There is no separate `hello_agents/` runtime package in the integrated target; local scripts usually need `PYTHONPATH=/Users/wenzhilong/space/warehouse/agent_learning/hello-agents/HelloAgents`.
- `docs/current-architecture.md` is the most accurate architecture overview for the integrated version.

## Core Runtime Flow

- `core/llm.py` defines `HelloAgentsLLM`, the unified model entry point. It reads `LLM_MODEL_ID/LLM_API_KEY/LLM_BASE_URL` first and also supports legacy `MODEL_ID/API_KEY/BASE_URL`; `app_id` is accepted as an API key alias.
- `core/llm_adapters.py` selects an adapter from `base_url`: OpenAI-compatible by default, Anthropic for Anthropic URLs, and Gemini for Google generative language URLs.
- `core/agent.py` defines the abstract `Agent` base. Construction wires `HistoryManager`, `ObservationTruncator`, `TokenCounter`, optional `TraceLogger`, optional `SkillLoader`, optional `SessionStore`, and auto-registers Task/TodoWrite/DevLog tools when enabled.
- Typical run loop: user input -> Agent builds messages -> `HelloAgentsLLM.invoke()` or `invoke_with_tools()` -> optional tool calls -> `ToolRegistry` executes tools -> `ToolResponse.text` is appended as tool context -> Agent records history/trace/session metadata -> final answer.

## Agent Implementations

- `agents/simple_agent.py`: direct chat plus optional OpenAI Function Calling; supports multiple tool-call iterations.
- `agents/react_agent.py`: Function Calling based ReAct loop with built-in `Thought` and `Finish` tool semantics, plus user tools from the registry.
- `agents/reflection_agent.py`: initial execution -> reflection -> refinement loop; stores short-term execution/reflection trajectory in an internal `Memory`.
- `agents/plan_solve_agent.py`: `Planner` forces a `generate_plan` tool call to produce ordered steps; `Executor` runs each step and can reuse SimpleAgent-style tool calling.
- `PlanAndSolveAgent` remains as a compatibility alias for `PlanSolveAgent`.

## Tool Protocol

- `tools/base.py` defines `Tool`, `ToolParameter`, `tool_action`, expandable tools, and sync/async `run_with_timing` wrappers.
- `tools/response.py` defines the standard `ToolResponse` protocol with `success`, `partial`, and `error` states.
- `tools/registry.py` supports both class-based tools and direct function tools, parses JSON/string input, records timing, and feeds results into `CircuitBreaker`.
- Agent-side `_build_tool_schemas()` converts registered tools into OpenAI Function Calling schemas; `_execute_tool_call()` runs tools with type conversion and returns an LLM-facing string.

## Context, Trace, And Session

- `context/history.py` keeps append-only message history, finds user-turn boundaries, and compresses old turns into a `summary` message while retaining recent rounds.
- `context/token_counter.py` caches token counts so `Agent.add_message()` can cheaply decide when to compress.
- `context/truncator.py` limits long tool observations and saves full output under `tool-output/`.
- `observability/trace_logger.py` writes JSONL and HTML traces with events such as session start, model output, tool calls, tool results, errors, and session end.
- `core/session_store.py` saves sessions atomically to `memory/sessions`, including agent config, history, tool schema hash, read cache, and metadata.

## Memory And RAG

- Integrated memory runtime package is `mem`; do not add new runtime code under a separate `memory` package.
- `mem/manager.py` coordinates working, episodic, semantic, and optional perceptual memory types.
- `tools/builtin/memory_tool.py` exposes add/search/summary/stats/update/remove/forget/consolidate/clear actions through the Tool protocol.
- `mem/rag/pipeline.py` converts documents to markdown with MarkItDown when available, applies enhanced PDF cleanup, creates heading-aware chunks, embeds them, stores them in Qdrant, and supports vector/advanced search.
- `tools/builtin/rag_tool.py` exposes `add_document`, `add_text`, `ask`, `search`, `stats`, and `clear`; it creates `HelloAgentsLLM` from legacy env names with `provider="openai"` for compatibility.

## Default Runtime Artifacts

- Trace files: `memory/traces/*.jsonl` and `memory/traces/*.html`.
- Session files: `memory/sessions/*.json`.
- Todo files: `memory/todos/*`.
- DevLog files: `memory/devlogs/*`.
- Full long tool output: `tool-output/*`.
