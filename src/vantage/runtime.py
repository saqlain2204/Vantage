from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .config import load_agents_from_yaml
from .core.agent import Agent
from .core.bases import ToolBase
from .core.models import AgentResponse


def run_yaml_agent(
    config_path: str | Path,
    agent_name: str,
    prompt: str,
    tools: Optional[List[ToolBase]] = None,
) -> AgentResponse:
    """Run a named agent defined in a YAML config file.

    Supports multi-agent flows: if an agent emits a handover signal via
    ``HandoverTool``, control is automatically transferred to the target agent
    up to five hops deep.
    """
    agents = {a.name: a.agent for a in load_agents_from_yaml(config_path, extra_tools=tools)}
    if agent_name not in agents:
        available = ", ".join(sorted(agents.keys()))
        raise ValueError(f"Unknown agent '{agent_name}'. Available: {available}")

    current_agent_name = agent_name
    current_prompt = prompt
    all_tool_results = []
    all_trace: list = []

    for _ in range(5):
        agent: Agent = agents[current_agent_name]
        resp = agent.run(current_prompt)

        all_tool_results.extend(resp.tool_results)
        all_trace.extend(resp.trace)

        # Detect handover signal from tool results.
        handover: Optional[str] = None
        for res in resp.tool_results:
            if res.output.startswith("Handing over to "):
                handover = res.output.replace("Handing over to ", "").strip()
                break

        if not handover or handover == current_agent_name:
            return AgentResponse(
                content=resp.content,
                tool_results=all_tool_results,
                trace=all_trace,
                next_agent=resp.next_agent,
            )

        previous_agent_name = current_agent_name   # capture BEFORE overwriting
        current_agent_name = handover
        current_prompt = (
            f"Previous agent ({previous_agent_name}) output: {resp.content}. "
            f"Original user request: {prompt}"
        )

    return AgentResponse(
        content=resp.content,
        tool_results=all_tool_results,
        trace=all_trace,
    )


async def async_run_yaml_agent(
    config_path: str | Path,
    agent_name: str,
    prompt: str,
    tools: Optional[List[ToolBase]] = None,
) -> AgentResponse:
    """Async variant of :func:`run_yaml_agent`."""
    from .core.agent import AsyncAgent  # local to avoid circular at module level

    agents = {
        a.name: a.agent
        for a in load_agents_from_yaml(config_path, extra_tools=tools, use_async=True)
    }
    if agent_name not in agents:
        available = ", ".join(sorted(agents.keys()))
        raise ValueError(f"Unknown agent '{agent_name}'. Available: {available}")

    current_agent_name = agent_name
    current_prompt = prompt
    all_tool_results = []
    all_trace: list = []

    for _ in range(5):
        agent_obj: AsyncAgent = agents[current_agent_name]
        resp = await agent_obj.run(current_prompt)

        all_tool_results.extend(resp.tool_results)
        all_trace.extend(resp.trace)

        handover: Optional[str] = None
        for res in resp.tool_results:
            if res.output.startswith("Handing over to "):
                handover = res.output.replace("Handing over to ", "").strip()
                break

        if not handover or handover == current_agent_name:
            return AgentResponse(
                content=resp.content,
                tool_results=all_tool_results,
                trace=all_trace,
                next_agent=resp.next_agent,
            )

        previous_agent_name = current_agent_name
        current_agent_name = handover
        current_prompt = (
            f"Previous agent ({previous_agent_name}) output: {resp.content}. "
            f"Original user request: {prompt}"
        )

    return AgentResponse(
        content=resp.content,
        tool_results=all_tool_results,
        trace=all_trace,
    )

