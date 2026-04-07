from __future__ import annotations

from typing import Any, Dict

import httpx

from ..core.bases import ToolBase

_DEFAULT_TIMEOUT = 10.0
_RESPONSE_SNIPPET_LENGTH = 200


class DictionaryTool(ToolBase):
    def __init__(self, timeout: float = _DEFAULT_TIMEOUT) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "dictionary_search"

    @property
    def description(self) -> str:
        return "Search for the definition, phonetic, and part of speech of an English word."

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "word": {
                    "type": "string",
                    "description": "The word to look up, e.g. 'hello'",
                },
            },
            "required": ["word"],
            "additionalProperties": False,
        }

    def execute(self, **kwargs: Any) -> str:
        word = str(kwargs.get("word", ""))
        if not word.strip():
            raise ValueError("word is required")
            
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        try:
            response = httpx.get(url, timeout=self._timeout)
            
            if response.status_code == 404:
                return f"No definition found for the word '{word}'."
                
            response.raise_for_status()
            data = response.json()
            
            if not isinstance(data, list) or not data:
                return f"No definition found for the word '{word}'."
                
            entry = data[0]
            word_name = entry.get("word", word)
            phonetics = entry.get("phonetic", "")
            
            output = [f"Word: {word_name}"]
            if phonetics:
                output.append(f"Phonetic: {phonetics}")
                
            meanings = entry.get("meanings", [])
            for meaning in meanings:
                part_of_speech = meaning.get("partOfSpeech", "")
                definitions = meaning.get("definitions", [])
                
                output.append(f"\nPart of Speech: {part_of_speech}")
                for i, dfn in enumerate(definitions[:3], start=1):
                    definition_text = dfn.get("definition", "")
                    output.append(f"  {i}. {definition_text}")
                    
            return "\n".join(output)
            
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            snippet = body[:_RESPONSE_SNIPPET_LENGTH] + ("..." if len(body) > _RESPONSE_SNIPPET_LENGTH else "")
            message = f"Failed to fetch dictionary data for word '{word}' (status {exc.response.status_code})."
            if snippet:
                message += f" Response snippet: {snippet}"
            raise RuntimeError(message) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Failed to fetch dictionary data for word '{word}': {exc}") from exc
        except ValueError as exc:
             raise RuntimeError(f"Failed to parse dictionary response for word '{word}': {exc}") from exc
