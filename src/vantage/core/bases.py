from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

from .models import Message


class ToolBase(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    def input_schema(self) -> Dict[str, Any]: ...

    @abstractmethod
    def execute(self, **kwargs: Any) -> str: ...


class LLMBase(ABC):
    @abstractmethod
    def generate(
        self,
        messages: List[Message],
        tools: List[ToolBase],
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> Message: ...


class AsyncLLMBase(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        tools: List[ToolBase],
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> Message: ...

    def generate_stream(
        self,
        messages: List[Message],
        tools: List[ToolBase],
    ) -> AsyncIterator[str]:
        """Stream token chunks.  Default implementation yields the full response as one chunk."""
        return _default_stream(self, messages, tools)


async def _default_stream(
    llm: AsyncLLMBase,
    messages: List[Message],
    tools: List[ToolBase],
) -> AsyncIterator[str]:
    """Fallback: call generate() and yield the whole content at once."""
    response = await llm.generate(messages, tools)
    if response.content:
        yield response.content


class MemoryBase(ABC):
    @abstractmethod
    def add(self, message: Message) -> None: ...

    @abstractmethod
    def get_messages(self) -> List[Message]: ...

    @abstractmethod
    def clear(self) -> None: ...

