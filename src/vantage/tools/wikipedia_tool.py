from __future__ import annotations

import re
from typing import Any, Dict
from urllib.parse import urlencode

import httpx

from ..core.bases import ToolBase

_DEFAULT_TIMEOUT = 10.0
_RESPONSE_SNIPPET_LENGTH = 200


class WikipediaTool(ToolBase):
    def __init__(self, timeout: float = _DEFAULT_TIMEOUT) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "wikipedia_search"

    @property
    def description(self) -> str:
        return "Search Wikipedia for a given query and return a brief summary of top results."

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query, e.g. 'Albert Einstein'",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        }

    def execute(self, **kwargs: Any) -> str:
        query = str(kwargs.get("query", ""))
        if not query.strip():
            raise ValueError("query is required")
            
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "utf8": "",
            "format": "json"
        }
        url = f"https://en.wikipedia.org/w/api.php?{urlencode(params)}"
        try:
            response = httpx.get(url, timeout=self._timeout)
            response.raise_for_status()
            data = response.json()
            search_results = data.get("query", {}).get("search", [])
            if not search_results:
                return "No results found."
            
            output = []
            for item in search_results[:3]: # return top 3
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                # Clean up simple HTML tags from the snippet
                snippet = re.sub(r'<[^>]+>', '', snippet)
                output.append(f"Title: {title}\nSummary: {snippet}")
                
            return "\n\n".join(output)
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            snippet = body[:_RESPONSE_SNIPPET_LENGTH] + ("..." if len(body) > _RESPONSE_SNIPPET_LENGTH else "")
            message = f"Failed to fetch Wikipedia data for query '{query}' (status {exc.response.status_code})."
            if snippet:
                message += f" Response snippet: {snippet}"
            raise RuntimeError(message) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Failed to fetch Wikipedia data for query '{query}': {exc}") from exc
        except ValueError as exc:
             raise RuntimeError(f"Failed to parse Wikipedia response for query '{query}': {exc}") from exc
