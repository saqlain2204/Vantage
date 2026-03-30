from typing import Any, Dict
from ..core.bases import ToolBase

class HandoverTool(ToolBase):
    def __init__(self, agent_name: str, description: str):
        self._name = f"transfer_to_{agent_name}"
        self._description = description
        self._agent_name = agent_name

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def input_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> str:
        return f"Handing over to {self._agent_name}"
