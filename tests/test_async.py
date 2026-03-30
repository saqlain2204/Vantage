"""Tests for AsyncAgent and AsyncLLMBase."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from vantage.core.agent import AsyncAgent
from vantage.core.bases import AsyncLLMBase, ToolBase
from vantage.core.models import Message, Role, ToolCall


class StubAsyncLLM(AsyncLLMBase):
    """Configurable async stub that yields pre-defined responses in order."""

    def __init__(self, responses: List[Message]) -> None:
        self._queue = list(responses)

    async def generate(
        self,
        messages: List[Message],
        tools: List[ToolBase],
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> Message:
        assert self._queue, "StubAsyncLLM ran out of responses"
        return self._queue.pop(0)


class EchoTool(ToolBase):
    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echoes text."

    def input_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {"text": {"type": "string"}}}

    def execute(self, **kwargs: Any) -> str:
        return kwargs.get("text", "")


def _assistant(content: str) -> Message:
    return Message(role=Role.ASSISTANT, content=content)


def _tool_call_msg(name: str, args: Dict[str, Any]) -> Message:
    return Message(
        role=Role.ASSISTANT,
        content="",
        tool_calls=[ToolCall(id="c1", name=name, arguments=args)],
    )


@pytest.mark.asyncio
async def test_async_agent_single_turn():
    llm = StubAsyncLLM([_assistant("async response")])
    agent = AsyncAgent(llm=llm)
    resp = await agent.run("hello")
    assert resp.content == "async response"


@pytest.mark.asyncio
async def test_async_agent_tool_call():
    llm = StubAsyncLLM([
        _tool_call_msg("echo", {"text": "ping"}),
        _assistant("Got: ping"),
    ])
    agent = AsyncAgent(llm=llm, tools=[EchoTool()])
    resp = await agent.run("echo ping")
    assert resp.content == "Got: ping"
    assert resp.tool_results[0].output == "ping"


@pytest.mark.asyncio
async def test_async_agent_max_turns():
    responses = [_tool_call_msg("echo", {"text": "x"}) for _ in range(20)]
    responses += [_assistant("end")] * 5
    llm = StubAsyncLLM(responses)
    agent = AsyncAgent(llm=llm, tools=[EchoTool()], max_turns=2)
    resp = await agent.run("loop")
    assert resp.content == "Max turns exceeded."


@pytest.mark.asyncio
async def test_async_agent_trace_has_user_step():
    llm = StubAsyncLLM([_assistant("done")])
    agent = AsyncAgent(llm=llm)
    resp = await agent.run("test")
    assert resp.trace[0].step_type == "user"
    assert resp.trace[0].content == "test"


@pytest.mark.asyncio
async def test_async_stream_default_fallback():
    """Default generate_stream falls back to generate() and yields the full content."""
    llm = StubAsyncLLM([_assistant("streamed content")])
    agent = AsyncAgent(llm=llm)
    chunks = [c async for c in agent.stream("hello")]
    assert "".join(chunks) == "streamed content"
