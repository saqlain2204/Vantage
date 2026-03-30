from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from ..core.bases import AsyncLLMBase, LLMBase, ToolBase
from ..core.models import Message, Role, ToolCall


class OpenAIModel(LLMBase):
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_s: float = 60.0,
        temperature: Optional[float] = None,
        max_completion_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        reasoning_effort: Optional[str] = None,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = (
            base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        ).rstrip("/")
        self._client = httpx.Client(timeout=timeout_s)
        self.temperature = temperature
        self.max_completion_tokens = max_completion_tokens
        self.top_p = top_p
        self.reasoning_effort = reasoning_effort

    def generate(
        self,
        messages: List[Message],
        tools: List[ToolBase],
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> Message:
        if not self.api_key:
            raise ValueError("Missing API key. Set OPENAI_API_KEY or pass api_key=...")

        payload = _build_payload(
            self.model, messages, tools, response_schema,
            self.temperature, self.max_completion_tokens, self.top_p, self.reasoning_effort,
        )
        r = self._client.post(
            f"{self.base_url}/chat/completions",
            headers=_auth_headers(self.api_key),
            json=payload,
        )
        r.raise_for_status()
        return _parse_response(r.json())

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> OpenAIModel:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class AsyncOpenAIModel(AsyncLLMBase):
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_s: float = 60.0,
        temperature: Optional[float] = None,
        max_completion_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        reasoning_effort: Optional[str] = None,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = (
            base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        ).rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout_s)
        self.temperature = temperature
        self.max_completion_tokens = max_completion_tokens
        self.top_p = top_p
        self.reasoning_effort = reasoning_effort

    async def generate(
        self,
        messages: List[Message],
        tools: List[ToolBase],
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> Message:
        if not self.api_key:
            raise ValueError("Missing API key. Set OPENAI_API_KEY or pass api_key=...")

        payload = _build_payload(
            self.model, messages, tools, response_schema,
            self.temperature, self.max_completion_tokens, self.top_p, self.reasoning_effort,
        )
        r = await self._client.post(
            f"{self.base_url}/chat/completions",
            headers=_auth_headers(self.api_key),
            json=payload,
        )
        r.raise_for_status()
        return _parse_response(r.json())

    async def generate_stream(  # type: ignore[override]
        self,
        messages: List[Message],
        tools: List[ToolBase],
    ) -> AsyncIterator[str]:
        """Yield token chunks from the streaming chat completions endpoint."""
        if not self.api_key:
            raise ValueError("Missing API key. Set OPENAI_API_KEY or pass api_key=...")

        payload = _build_payload(self.model, messages, tools, stream=True)
        async with self._client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            headers=_auth_headers(self.api_key),
            json=payload,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    token: str = chunk["choices"][0]["delta"].get("content") or ""
                    if token:
                        yield token
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncOpenAIModel:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()


def _auth_headers(api_key: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _build_payload(
    model: str,
    messages: List[Message],
    tools: List[ToolBase],
    response_schema: Optional[Dict[str, Any]] = None,
    temperature: Optional[float] = None,
    max_completion_tokens: Optional[int] = None,
    top_p: Optional[float] = None,
    reasoning_effort: Optional[str] = None,
    stream: bool = False,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model": model,
        "messages": [_to_openai_message(m) for m in messages],
    }
    if response_schema:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "response_schema",
                "strict": True,
                "schema": response_schema,
            },
        }
    if temperature is not None:
        payload["temperature"] = temperature
    if max_completion_tokens is not None:
        payload["max_completion_tokens"] = max_completion_tokens
    if top_p is not None:
        payload["top_p"] = top_p
    if reasoning_effort is not None:
        payload["reasoning_effort"] = reasoning_effort
    if stream:
        payload["stream"] = True
    tool_payload = [_to_openai_tool(t) for t in tools]
    if tool_payload:
        payload["tools"] = tool_payload
    return payload


def _parse_response(data: Dict[str, Any]) -> Message:
    msg = data["choices"][0]["message"]
    tool_calls: List[ToolCall] = []
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        args_raw = fn.get("arguments") or "{}"
        try:
            args = json.loads(args_raw) if isinstance(args_raw, str) else dict(args_raw)
        except Exception:
            args = {}
        tool_calls.append(
            ToolCall(
                id=str(tc.get("id") or ""),
                name=str(fn.get("name") or ""),
                arguments=args,
            )
        )
    return Message(role=Role.ASSISTANT, content=msg.get("content") or "", tool_calls=tool_calls)


def _to_openai_message(m: Message) -> Dict[str, Any]:
    base: Dict[str, Any] = {"role": m.role.value, "content": m.content}
    if m.name:
        base["name"] = m.name
    if m.tool_calls:
        base["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
            }
            for tc in m.tool_calls
        ]
    if m.tool_call_id:
        base["tool_call_id"] = m.tool_call_id
    return base


def _to_openai_tool(t: ToolBase) -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": t.name,
            "description": t.description,
            "parameters": t.input_schema(),
        },
    }


