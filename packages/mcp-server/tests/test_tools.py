from unittest.mock import patch

import pytest
from mcp_server.tools import db_show_meta, list_docs, search_docs, update_docs

pytestmark = pytest.mark.small


# ── search_docs ────────────────────────────────────────────────────────────────

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


# ── list_docs ──────────────────────────────────────────────────────────────────

def test_list_docs_not_found():
    with patch("cli.db.search_db.list_docs_in_db", return_value=[]):
        result = list_docs("nonexistent")
    assert "was not found" in result


def test_list_docs_returns_formatted_result():
    mock_results = [{"source": "/path/to/doc.md", "doc_name": "doc.md"}]
    with patch("cli.db.search_db.list_docs_in_db", return_value=mock_results):
        result = list_docs("doc")
    assert "/path/to/doc.md" in result
    assert "doc.md" in result


def test_list_docs_multiple_results():
    mock_results = [
        {"source": "/path/a.md", "doc_name": "a.md"},
        {"source": "/path/b.md", "doc_name": "b.md"},
    ]
    with patch("cli.db.search_db.list_docs_in_db", return_value=mock_results):
        result = list_docs("path")
    assert "/path/a.md" in result
    assert "/path/b.md" in result


# ── update_docs ────────────────────────────────────────────────────────────────

def test_update_docs_success_returns_none():
    with patch("mcp_server.tools.update_files_in_db"):
        result = update_docs([])
    assert result is None


def test_update_docs_on_exception_returns_error_message():
    with patch("mcp_server.tools.update_files_in_db", side_effect=RuntimeError("db error")):
        result = update_docs([])
    assert result is not None
    assert "failed" in result.lower() or "db error" in result


# ── db_show_meta ───────────────────────────────────────────────────────────────

class _MockField:
    def __init__(self, name: str, typ: str) -> None:
        self.name = name
        self.type = typ


def test_db_show_meta_contains_path():
    mock_meta = {
        "database_path": "/tmp/.lancedb",
        "total_tables": 1,
        "tables": [
            {
                "table_name": "doc_chunk",
                "record_count": 10,
                "version": 1,
                "schema": [_MockField("chunk_id", "int64"), _MockField("chunk_text", "string")],
            }
        ],
    }
    with patch("cli.meta.db_info.get_meta", return_value=mock_meta):
        result = db_show_meta()
    assert "/tmp/.lancedb" in result
    assert "doc_chunk" in result


def test_db_show_meta_contains_record_count():
    mock_meta = {
        "database_path": "/tmp/.lancedb",
        "total_tables": 1,
        "tables": [
            {
                "table_name": "doc_meta",
                "record_count": 42,
                "version": 2,
                "schema": [_MockField("source", "string")],
            }
        ],
    }
    with patch("cli.meta.db_info.get_meta", return_value=mock_meta):
        result = db_show_meta()
    assert "42" in result


def test_db_show_meta_truncates_many_fields():
    """フィールドが max_fields(10) を超えた場合に省略表記が入る。"""
    many_fields = [_MockField(f"col{i}", "string") for i in range(15)]
    mock_meta = {
        "database_path": "/tmp/.lancedb",
        "total_tables": 1,
        "tables": [
            {
                "table_name": "big_table",
                "record_count": 0,
                "version": 1,
                "schema": many_fields,
            }
        ],
    }
    with patch("cli.meta.db_info.get_meta", return_value=mock_meta):
        result = db_show_meta()
    assert "more" in result
