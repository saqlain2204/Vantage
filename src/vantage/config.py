from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import yaml

from .core.agent import Agent
from .core.bases import ToolBase
from .llms import GroqModel, OpenAIModel
from .memory.local import LocalMemory
from .tools import Calculator


@dataclass(frozen=True)
class LoadedAgent:
    name: str
    agent: Any


def load_agents_from_yaml(
    path: str | Path,
    extra_tools: Optional[List[ToolBase]] = None,
    use_async: bool = False,
) -> List[LoadedAgent]:
    """Load agents from a YAML configuration file.

    Supports two formats for specifying the LLM:

    **New flat format (recommended)**::

        agents:
          my_agent:
            model: groq/llama-3.3-70b-versatile
            system_prompt: "You are a helpful assistant."
            tools: [calculator]

    **Legacy format** with a top-level ``providers`` block::

        providers:
          groq: llama-3.3-70b-versatile

        agents:
          my_agent:
            provider: groq
            ...

    ``response_schema`` accepts a flat ``{field: type}`` shorthand::

        response_schema:
          result: number
          summary: string

    or a full JSON Schema object.
    """
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(data, Mapping):
        raise ValueError("YAML root must be a mapping")

    providers = _ensure_mapping(data.get("providers", {}), "providers")
    tools_cfg = _ensure_mapping(data.get("tools", {}), "tools")
    agents_cfg = _ensure_mapping(data.get("agents", {}), "agents")

    tool_instances = _build_tools(tools_cfg)
    if extra_tools:
        for t in extra_tools:
            tool_instances[t.name] = t

    loaded: List[LoadedAgent] = []
    for name, cfg_any in agents_cfg.items():
        cfg = _ensure_mapping(cfg_any, f"agents.{name}")

        # Determine LLM — prefer new inline `model:` key, fall back to `provider:`.
        if "model" in cfg:
            llm = _build_llm_from_model_string(str(cfg["model"]), name, use_async=use_async)
        elif "provider" in cfg:
            provider_name = str(cfg["provider"])
            provider_cfg = providers.get(provider_name)
            if provider_cfg is None:
                raise ValueError(
                    f"agents.{name}.provider='{provider_name}' not found in the providers block. "
                    f"Use the inline format instead: model: {provider_name}/<model-name>"
                )
            llm = _build_llm(provider_name, provider_cfg, use_async=use_async)
        else:
            raise ValueError(
                f"agents.{name} must specify either 'model: provider/model-name' "
                f"or 'provider: <name>' with a matching providers block."
            )

        system_prompt = str(cfg.get("system_prompt") or "You are a helpful assistant.")
        max_turns = int(cfg.get("max_turns") or 12)

        response_schema: Optional[Dict[str, Any]] = None
        raw_schema = cfg.get("response_schema")
        if raw_schema is not None:
            response_schema = _expand_response_schema(
                _ensure_mapping(raw_schema, f"agents.{name}.response_schema"),
                f"agents.{name}.response_schema",
            )

        # Validate memory type if specified — only "local" is currently supported.
        mem_cfg = cfg.get("memory")
        if mem_cfg is not None:
            if isinstance(mem_cfg, str):
                mem_type = mem_cfg
            else:
                mem_type = str(
                    _ensure_mapping(mem_cfg, f"agents.{name}.memory").get("type", "local")
                )
            if mem_type != "local":
                raise ValueError(
                    f"agents.{name}.memory: unsupported type '{mem_type}'. Only 'local' is available."
                )

        tool_names = cfg.get("tools") or []
        if not isinstance(tool_names, list):
            raise ValueError(f"agents.{name}.tools must be a list")
        tools: List[ToolBase] = []
        for tname_any in tool_names:
            tname = str(tname_any)
            if tname not in tool_instances:
                raise ValueError(f"Unknown tool referenced by agent '{name}': {tname}")
            tools.append(tool_instances[tname])

        if use_async:
            from .core.agent import AsyncAgent  # local import to avoid circular at module level

            agent_obj: Any = AsyncAgent(
                llm=llm,
                tools=tools,
                memory=LocalMemory(),
                system_prompt=system_prompt,
                max_turns=max_turns,
                response_schema=response_schema,
            )
        else:
            agent_obj = Agent(
                llm=llm,
                tools=tools,
                memory=LocalMemory(),
                system_prompt=system_prompt,
                max_turns=max_turns,
                response_schema=response_schema,
            )

        loaded.append(LoadedAgent(name=name, agent=agent_obj))

    return loaded


def _build_llm_from_model_string(model_str: str, agent_name: str, *, use_async: bool = False) -> Any:
    """Parse ``provider/model-name`` or well-known OpenAI model prefixes into an LLM."""
    if "/" in model_str:
        ptype, model = model_str.split("/", 1)
    elif model_str.startswith(("gpt-", "o1", "o3", "o4")):
        ptype, model = "openai", model_str
    else:
        raise ValueError(
            f"agents.{agent_name}.model='{model_str}': cannot infer provider. "
            f"Use 'provider/model-name', e.g. 'groq/llama-3.3-70b-versatile' or 'openai/gpt-4o-mini'."
        )

    if ptype == "openai":
        if use_async:
            from .llms.openai import AsyncOpenAIModel
            return AsyncOpenAIModel(model=model)
        return OpenAIModel(model=model)
    if ptype == "groq":
        if use_async:
            from .llms.groq import AsyncGroqModel
            return AsyncGroqModel(model=model)
        return GroqModel(model=model)
    raise ValueError(
        f"agents.{agent_name}.model='{model_str}': unknown provider '{ptype}'. "
        f"Supported providers: openai, groq."
    )


def _build_llm(name: str, cfg_any: Any, *, use_async: bool = False) -> Any:
    """Build an LLM from a legacy ``providers:`` block entry."""
    if isinstance(cfg_any, str):
        ptype = name
        model = cfg_any
        cfg: Mapping[str, Any] = {}
    elif isinstance(cfg_any, Mapping):
        cfg = cfg_any
        ptype = str(cfg.get("type") or name)
        model = str(cfg.get("model") or "")
    else:
        raise ValueError(f"Invalid provider config for '{name}'")

    if not model:
        raise ValueError(f"providers.{name}.model is required")

    timeout_s = float(cfg.get("timeout_s") or 60.0)
    temperature = cfg.get("temperature")
    max_completion_tokens = cfg.get("max_completion_tokens")
    top_p = cfg.get("top_p")

    if ptype == "openai":
        if use_async:
            from .llms.openai import AsyncOpenAIModel
            return AsyncOpenAIModel(
                model=model,
                api_key=cfg.get("api_key"),
                base_url=cfg.get("base_url"),
                timeout_s=timeout_s,
                temperature=float(temperature) if temperature is not None else None,
                max_completion_tokens=int(max_completion_tokens) if max_completion_tokens is not None else None,
                top_p=float(top_p) if top_p is not None else None,
            )
        return OpenAIModel(
            model=model,
            api_key=cfg.get("api_key"),
            base_url=cfg.get("base_url"),
            timeout_s=timeout_s,
            temperature=float(temperature) if temperature is not None else None,
            max_completion_tokens=int(max_completion_tokens) if max_completion_tokens is not None else None,
            top_p=float(top_p) if top_p is not None else None,
        )
    if ptype == "groq":
        if use_async:
            from .llms.groq import AsyncGroqModel
            return AsyncGroqModel(
                model=model,
                api_key=cfg.get("api_key"),
                base_url=cfg.get("base_url"),
                timeout_s=timeout_s,
                temperature=float(temperature) if temperature is not None else None,
                max_completion_tokens=int(max_completion_tokens) if max_completion_tokens is not None else None,
                top_p=float(top_p) if top_p is not None else None,
            )
        return GroqModel(
            model=model,
            api_key=cfg.get("api_key"),
            base_url=cfg.get("base_url"),
            timeout_s=timeout_s,
            temperature=float(temperature) if temperature is not None else None,
            max_completion_tokens=int(max_completion_tokens) if max_completion_tokens is not None else None,
            top_p=float(top_p) if top_p is not None else None,
        )
    raise ValueError(f"Unknown provider type '{ptype}'. Supported: openai, groq.")


def _build_tools(cfg: Mapping[str, Any]) -> Dict[str, ToolBase]:
    out: Dict[str, ToolBase] = {}
    for name, spec_any in cfg.items():
        if isinstance(spec_any, str):
            ttype = spec_any
            spec: Mapping[str, Any] = {}
        elif isinstance(spec_any, Mapping):
            spec = spec_any
            ttype = str(spec.get("type") or "")
            if not ttype and "class" in spec:
                ttype = "python"
            if not ttype:
                ttype = name
        else:
            raise ValueError(f"Invalid tool config for '{name}'")

        if ttype == "calculator":
            out[name] = Calculator()
        elif ttype == "python":
            class_path = str(spec.get("class") or "")
            if not class_path:
                raise ValueError(f"tools.{name}.class is required for python tools")
            module_name, _, cls_name = class_path.rpartition(".")
            if not module_name or not cls_name:
                raise ValueError(f"tools.{name}.class must be 'module.ClassName'")
            module = importlib.import_module(module_name)
            tool_cls = getattr(module, cls_name)
            if not (isinstance(tool_cls, type) and issubclass(tool_cls, ToolBase)):
                raise ValueError(
                    f"tools.{name}.class '{class_path}' must be a subclass of ToolBase"
                )
            out[name] = tool_cls()
        else:
            raise ValueError(
                f"Unsupported tool type '{ttype}' for tool '{name}'. "
                f"Built-in types: 'calculator'. For custom tools use type: python."
            )
    return out


_SHORTHAND_TYPES = frozenset({"string", "number", "integer", "boolean", "array", "object"})


def _expand_response_schema(schema: Mapping[str, Any], path: str) -> Dict[str, Any]:
    """Expand a flat ``{field: type}`` shorthand to a full JSON Schema object.

    If the mapping already contains a ``type`` or ``properties`` key it is
    treated as a full JSON Schema and returned unchanged.
    """
    # Already a full JSON Schema
    if "type" in schema or "properties" in schema:
        return dict(schema)

    # Shorthand: every value must be a plain type-name string
    if all(isinstance(v, str) and v in _SHORTHAND_TYPES for v in schema.values()):
        return {
            "type": "object",
            "properties": {k: {"type": v} for k, v in schema.items()},
            "required": list(schema.keys()),
            "additionalProperties": False,
        }

    raise ValueError(
        f"{path}: response_schema must be a flat {{field: type}} shorthand "
        f"(e.g. 'result: number') or a valid JSON Schema with a 'type'/'properties' key. "
        f"Valid shorthand types: {', '.join(sorted(_SHORTHAND_TYPES))}."
    )


def _ensure_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be a mapping")
    return value

