from __future__ import annotations

from typing import Any, Dict
from urllib.parse import quote

import httpx

from ..core.bases import ToolBase

_DEFAULT_TIMEOUT = 10.0
_RESPONSE_SNIPPET_LENGTH = 200


class WeatherTool(ToolBase):
    def __init__(self, timeout: float = _DEFAULT_TIMEOUT) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "weather_tool"

    @property
    def description(self) -> str:
        return "Fetch weather information for a given location."

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Location for which to fetch weather information, e.g. 'New York, NY'",
                },
            },
            "required": ["location"],
            "additionalProperties": False,
        }

    def execute(self, **kwargs: Any) -> str:
        location = str(kwargs.get("location", ""))
        if not location.strip():
            raise ValueError("location is required")
        encoded_location = quote(location)
        url = f"https://wttr.in/{encoded_location}"
        try:
            response = httpx.get(url, params={"format": "3"}, timeout=self._timeout)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            snippet = body[:_RESPONSE_SNIPPET_LENGTH] + ("..." if len(body) > _RESPONSE_SNIPPET_LENGTH else "")
            message = f"Failed to fetch weather data for {location} (status {exc.response.status_code})."
            if snippet:
                message += f" Response snippet: {snippet}"
            raise RuntimeError(message) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Failed to fetch weather data for {location}: {exc}") from exc
        return response.text


