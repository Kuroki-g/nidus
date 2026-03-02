import pytest
from mcp_server.tools import search_docs

pytestmark = pytest.mark.medium


def test_some_function():
    words = "keywords"
    assert search_docs(words) == f"Searching for: {words}"
