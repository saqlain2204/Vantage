
import respx
import httpx

from vantage.config import load_agents_from_yaml


def _write(tmp_path, name: str, content: str):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


@respx.mock
def test_openai_compatible_text_response(tmp_path):
    cfg = _write(
        tmp_path,
        "agents.yaml",
        """
providers:
  openai:
    type: openai
    model: gpt-4o-mini
    api_key: test
    base_url: https://api.openai.com/v1

tools: {}

agents:
  a:
    provider: openai
""",
    )

    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"role": "assistant", "content": "hello", "tool_calls": []}}
                ]
            },
        )
    )

    agent = {a.name: a.agent for a in load_agents_from_yaml(cfg)}["a"]
    resp = agent.run("hi")
    assert resp.content == "hello"


@respx.mock
def test_groq_uses_openai_compatible_endpoint(tmp_path):
    cfg = _write(
        tmp_path,
        "agents.yaml",
        """
providers:
  groq:
    type: groq
    model: llama-3.1-70b-versatile
    api_key: test
    base_url: https://api.groq.com/openai/v1

tools:
  calc:
    type: calculator

agents:
  a:
    provider: groq
    tools: [calc]
""",
    )

    respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"role": "assistant", "content": "ok", "tool_calls": []}}
                ]
            },
        )
    )

    agent = {a.name: a.agent for a in load_agents_from_yaml(cfg)}["a"]
    resp = agent.run("hi")
    assert resp.content == "ok"


@respx.mock
def test_tool_call_round_trip(tmp_path):
    cfg = _write(
        tmp_path,
        "agents.yaml",
        """
providers:
  openai:
    type: openai
    model: gpt-4o-mini
    api_key: test
    base_url: https://api.openai.com/v1

tools:
  calc:
    type: calculator

agents:
  a:
    provider: openai
    tools: [calc]
""",
    )

    route = respx.post("https://api.openai.com/v1/chat/completions")

    route.side_effect = [
        httpx.Response(
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
                                    "function": {"name": "calculator", "arguments": '{"expression":"2+2"}'},
                                }
                            ],
                        }
                    }
                ]
            },
        ),
        httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"role": "assistant", "content": "4", "tool_calls": []}}
                ]
            },
        ),
    ]

    agent = {a.name: a.agent for a in load_agents_from_yaml(cfg)}["a"]
    resp = agent.run("what is 2+2")
    assert resp.content == "4"
    assert resp.tool_results and resp.tool_results[0].output == "4"

