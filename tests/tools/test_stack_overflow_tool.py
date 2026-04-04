"""Tests for StackOverflowTool."""
from __future__ import annotations

import httpx
import pytest
import respx

from vantage.tools.stack_overflow_tool import StackOverflowTool

@respx.mock
def test_execute_returns_answer_snippet() -> None:
    tool = StackOverflowTool()
    # Mock search response
    respx.get("https://api.stackexchange.com/2.3/search/advanced").mock(
        return_value=httpx.Response(200, json={
            "items": [{"question_id": 123, "title": "How to reverse a list in Python?"}]
        })
    )
    # Mock answer response
    respx.get("https://api.stackexchange.com/2.3/questions/123/answers").mock(
        return_value=httpx.Response(200, json={
            "items": [{"body": "<p>You can use <code>list[::-1]</code> to reverse a list.</p>"}]
        })
    )
    result = tool.execute(query="How to reverse a list in Python?")
    assert "reverse a list" in result
    assert "list[::-1]" in result

@respx.mock
def test_execute_no_results() -> None:
    tool = StackOverflowTool()
    respx.get("https://api.stackexchange.com/2.3/search/advanced").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    result = tool.execute(query="some totally random query")
    assert result == "No results found."

@respx.mock
def test_execute_no_answers() -> None:
    tool = StackOverflowTool()
    respx.get("https://api.stackexchange.com/2.3/search/advanced").mock(
        return_value=httpx.Response(200, json={
            "items": [{"question_id": 456, "title": "Unanswered question"}]
        })
    )
    respx.get("https://api.stackexchange.com/2.3/questions/456/answers").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    result = tool.execute(query="Unanswered question")
    assert result.startswith("No answers found for:")

def test_execute_raises_on_empty_query() -> None:
    tool = StackOverflowTool()
    with pytest.raises(ValueError, match="query is required"):
        tool.execute(query="")

def test_execute_raises_on_blank_query() -> None:
    tool = StackOverflowTool()
    with pytest.raises(ValueError, match="query is required"):
        tool.execute(query="   ")
