from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    role: Role
    content: str
    name: Optional[str] = None
    tool_calls: List[ToolCall] = Field(default_factory=list)
    tool_call_id: Optional[str] = None


class TraceStep(BaseModel):
    step_type: Literal["user", "thought", "call", "result", "final"]
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    tool_name: str
    output: str
    is_error: bool = False
    tool_call_id: Optional[str] = None


class AgentResponse(BaseModel):
    content: str
    tool_results: List[ToolResult] = Field(default_factory=list)
    next_agent: Optional[str] = None
    trace: List[TraceStep] = Field(default_factory=list)
