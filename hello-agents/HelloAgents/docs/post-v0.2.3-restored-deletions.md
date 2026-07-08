# Post V0.2.3 Restored Deletions

Rule: commits after `9a1af1bf968f8cd1974da227ce8782857d1afee8` were integrated without applying historical deletions. Files below were deleted later in upstream history and do not exist in upstream `main`, so they were restored from the parent of the deletion commit.

Paths are listed as they appear in upstream history. In the target project, the `hello_agents/` prefix has been stripped and those files live in the corresponding top-level directories, for example `hello_agents/rl/datasets.py` is integrated as `rl/datasets.py`.

## 65bebf2 2025-10-18 16:15:03 +1100 jjyaoao update v0.2.5

Restored from `65bebf2^`:

- `examples/chapter11_orchestration.py`

## ebb01fd 2025-10-18 16:17:38 +1100 jjyaoao fix bug

Restored from `ebb01fd^`:

- `.github/workflows/ci.yml`

## 4a5a8dc 2025-10-23 13:01:31 +0800 Sun Tao Delete setup.py

Kept current `main` version because the path exists again in `main`:

- `setup.py`

## 9ff239a 2026-02-21 13:56:41 +0800 jjyaoao Update version V1.0.0

Restored from `9ff239a^`:

- `docs/api/agents/index.md`
- `docs/api/core/llm.md`
- `docs/api/index.md`
- `docs/api/memory/index.md`
- `docs/api/protocols/README.md`
- `docs/api/protocols/a2a_examples.md`
- `docs/api/protocols/anp_examples.md`
- `docs/api/protocols/mcp_detailed.md`
- `docs/api/rl/README.md`
- `docs/api/rl/datasets.md`
- `docs/api/rl/rewards.md`
- `docs/api/rl/rl_training_tool.md`
- `docs/api/rl/trainers.md`
- `docs/api/tools/index.md`
- `docs/tutorials/CONFIGURATION.md`
- `docs/tutorials/LOCAL_DEPLOYMENT_GUIDE.md`
- `examples/agent/function_call_agent_demo.py`
- `examples/chapter07_basic_setup.py`
- `examples/chapter08_memory_rag.py`
- `examples/chapter09_context_engineering.py`
- `examples/chapter10_protocols.py`
- `examples/chapter11_RL.py`
- `hello_agents/agents/function_call_agent.py`
- `hello_agents/agents/tool_aware_agent.py`
- `hello_agents/core/database_config.py`
- `hello_agents/evaluation/__init__.py`
- `hello_agents/evaluation/benchmarks/__init__.py`
- `hello_agents/evaluation/benchmarks/bfcl/__init__.py`
- `hello_agents/evaluation/benchmarks/bfcl/bfcl_integration.py`
- `hello_agents/evaluation/benchmarks/bfcl/dataset.py`
- `hello_agents/evaluation/benchmarks/bfcl/evaluator.py`
- `hello_agents/evaluation/benchmarks/bfcl/metrics.py`
- `hello_agents/evaluation/benchmarks/data_generation/__init__.py`
- `hello_agents/evaluation/benchmarks/data_generation/dataset.py`
- `hello_agents/evaluation/benchmarks/data_generation/llm_judge.py`
- `hello_agents/evaluation/benchmarks/data_generation/win_rate.py`
- `hello_agents/evaluation/benchmarks/gaia/__init__.py`
- `hello_agents/evaluation/benchmarks/gaia/dataset.py`
- `hello_agents/evaluation/benchmarks/gaia/evaluator.py`
- `hello_agents/evaluation/benchmarks/gaia/metrics.py`
- `hello_agents/memory/__init__.py`
- `hello_agents/memory/base.py`
- `hello_agents/memory/embedding.py`
- `hello_agents/memory/manager.py`
- `hello_agents/memory/rag/__init__.py`
- `hello_agents/memory/rag/document.py`
- `hello_agents/memory/rag/pipeline.py`
- `hello_agents/memory/storage/__init__.py`
- `hello_agents/memory/storage/document_store.py`
- `hello_agents/memory/storage/neo4j_store.py`
- `hello_agents/memory/storage/qdrant_store.py`
- `hello_agents/memory/types/__init__.py`
- `hello_agents/memory/types/episodic.py`
- `hello_agents/memory/types/perceptual.py`
- `hello_agents/memory/types/semantic.py`
- `hello_agents/memory/types/working.py`
- `hello_agents/protocols/__init__.py`
- `hello_agents/protocols/a2a/__init__.py`
- `hello_agents/protocols/a2a/implementation.py`
- `hello_agents/protocols/anp/__init__.py`
- `hello_agents/protocols/anp/implementation.py`
- `hello_agents/protocols/base.py`
- `hello_agents/protocols/mcp/__init__.py`
- `hello_agents/protocols/mcp/client.py`
- `hello_agents/protocols/mcp/server.py`
- `hello_agents/protocols/mcp/utils.py`
- `hello_agents/rl/__init__.py`
- `hello_agents/rl/datasets.py`
- `hello_agents/rl/rewards.py`
- `hello_agents/rl/trainers.py`
- `hello_agents/rl/utils.py`
- `hello_agents/tools/async_executor.py`
- `hello_agents/tools/builtin/bfcl_evaluation_tool.py`
- `hello_agents/tools/builtin/gaia_evaluation_tool.py`
- `hello_agents/tools/builtin/llm_judge_tool.py`
- `hello_agents/tools/builtin/mcp_wrapper_tool.py`
- `hello_agents/tools/builtin/memory_tool.py`
- `hello_agents/tools/builtin/note_tool.py`
- `hello_agents/tools/builtin/protocol_tools.py`
- `hello_agents/tools/builtin/rag_tool.py`
- `hello_agents/tools/builtin/rl_training_tool.py`
- `hello_agents/tools/builtin/search_tool.py`
- `hello_agents/tools/builtin/terminal_tool.py`
- `hello_agents/tools/builtin/win_rate_tool.py`
- `hello_agents/tools/chain.py`
- `hello_agents/utils/__init__.py`
- `hello_agents/utils/helpers.py`
- `hello_agents/utils/logging.py`
- `hello_agents/utils/serialization.py`

## Totals

- Restored deleted paths: 91
- Paths deleted then recreated in main: 1
