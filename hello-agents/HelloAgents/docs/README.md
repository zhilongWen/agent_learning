# HelloAgents 文档中心

本目录记录当前 `HelloAgents` 集成版的使用方式、架构说明和 API 参考。当前项目采用顶层包布局，示例代码默认从项目根加入 `PYTHONPATH` 后使用：

```python
from agents import ReActAgent
from core import HelloAgentsLLM, Config
from tools import ToolRegistry
```

> 注意：当前目标项目没有保留独立的 `hello_agents/` 包目录；上游 `memory/` 包也已合并到本项目的 `mem/` 包中。

## 推荐阅读路径

### 1. 快速理解项目

- [当前架构总览](./current-architecture.md)：模块边界、核心数据流、外部依赖和运行产物。
- [配置说明](./configuration.md)：LLM、上下文压缩、Trace、Session、Skills、Memory/RAG 等配置入口。
- [测试与验证](./testing-and-validation.md)：如何运行 test 目录、真实 LLM 用例、常见失败原因。
- [导入路径迁移说明](./import-migration.md)：如何把历史文档中的 `hello_agents.*` 示例映射到当前顶层包布局。

### 2. 核心能力指南

- [工具响应协议](./tool-response-protocol.md)：`ToolResponse` 统一返回格式。
- [上下文工程](./context-engineering-guide.md)：历史压缩、Token 计数、工具输出截断。
- [Function Calling 架构](./function-calling-architecture.md)：LLM 与 Agent 的结构化工具调用。
- [会话持久化](./session-persistence-guide.md)：`SessionStore` 的保存、恢复与一致性检查。
- [可观测性](./observability-guide.md)：`TraceLogger` 的 JSONL/HTML 轨迹。
- [异步 Agent](./async-agent-guide.md)：异步执行、生命周期事件和流式输出。

### 3. 工具与扩展

- [自定义工具开发](./custom_tools_guide.md)：函数式工具、标准工具类、可展开工具。
- [文件工具与乐观锁](./file_tools.md)：`Read/Write/Edit/MultiEdit` 的并发保护。
- [子代理机制](./subagent-guide.md)：`TaskTool`、工具过滤和上下文隔离。
- [TodoWrite 进度管理](./todowrite-usage-guide.md)：任务列表工具。
- [DevLog 决策日志](./devlog-guide.md)：开发过程记录工具。
- [Skills 知识外化](./skills-usage-guide.md)：`SkillLoader` 与 `SkillTool`。
- [熔断器机制](./circuit-breaker-guide.md)：工具失败保护。

### 4. API 参考

- [API 总览](./api/index.md)
- [LLM API](./api/core/llm.md)
- [Agent API](./api/agents/index.md)
- [工具 API](./api/tools/index.md)
- [记忆与 RAG API](./api/memory/index.md)
- [协议 API](./api/protocols/README.md)
- [RL API](./api/rl/README.md)

### 5. 集成记录

- [Post V0.2.3 集成说明](./post-v0.2.3-integration.md)
- [Post V0.2.3 Commit 列表](./post-v0.2.3-commit-list.md)
- [恢复的删除内容](./post-v0.2.3-restored-deletions.md)

## 当前验证快照

最近一次完整测试命令：

```bash
PYTHONPATH=/Users/wenzhilong/space/warehouse/agent_learning/hello-agents/HelloAgents \
/Users/wenzhilong/miniconda3/envs/myenv3.12/bin/python -m pytest \
/Users/wenzhilong/space/warehouse/agent_learning/hello-agents/HelloAgents/test -q
```

结果：`270 passed, 6 skipped, 10 warnings`。

## 目录维护约定

- 面向用户的能力说明放在 `docs/*.md`。
- 面向代码调用的接口说明放在 `docs/api/**`。
- 教程式、部署式内容放在 `docs/tutorials/**`。
- 上游集成、历史删除恢复等过程记录保留在 `post-v0.2.3-*` 文档中。
- 历史教程页可能保留 upstream 的 `hello_agents.*` 导入示例；当前运行时以 [导入路径迁移说明](./import-migration.md) 为准。
