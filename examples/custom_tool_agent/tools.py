from __future__ import annotations

from typing import Any, Dict

from vantage.core import ToolBase


class WordCountTool(ToolBase):
    @property
    def name(self) -> str:
        return "word_count"

    @property
    def description(self) -> str:
        return "Count words in the given text."

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to count words in.",
                },
            },
            "required": ["text"],
            "additionalProperties": False,
        }

    def execute(self, **kwargs: Any) -> str:
        text = str(kwargs.get("text", ""))
        count = len([w for w in text.split() if w])
        return str(count)

