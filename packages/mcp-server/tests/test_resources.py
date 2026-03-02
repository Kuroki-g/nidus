from unittest.mock import patch

import pytest
from mcp_server.resources import get_single_doc

pytestmark = pytest.mark.small


def test_found_returns_source_and_name():
    mock_results = [{"source": "/path/to/doc.md", "doc_name": "doc.md"}]
    with patch("cli.db.search_db.list_docs_in_db", return_value=mock_results):
        result = get_single_doc("/path/to/doc.md")
    assert "/path/to/doc.md" in result
    assert "doc.md" in result


def test_not_found_returns_message():
    with patch("cli.db.search_db.list_docs_in_db", return_value=[]):
        result = get_single_doc("/nonexistent/path.md")
    assert "not found" in result.lower() or "was not found" in result


def test_multiple_results_all_listed():
    mock_results = [
        {"source": "/path/a.md", "doc_name": "a.md"},
        {"source": "/path/b.md", "doc_name": "b.md"},
    ]
    with patch("cli.db.search_db.list_docs_in_db", return_value=mock_results):
        result = get_single_doc("/path/")
    assert "/path/a.md" in result
    assert "/path/b.md" in result


def test_missing_doc_name_handled():
    mock_results = [{"source": "/path/doc.md"}]
    with patch("cli.db.search_db.list_docs_in_db", return_value=mock_results):
        result = get_single_doc("/path/doc.md")
    assert "/path/doc.md" in result
