from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from ..core.bases import AsyncLLMBase, LLMBase, ToolBase
from ..core.models import Message
from .openai import _auth_headers, _parse_response, _to_openai_message


class GroqModel(LLMBase):
    def __init__(
        self,
        model: str = "llama-3.3-70b-versatile",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_s: float = 60.0,
        temperature: Optional[float] = None,
        max_completion_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.base_url = (
            base_url or os.getenv("GROQ_BASE_URL") or "https://api.groq.com/openai/v1"
        ).rstrip("/")
        self._client = httpx.Client(timeout=timeout_s)
        self.temperature = temperature
        self.max_completion_tokens = max_completion_tokens
        self.top_p = top_p

    def generate(
        self,
        messages: List[Message],
        tools: List[ToolBase],
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> Message:
        if not self.api_key:
            raise ValueError("Missing API key. Set GROQ_API_KEY or pass api_key=...")

        msgs, payload = _groq_payload(
            self.model, messages, tools, response_schema,
            self.temperature, self.max_completion_tokens, self.top_p,
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

    def __enter__(self) -> GroqModel:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class AsyncGroqModel(AsyncLLMBase):
    def __init__(
        self,
        model: str = "llama-3.3-70b-versatile",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_s: float = 60.0,
        temperature: Optional[float] = None,
        max_completion_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.base_url = (
            base_url or os.getenv("GROQ_BASE_URL") or "https://api.groq.com/openai/v1"
        ).rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout_s)
        self.temperature = temperature
        self.max_completion_tokens = max_completion_tokens
        self.top_p = top_p

    async def generate(
        self,
        messages: List[Message],
        tools: List[ToolBase],
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> Message:
        if not self.api_key:
            raise ValueError("Missing API key. Set GROQ_API_KEY or pass api_key=...")

        msgs, payload = _groq_payload(
            self.model, messages, tools, response_schema,
            self.temperature, self.max_completion_tokens, self.top_p,
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
        if not self.api_key:
            raise ValueError("Missing API key. Set GROQ_API_KEY or pass api_key=...")

        _, payload = _groq_payload(self.model, messages, tools)
        payload["stream"] = True
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

    async def __aenter__(self) -> AsyncGroqModel:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()


def _groq_payload(
    model: str,
    messages: List[Message],
    tools: List[ToolBase],
    response_schema: Optional[Dict[str, Any]] = None,
    temperature: Optional[float] = None,
    max_completion_tokens: Optional[int] = None,
    top_p: Optional[float] = None,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    msgs: List[Dict[str, Any]] = [_to_openai_message(m) for m in messages]
    payload: Dict[str, Any] = {"model": model, "messages": msgs}

    if response_schema:
        payload["response_format"] = {"type": "json_object"}
        for m in msgs:
            if m["role"] in ("system", "user"):
                m["content"] = (m["content"] or "") + (
                    f"\n\nIMPORTANT: Respond ONLY with a JSON object matching this schema: "
                    f"{json.dumps(response_schema)}"
                )
                break
        else:
            msgs.insert(0, {
                "role": "system",
                "content": (
                    f"Respond ONLY with a JSON object matching this schema: "
                    f"{json.dumps(response_schema)}"
                ),
            })

    if temperature is not None:
        payload["temperature"] = temperature
    if max_completion_tokens is not None:
        payload["max_completion_tokens"] = max_completion_tokens
    if top_p is not None:
        payload["top_p"] = top_p

    tool_payload = [_to_groq_tool(t) for t in tools]
    if tool_payload:
        payload["tools"] = tool_payload

    return msgs, payload


def _to_groq_tool(t: ToolBase) -> Dict[str, Any]:
    """Like _to_openai_tool but strips `additionalProperties` which Groq rejects."""
    schema = {k: v for k, v in t.input_schema().items() if k != "additionalProperties"}
    return {
        "type": "function",
        "function": {
            "name": t.name,
            "description": t.description,
            "parameters": schema,
        },
    }



