from unittest.mock import patch

import pytest
from mcp_server.tools import search_docs

pytestmark = pytest.mark.small


def test_search_docs_not_found():
    with patch("mcp_server.tools.search_docs_in_db", return_value=[]):
        result = search_docs("notfound")
    assert result == "'notfound' was not found."


def test_search_docs_returns_formatted_result():
    from cli.db.search_db import SearchMethod

    mock_results = [
        {
            "source": "/path/to/doc.md",
            "method": SearchMethod.Hybrid,
            "score": 0.9500,
            "text": "サンプルテキスト",
            "chunk_id": 0,
        }
    ]
    with patch("mcp_server.tools.search_docs_in_db", return_value=mock_results):
        result = search_docs("テスト")

    assert "/path/to/doc.md" in result
    assert "0.9500" in result
    assert "サンプルテキスト" in result
