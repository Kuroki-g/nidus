import pytest
from mcp_server.prompts import custom_instruction

pytestmark = pytest.mark.small


def test_returns_string():
    result = custom_instruction()
    assert isinstance(result, str)


def test_is_not_empty():
    result = custom_instruction()
    assert len(result.strip()) > 0


def test_mentions_search():
    result = custom_instruction()
    assert "search" in result.lower()


def test_mentions_mcp():
    result = custom_instruction()
    assert "mcp" in result.lower() or "MCP" in result
