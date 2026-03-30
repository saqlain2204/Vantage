"""Shared pytest fixtures."""
from __future__ import annotations

import httpx


def openai_text_response(content: str = "ok") -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"message": {"role": "assistant", "content": content, "tool_calls": []}}]},
    )


def openai_tool_call_response(tool_name: str, arguments: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": tool_name, "arguments": arguments},
                            }
                        ],
                    }
                }
            ]
        },
    )


def write_yaml(tmp_path, name: str, content: str):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p
