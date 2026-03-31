"""Tests for WeatherTool."""
from __future__ import annotations

import httpx
import pytest
import respx

from vantage.tools.weather_tool import WeatherTool


@respx.mock
def test_execute_returns_weather_text() -> None:
    tool = WeatherTool()
    respx.get("https://wttr.in/London").mock(
        return_value=httpx.Response(200, text="London: ⛅  +15°C")
    )
    result = tool.execute(location="London")
    assert result == "London: ⛅  +15°C"


@respx.mock
def test_execute_url_encodes_location() -> None:
    tool = WeatherTool()
    respx.get("https://wttr.in/New%20York").mock(
        return_value=httpx.Response(200, text="New York: ☀  +22°C")
    )
    result = tool.execute(location="New York")
    assert "New York" in result


def test_execute_raises_on_empty_location() -> None:
    tool = WeatherTool()
    with pytest.raises(ValueError, match="location is required"):
        tool.execute(location="")


def test_execute_raises_on_blank_location() -> None:
    tool = WeatherTool()
    with pytest.raises(ValueError, match="location is required"):
        tool.execute(location="   ")


@respx.mock
def test_execute_raises_runtime_error_on_http_error() -> None:
    tool = WeatherTool()
    respx.get("https://wttr.in/BadLocation").mock(
        return_value=httpx.Response(404, text="Not Found")
    )
    with pytest.raises(RuntimeError, match="status 404"):
        tool.execute(location="BadLocation")


@respx.mock
def test_execute_raises_runtime_error_on_network_error() -> None:
    tool = WeatherTool()
    respx.get("https://wttr.in/London").mock(side_effect=httpx.ConnectError("DNS failure"))
    with pytest.raises(RuntimeError, match="Failed to fetch weather data for London"):
        tool.execute(location="London")


def test_tool_name() -> None:
    assert WeatherTool().name == "weather_tool"


def test_tool_description() -> None:
    assert "weather" in WeatherTool().description.lower()


def test_input_schema_requires_location() -> None:
    schema = WeatherTool().input_schema()
    assert "location" in schema["required"]
