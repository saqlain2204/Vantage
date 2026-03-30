# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-03-30

### Added
- `Agent` for synchronous single-agent and multi-agent flows.
- `AsyncAgent` with `run()` and `stream()` for async/streaming usage.
- `OpenAIModel` and `GroqModel` sync LLM clients.
- `AsyncOpenAIModel` and `AsyncGroqModel` async LLM clients with SSE streaming.
- `LocalMemory` for in-process conversation history.
- `Calculator` built-in tool using a safe AST-based evaluator.
- `HandoverTool` for routing between agents in multi-agent flows.
- `run_yaml_agent` and `async_run_yaml_agent` for YAML-driven agent execution.
- `save_trace_png` for rendering execution traces as PNG diagrams.
- New flat YAML format: `model: provider/model-name` — no `providers:` block required.
- `response_schema` shorthand: `{field: type}` expanded to full JSON Schema automatically.
- GitHub Actions CI pipeline (Python 3.11 / 3.12 / 3.13, ubuntu / windows / macos).
- GitHub Actions publish workflow for PyPI releases.
