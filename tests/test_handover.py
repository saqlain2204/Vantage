"""Tests for HandoverTool."""
from __future__ import annotations

from vantage.core.handovers import HandoverTool


def test_name_includes_agent_name():
    ht = HandoverTool("billing", "Transfer to billing agent.")
    assert ht.name == "transfer_to_billing"


def test_execute_returns_handover_string():
    ht = HandoverTool("support", "Transfer to support.")
    result = ht.execute()
    assert result == "Handing over to support"


def test_description_preserved():
    ht = HandoverTool("sales", "Sales handover.")
    assert ht.description == "Sales handover."


def test_input_schema_is_empty_object():
    ht = HandoverTool("ops", "Ops.")
    schema = ht.input_schema()
    assert schema.get("type") == "object"
    assert schema.get("properties") == {}
