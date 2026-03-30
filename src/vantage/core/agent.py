from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from .bases import AsyncLLMBase, LLMBase, MemoryBase, ToolBase
from .models import Message, Role, AgentResponse, ToolResult, TraceStep

logger = logging.getLogger(__name__)


class Agent:
    def __init__(
        self,
        llm: LLMBase,
        tools: Optional[List[ToolBase]] = None,
        memory: Optional[MemoryBase] = None,
        system_prompt: str = "You are a helpful assistant.",
        max_turns: int = 12,
        response_schema: Optional[Dict[str, Any]] = None,
    ):
        self.llm = llm
        self.tools = tools or []
        self.memory = memory
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.response_schema = response_schema

        if self.memory and not self.memory.get_messages():
            self.memory.add(Message(role=Role.SYSTEM, content=system_prompt))

    def _add(self, messages: List[Message], msg: Message) -> None:
        """Append *msg* to the local list and keep memory in sync."""
        messages.append(msg)
        if self.memory:
            self.memory.add(msg)

    def run(
        self,
        prompt: str,
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        active_schema = response_schema or self.response_schema
        user_message = Message(role=Role.USER, content=prompt)
        trace: List[TraceStep] = [TraceStep(step_type="user", content=prompt)]
        tool_map: Dict[str, ToolBase] = {t.name: t for t in self.tools}
        tool_results: List[ToolResult] = []

        if self.memory:
            self.memory.add(user_message)
            messages: List[Message] = list(self.memory.get_messages())
        else:
            messages = [
                Message(role=Role.SYSTEM, content=self.system_prompt),
                user_message,
            ]

        for turn in range(self.max_turns):
            logger.debug("Turn %d/%d", turn + 1, self.max_turns)
            response_message = self.llm.generate(messages, self.tools)

            if response_message.content:
                logger.debug("LLM: %.200s", response_message.content)
                trace.append(TraceStep(step_type="thought", content=response_message.content))

            if not response_message.tool_calls:
                # Final response turn — add message, then optionally enforce schema.
                self._add(messages, response_message)
                if active_schema:
                    final = self.llm.generate(messages, tools=[], response_schema=active_schema)
                    self._add(messages, final)
                    trace.append(TraceStep(step_type="final", content=final.content))
                    return AgentResponse(content=final.content, tool_results=tool_results, trace=trace)
                return AgentResponse(content=response_message.content, tool_results=tool_results, trace=trace)

            # Tool-call turn.
            self._add(messages, response_message)

            for tc in response_message.tool_calls:
                logger.debug("Tool call: %s(%s)", tc.name, tc.arguments)
                trace.append(TraceStep(step_type="call", content=tc.name, metadata=tc.arguments))

                tool = tool_map.get(tc.name)
                if tool is None:
                    result = ToolResult(
                        tool_name=tc.name,
                        output=f"Unknown tool: {tc.name}",
                        is_error=True,
                        tool_call_id=tc.id,
                    )
                else:
                    try:
                        output = tool.execute(**tc.arguments)
                        result = ToolResult(
                            tool_name=tool.name,
                            output=output,
                            is_error=False,
                            tool_call_id=tc.id,
                        )
                    except Exception as exc:
                        result = ToolResult(
                            tool_name=tool.name,
                            output=str(exc),
                            is_error=True,
                            tool_call_id=tc.id,
                        )

                logger.debug("Tool result [%s]: %s", result.tool_name, result.output)
                trace.append(
                    TraceStep(
                        step_type="result",
                        content=result.output,
                        metadata={"tool": result.tool_name, "is_error": result.is_error},
                    )
                )
                tool_results.append(result)

                if result.output.startswith("Handing over to "):
                    return AgentResponse(content=result.output, tool_results=tool_results, trace=trace)

                tool_msg = Message(
                    role=Role.TOOL,
                    name=result.tool_name,
                    content=result.output,
                    tool_call_id=result.tool_call_id,
                )
                self._add(messages, tool_msg)

        # Max turns reached — try to produce a structured response if needed.
        logger.warning("Max turns (%d) reached", self.max_turns)
        if active_schema:
            final = self.llm.generate(messages, self.tools, response_schema=active_schema)
            trace.append(TraceStep(step_type="final", content=final.content))
            self._add(messages, final)
            return AgentResponse(content=final.content, tool_results=tool_results, trace=trace)
        return AgentResponse(content="Max turns exceeded.", tool_results=tool_results, trace=trace)

    def run_text(self, prompt: str) -> str:
        return self.run(prompt).content


class AsyncAgent:
    def __init__(
        self,
        llm: AsyncLLMBase,
        tools: Optional[List[ToolBase]] = None,
        memory: Optional[MemoryBase] = None,
        system_prompt: str = "You are a helpful assistant.",
        max_turns: int = 12,
        response_schema: Optional[Dict[str, Any]] = None,
    ):
        self.llm = llm
        self.tools = tools or []
        self.memory = memory
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.response_schema = response_schema

        if self.memory and not self.memory.get_messages():
            self.memory.add(Message(role=Role.SYSTEM, content=system_prompt))

    def _add(self, messages: List[Message], msg: Message) -> None:
        messages.append(msg)
        if self.memory:
            self.memory.add(msg)

    async def run(
        self,
        prompt: str,
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        active_schema = response_schema or self.response_schema
        user_message = Message(role=Role.USER, content=prompt)
        trace: List[TraceStep] = [TraceStep(step_type="user", content=prompt)]
        tool_map: Dict[str, ToolBase] = {t.name: t for t in self.tools}
        tool_results: List[ToolResult] = []

        if self.memory:
            self.memory.add(user_message)
            messages: List[Message] = list(self.memory.get_messages())
        else:
            messages = [
                Message(role=Role.SYSTEM, content=self.system_prompt),
                user_message,
            ]

        for turn in range(self.max_turns):
            logger.debug("Async turn %d/%d", turn + 1, self.max_turns)
            response_message = await self.llm.generate(messages, self.tools)

            if response_message.content:
                trace.append(TraceStep(step_type="thought", content=response_message.content))

            if not response_message.tool_calls:
                self._add(messages, response_message)
                if active_schema:
                    final = await self.llm.generate(messages, tools=[], response_schema=active_schema)
                    self._add(messages, final)
                    trace.append(TraceStep(step_type="final", content=final.content))
                    return AgentResponse(content=final.content, tool_results=tool_results, trace=trace)
                return AgentResponse(content=response_message.content, tool_results=tool_results, trace=trace)

            self._add(messages, response_message)

            for tc in response_message.tool_calls:
                trace.append(TraceStep(step_type="call", content=tc.name, metadata=tc.arguments))

                tool = tool_map.get(tc.name)
                if tool is None:
                    result = ToolResult(
                        tool_name=tc.name,
                        output=f"Unknown tool: {tc.name}",
                        is_error=True,
                        tool_call_id=tc.id,
                    )
                else:
                    try:
                        output = tool.execute(**tc.arguments)
                        result = ToolResult(tool_name=tool.name, output=output, is_error=False, tool_call_id=tc.id)
                    except Exception as exc:
                        result = ToolResult(tool_name=tool.name, output=str(exc), is_error=True, tool_call_id=tc.id)

                trace.append(
                    TraceStep(
                        step_type="result",
                        content=result.output,
                        metadata={"tool": result.tool_name, "is_error": result.is_error},
                    )
                )
                tool_results.append(result)

                if result.output.startswith("Handing over to "):
                    return AgentResponse(content=result.output, tool_results=tool_results, trace=trace)

                self._add(messages, Message(
                    role=Role.TOOL,
                    name=result.tool_name,
                    content=result.output,
                    tool_call_id=result.tool_call_id,
                ))

        logger.warning("Async max turns (%d) reached", self.max_turns)
        if active_schema:
            final = await self.llm.generate(messages, self.tools, response_schema=active_schema)
            trace.append(TraceStep(step_type="final", content=final.content))
            self._add(messages, final)
            return AgentResponse(content=final.content, tool_results=tool_results, trace=trace)
        return AgentResponse(content="Max turns exceeded.", tool_results=tool_results, trace=trace)

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        """Stream token chunks for a single-turn exchange (no tool calls)."""
        user_message = Message(role=Role.USER, content=prompt)
        if self.memory:
            self.memory.add(user_message)
            messages: List[Message] = list(self.memory.get_messages())
        else:
            messages = [Message(role=Role.SYSTEM, content=self.system_prompt), user_message]

        async for token in self.llm.generate_stream(messages, self.tools):
            yield token


