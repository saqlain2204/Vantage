"""Tests for config.py — YAML loading, YAML formats, and schema expansion."""
from __future__ import annotations

import httpx
import pytest
import respx

from vantage.config import load_agents_from_yaml

_MOCK_RESPONSE = httpx.Response(
    200,
    json={"choices": [{"message": {"role": "assistant", "content": "ok", "tool_calls": []}}]},
)

_OPENAI_URL = "https://api.openai.com/v1/chat/completions"
_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _write(tmp_path, content: str):
    p = tmp_path / "agents.yaml"
    p.write_text(content, encoding="utf-8")
    return p


@respx.mock
def test_flat_format_groq(tmp_path):
    """New flat 'model: groq/...' format should load and call Groq endpoint."""
    cfg = _write(tmp_path, """
agents:
  bot:
    model: groq/llama-3.3-70b-versatile
    system_prompt: "Helpful assistant."
""")
    respx.post(_GROQ_URL).mock(return_value=_MOCK_RESPONSE)
    agents = {a.name: a.agent for a in load_agents_from_yaml(cfg)}
    resp = agents["bot"].run("hi")
    assert resp.content == "ok"


@respx.mock
def test_flat_format_openai(tmp_path, monkeypatch):
    """New flat 'model: openai/...' format should load and call OpenAI endpoint."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    cfg = _write(tmp_path, """
agents:
  bot:
    model: openai/gpt-4o-mini
""")
    respx.post(_OPENAI_URL).mock(return_value=_MOCK_RESPONSE)
    agents = {a.name: a.agent for a in load_agents_from_yaml(cfg)}
    resp = agents["bot"].run("hi")
    assert resp.content == "ok"


@respx.mock
def test_legacy_providers_block_still_works(tmp_path):
    """Old providers: block format must remain backward compatible."""
    cfg = _write(tmp_path, """
providers:
  openai:
    type: openai
    model: gpt-4o-mini
    api_key: test
    base_url: https://api.openai.com/v1

tools: {}

agents:
  a:
    provider: openai
""")
    respx.post(_OPENAI_URL).mock(return_value=_MOCK_RESPONSE)
    agents = {a.name: a.agent for a in load_agents_from_yaml(cfg)}
    resp = agents["a"].run("hi")
    assert resp.content == "ok"


def test_unknown_tool_raises(tmp_path):
    cfg = _write(tmp_path, """
agents:
  bot:
    model: groq/llama-3.3-70b-versatile
    tools: [does_not_exist]
""")
    with pytest.raises(ValueError, match="Unknown tool"):
        load_agents_from_yaml(cfg)


def test_missing_provider_in_legacy_raises(tmp_path):
    cfg = _write(tmp_path, """
providers: {}

agents:
  bot:
    provider: groq
""")
    with pytest.raises(ValueError, match="not found in the providers block"):
        load_agents_from_yaml(cfg)


def test_unresolvable_model_string_raises(tmp_path):
    cfg = _write(tmp_path, """
agents:
  bot:
    model: unknown_provider/some-model
""")
    with pytest.raises(ValueError, match="unknown provider"):
        load_agents_from_yaml(cfg)


@respx.mock
def test_shorthand_schema_expansion(tmp_path):
    """response_schema shorthand {field: type} must be expanded to full JSON Schema."""
    cfg = _write(tmp_path, """
agents:
  bot:
    model: groq/llama-3.3-70b-versatile
    response_schema:
      answer: string
      score: number
""")
    respx.post(_GROQ_URL).mock(return_value=_MOCK_RESPONSE)
    agents_by_name = {a.name: a.agent for a in load_agents_from_yaml(cfg)}
    bot = agents_by_name["bot"]
    assert bot.response_schema is not None
    props = bot.response_schema.get("properties", {})
    assert props.get("answer", {}).get("type") == "string"
    assert props.get("score", {}).get("type") == "number"


@respx.mock
def test_max_turns_respected(tmp_path):
    cfg = _write(tmp_path, """
agents:
  bot:
    model: groq/llama-3.3-70b-versatile
    max_turns: 7
""")
    respx.post(_GROQ_URL).mock(return_value=_MOCK_RESPONSE)
    bot = {a.name: a.agent for a in load_agents_from_yaml(cfg)}["bot"]
    assert bot.max_turns == 7


def test_calculator_tool_loaded(tmp_path):
    cfg = _write(tmp_path, """
tools:
  calc:
    type: calculator

agents:
  bot:
    model: groq/llama-3.3-70b-versatile
    tools: [calc]
""")
    bot = {a.name: a.agent for a in load_agents_from_yaml(cfg)}["bot"]
    tool_names = [t.name for t in bot.tools]
    assert "calculator" in tool_names
