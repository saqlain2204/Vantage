from __future__ import annotations

import ast
import operator
from typing import Any, Dict

from ..core.bases import ToolBase
from typing import Callable
import requests


class WeatherTool(ToolBase):
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
        url = f"https://wttr.in/{location}?format=3"
        response = requests.get(url)
        if response.status_code != 200:
            raise RuntimeError(f"Failed to fetch weather data for {location}")
        return response.text


