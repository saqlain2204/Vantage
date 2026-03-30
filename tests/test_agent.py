"""Unit tests for the sync Agent class using stub LLM implementations."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


from vantage.core.agent import Agent
from vantage.core.bases import LLMBase, ToolBase
from vantage.core.models import Message, Role, ToolCall
from vantage.memory.local import LocalMemory


class StubLLM(LLMBase):
    """Configurable stub that returns pre-defined responses in order."""

    def __init__(self, responses: List[Message]) -> None:
        self._queue = list(responses)
        self.calls: List[List[Message]] = []

    def generate(
        self,
        messages: List[Message],
        tools: List[ToolBase],
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> Message:
        self.calls.append(list(messages))
        assert self._queue, "StubLLM ran out of responses"
        return self._queue.pop(0)


class EchoTool(ToolBase):
    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echoes the input."

    def input_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {"text": {"type": "string"}}}

    def execute(self, **kwargs: Any) -> str:
        return kwargs.get("text", "")


class BrokenTool(ToolBase):
    @property
    def name(self) -> str:
        return "broken"

    @property
    def description(self) -> str:
        return "Always raises."

    def input_schema(self) -> Dict[str, Any]:
        return {}

    def execute(self, **kwargs: Any) -> str:
        raise RuntimeError("tool failure")


def _assistant(content: str) -> Message:
    return Message(role=Role.ASSISTANT, content=content)


def _tool_call_msg(name: str, args: Dict[str, Any], call_id: str = "c1") -> Message:
    return Message(
        role=Role.ASSISTANT,
        content="",
        tool_calls=[ToolCall(id=call_id, name=name, arguments=args)],
    )


def test_no_tool_single_turn():
    llm = StubLLM([_assistant("hello there")])
    agent = Agent(llm=llm)
    resp = agent.run("hi")
    assert resp.content == "hello there"
    assert resp.tool_results == []


def test_tool_call_round_trip():
    llm = StubLLM([
        _tool_call_msg("echo", {"text": "world"}),
        _assistant("The echo was: world"),
    ])
    agent = Agent(llm=llm, tools=[EchoTool()])
    resp = agent.run("please echo world")
    assert resp.content == "The echo was: world"
    assert len(resp.tool_results) == 1
    assert resp.tool_results[0].output == "world"
    assert not resp.tool_results[0].is_error


def test_unknown_tool_is_error():
    llm = StubLLM([
        _tool_call_msg("nonexistent", {}),
        _assistant("That didn't work"),
    ])
    agent = Agent(llm=llm)
    resp = agent.run("call nonexistent")
    assert any(r.is_error for r in resp.tool_results)


def test_broken_tool_is_error():
    llm = StubLLM([
        _tool_call_msg("broken", {}),
        _assistant("The tool failed"),
    ])
    agent = Agent(llm=llm, tools=[BrokenTool()])
    resp = agent.run("break something")
    assert resp.tool_results[0].is_error
    assert "tool failure" in resp.tool_results[0].output


def test_max_turns_returns_fallback():
    responses = [_tool_call_msg("echo", {"text": "x"}) for _ in range(20)]
    responses += [_assistant("fallback")] * 5
    llm = StubLLM(responses)
    agent = Agent(llm=llm, tools=[EchoTool()], max_turns=3)
    resp = agent.run("loop forever")
    assert resp.content == "Max turns exceeded."


def test_trace_has_user_thought_and_result_steps():
    llm = StubLLM([
        _tool_call_msg("echo", {"text": "hi"}),
        _assistant("done"),
    ])
    agent = Agent(llm=llm, tools=[EchoTool()])
    resp = agent.run("go")
    step_types = [s.step_type for s in resp.trace]
    assert "user" in step_types
    assert "call" in step_types
    assert "result" in step_types


def test_memory_not_duplicated():
    """Messages must not accumulate multiple times in LocalMemory."""
    llm = StubLLM([_assistant("first"), _assistant("second")])
    mem = LocalMemory()
    agent = Agent(llm=llm, memory=mem)
    agent.run("turn one")
    agent.run("turn two")
    msgs = mem.get_messages()
    contents = [m.content for m in msgs]
    # Each content should appear at most once
    assert len(contents) == len(set(c for c in contents if c))


def test_trace_result_step_is_error_false():
    llm = StubLLM([
        _tool_call_msg("echo", {"text": "ok"}),
        _assistant("done"),
    ])
    agent = Agent(llm=llm, tools=[EchoTool()])
    resp = agent.run("test")
    result_steps = [s for s in resp.trace if s.step_type == "result"]
    assert result_steps, "Expected at least one result trace step"
    assert result_steps[0].metadata.get("is_error") is False
