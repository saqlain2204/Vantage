from __future__ import annotations

from typing import Any, Dict
from urllib.parse import quote

import httpx

from ..core.bases import ToolBase

_DEFAULT_TIMEOUT = 10.0
_RESPONSE_SNIPPET_LENGTH = 200


class StackOverflowTool(ToolBase):
    def __init__(self, timeout: float = _DEFAULT_TIMEOUT) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "stack_overflow_tool"

    @property
    def description(self) -> str:
        return "Search Stack Overflow for programming questions and return the top answer snippet."

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Programming question to search on Stack Overflow.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        }

    def execute(self, **kwargs: Any) -> str:
        query = str(kwargs.get("query", "")).strip()
        if not query:
            raise ValueError("query is required")
        url = f"https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=relevance&q={quote(query)}&site=stackoverflow&filter=!9_bDDxJY5"
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.get(url)
            resp.raise_for_status()
            items = resp.json().get("items", [])
            if not items:
                return "No results found."
            question_id = items[0]["question_id"]
            answer_url = f"https://api.stackexchange.com/2.3/questions/{question_id}/answers?order=desc&sort=votes&site=stackoverflow&filter=withbody"
            answer_resp = client.get(answer_url)
            answer_resp.raise_for_status()
            answers = answer_resp.json().get("items", [])
            if not answers:
                return f"No answers found for: {items[0]['title']}"
            # Return a snippet of the top answer
            print(answers)
            body = answers[0].get("body", "")
            return body



