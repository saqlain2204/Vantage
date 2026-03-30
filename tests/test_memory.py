"""Tests for LocalMemory."""
from __future__ import annotations

from vantage.core.models import Message, Role
from vantage.memory.local import LocalMemory


def _user(text: str) -> Message:
    return Message(role=Role.USER, content=text)


def test_add_and_retrieve():
    mem = LocalMemory()
    msg = _user("hello")
    mem.add(msg)
    assert mem.get_messages() == [msg]


def test_get_returns_copy():
    mem = LocalMemory()
    msg = _user("hello")
    mem.add(msg)
    snapshot = mem.get_messages()
    snapshot.append(_user("injected"))
    assert len(mem.get_messages()) == 1, "mutating the returned list must not affect memory"


def test_clear():
    mem = LocalMemory()
    mem.add(_user("a"))
    mem.add(_user("b"))
    mem.clear()
    assert mem.get_messages() == []


def test_multiple_messages_order():
    mem = LocalMemory()
    msgs = [_user(f"msg{i}") for i in range(5)]
    for m in msgs:
        mem.add(m)
    assert mem.get_messages() == msgs
