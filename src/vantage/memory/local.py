from typing import List

from ..core.bases import MemoryBase
from ..core.models import Message


class LocalMemory(MemoryBase):
    def __init__(self) -> None:
        self._messages: List[Message] = []

    def add(self, message: Message) -> None:
        self._messages.append(message)

    def get_messages(self) -> List[Message]:
        # Return a copy so callers cannot mutate the internal store.
        return list(self._messages)

    def clear(self) -> None:
        self._messages = []
