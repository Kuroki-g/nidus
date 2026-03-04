import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from cli.db.search_db import (
    DocListEntry,
    SearchMethod,
    SearchResult,
    _get_adjacent_text,
    _rrf_score,
    display_list_results_simple,
    display_results_json,
    display_results_simple,
    list_docs_in_db,
    search_docs_in_db,
)

pytestmark = pytest.mark.small


class TestRrfScore:
    def test_rank0_formula(self):
        # 1 / (k + 0 + 1) = 1 / (k+1)
        assert _rrf_score(0, 60) == pytest.approx(1.0 / 61)

    def test_higher_rank_lower_score(self):
        assert _rrf_score(0, 60) > _rrf_score(1, 60)
        assert _rrf_score(1, 60) > _rrf_score(2, 60)

    def test_larger_k_lower_score(self):
        # k が大きいほどスコアは小さくなる
        assert _rrf_score(0, 10) > _rrf_score(0, 60)

    def test_score_always_positive(self):
        assert _rrf_score(0, 0) > 0
        assert _rrf_score(100, 60) > 0


class TestGetAdjacentText:
    def _make_table(self, rows: list[dict]) -> MagicMock:
        mock_table = MagicMock()
        (
            mock_table.search.return_value.where.return_value.select.return_value.to_list
        ).return_value = rows
        return mock_table

    def test_concatenates_chunks_in_order(self):
        rows = [
            {"chunk_id": 1, "chunk_text": "second"},
            {"chunk_id": 0, "chunk_text": "first"},
        ]
        result = _get_adjacent_text(self._make_table(rows), "/a.md", 0, 1)
        assert result == "first\nsecond"

    def test_single_chunk(self):
        rows = [{"chunk_id": 2, "chunk_text": "only"}]
        result = _get_adjacent_text(self._make_table(rows), "/a.md", 2, 0)
        assert result == "only"

    def test_empty_rows_returns_empty_string(self):
        result = _get_adjacent_text(self._make_table([]), "/a.md", 0, 1)
        assert result == ""

    def test_window_lower_bound_clamped_to_zero(self):
        """chunk_id=0, window=2 のとき lo=0 になること。"""
        mock_table = MagicMock()
        (
            mock_table.search.return_value.where.return_value.select.return_value.to_list
        ).return_value = []
        _get_adjacent_text(mock_table, "/a.md", 0, 2)
        call_args = mock_table.search.return_value.where.call_args[0][0]
        assert "chunk_id >= 0" in call_args


class TestListDocsInDb:
    def _make_ldb_mock(self, rows: list[dict]) -> MagicMock:
        mock_table = MagicMock()
        chain = mock_table.search.return_value.select.return_value
        chain.limit.return_value.to_list.return_value = rows
        chain.where.return_value.limit.return_value.to_list.return_value = rows
        return mock_table

    def test_returns_results_without_keyword(self):
        rows = [{"source": "/a.md", "doc_name": "a.md"}]
        mock_table = self._make_ldb_mock(rows)
        with patch("cli.db.search_db.LanceDBManager") as mock_ldb:
            mock_ldb.return_value.db.open_table.return_value = mock_table
            result = list_docs_in_db(None)
        assert result == rows

    def test_applies_where_clause_with_keyword(self):
        mock_table = self._make_ldb_mock([])
        with patch("cli.db.search_db.LanceDBManager") as mock_ldb:
            mock_ldb.return_value.db.open_table.return_value = mock_table
            list_docs_in_db("notes")
        mock_table.search.return_value.select.return_value.where.assert_called_once()
        where_arg = mock_table.search.return_value.select.return_value.where.call_args[0][0]
        assert "notes" in where_arg

    def test_returns_empty_on_exception(self):
        with patch("cli.db.search_db.LanceDBManager") as mock_ldb:
            mock_ldb.return_value.db.open_table.side_effect = Exception("no table")
            result = list_docs_in_db(None)
        assert result == []


class TestSearchDocsInDb:
    def _build_search_side_effect(
        self,
        fts_rows: list[dict],
        vec_rows: list[dict],
        adj_rows: list[dict],
    ):
        def _side_effect(*args, **kwargs):
            m = MagicMock()
            if kwargs.get("query_type") == "fts":
                m.select.return_value.limit.return_value.to_list.return_value = fts_rows
            elif "vector_column_name" in kwargs:
                m.select.return_value.limit.return_value.to_list.return_value = vec_rows
            else:
                m.where.return_value.select.return_value.to_list.return_value = adj_rows
            return m

        return _side_effect

    def test_returns_empty_on_exception(self):
        with patch("cli.db.search_db.LanceDBManager") as mock_ldb:
            mock_ldb.return_value.db.open_table.side_effect = Exception("no table")
            result = search_docs_in_db("test")
        assert result == []

    def test_short_keyword_skips_fts(self):
        """1文字クエリは FTS をスキップしてベクター検索のみ実行する。"""
        mock_embed = MagicMock()
        mock_embed.encode.return_value = np.zeros(4, dtype=np.float32)
        vec_rows = [{"source": "/a.md", "chunk_id": 0, "chunk_text": "content", "_distance": 0.1}]
        adj_rows = [{"chunk_id": 0, "chunk_text": "content"}]
        mock_table = MagicMock()
        mock_table.search.side_effect = self._build_search_side_effect([], vec_rows, adj_rows)

        with (
            patch("cli.db.search_db.LanceDBManager") as mock_ldb,
            patch("cli.db.search_db.EmbeddingModelManager") as mock_emm,
        ):
            mock_ldb.return_value.db.open_table.return_value = mock_table
            mock_emm.return_value.model = mock_embed
            results = search_docs_in_db("a")

        fts_calls = [
            c for c in mock_table.search.call_args_list if c.kwargs.get("query_type") == "fts"
        ]
        assert len(fts_calls) == 0
        assert len(results) == 1
        assert results[0]["method"] == SearchMethod.Semantic

    def test_hybrid_result_when_both_match(self):
        """FTS とベクター両方にヒットしたチャンクは Hybrid になる。"""
        mock_embed = MagicMock()
        mock_embed.encode.return_value = np.zeros(4, dtype=np.float32)
        fts_rows = [{"source": "/a.md", "chunk_id": 0, "chunk_text": "hello", "_score": 1.0}]
        vec_rows = [{"source": "/a.md", "chunk_id": 0, "chunk_text": "hello", "_distance": 0.1}]
        adj_rows = [{"chunk_id": 0, "chunk_text": "hello world"}]
        mock_table = MagicMock()
        mock_table.search.side_effect = self._build_search_side_effect(fts_rows, vec_rows, adj_rows)

        with (
            patch("cli.db.search_db.LanceDBManager") as mock_ldb,
            patch("cli.db.search_db.EmbeddingModelManager") as mock_emm,
        ):
            mock_ldb.return_value.db.open_table.return_value = mock_table
            mock_emm.return_value.model = mock_embed
            results = search_docs_in_db("hello world")

        assert len(results) == 1
        assert results[0]["method"] == SearchMethod.Hybrid
        assert results[0]["source"] == "/a.md"

    def test_fts_only_result_is_keyword(self):
        """FTS のみにヒットしたチャンクは Keyword になる。"""
        mock_embed = MagicMock()
        mock_embed.encode.return_value = np.zeros(4, dtype=np.float32)
        fts_rows = [{"source": "/a.md", "chunk_id": 0, "chunk_text": "hello", "_score": 1.0}]
        vec_rows = [{"source": "/b.md", "chunk_id": 0, "chunk_text": "other", "_distance": 0.5}]
        adj_rows = [{"chunk_id": 0, "chunk_text": "hello"}]
        mock_table = MagicMock()
        mock_table.search.side_effect = self._build_search_side_effect(fts_rows, vec_rows, adj_rows)

        with (
            patch("cli.db.search_db.LanceDBManager") as mock_ldb,
            patch("cli.db.search_db.EmbeddingModelManager") as mock_emm,
        ):
            mock_ldb.return_value.db.open_table.return_value = mock_table
            mock_emm.return_value.model = mock_embed
            results = search_docs_in_db("hello world")

        methods = {r["source"]: r["method"] for r in results}
        assert methods["/a.md"] == SearchMethod.Keyword


class TestDisplayResultsSimple:
    def test_outputs_header(self, capsys):
        display_results_simple([])
        out = capsys.readouterr().out
        assert "Score" in out
        assert "Method" in out
        assert "Source" in out

    def test_outputs_result_row(self, capsys):
        results: list[SearchResult] = [
            SearchResult(
                score=0.9500,
                method=SearchMethod.Hybrid,
                source="/path/doc.md",
                text="テストテキスト",
                chunk_id=0,
            )
        ]
        display_results_simple(results)
        out = capsys.readouterr().out
        assert "0.9500" in out
        assert "Hybrid" in out

    def test_keyword_method_displayed(self, capsys):
        results: list[SearchResult] = [
            SearchResult(
                score=0.5,
                method=SearchMethod.Keyword,
                source="/doc.md",
                text="内容",
                chunk_id=0,
            )
        ]
        display_results_simple(results)
        out = capsys.readouterr().out
        assert "Keyword" in out

    def test_long_source_truncated(self, capsys):
        results: list[SearchResult] = [
            SearchResult(
                score=0.5,
                method=SearchMethod.Semantic,
                source="/" + "x" * 50 + "/doc.md",
                text="text",
                chunk_id=0,
            )
        ]
        display_results_simple(results)
        out = capsys.readouterr().out
        # 16文字を超えたら ".." が付く
        assert ".." in out

    def test_short_source_not_truncated(self, capsys):
        results: list[SearchResult] = [
            SearchResult(
                score=0.5,
                method=SearchMethod.Hybrid,
                source="/a.md",
                text="text",
                chunk_id=0,
            )
        ]
        display_results_simple(results)
        out = capsys.readouterr().out
        assert "/a.md" in out


class TestDisplayResultsJson:
    def _make_result(self, **kwargs) -> SearchResult:
        defaults = dict(
            score=0.5,
            method=SearchMethod.Hybrid,
            source="/a.md",
            text="テキスト",
            chunk_id=0,
        )
        return SearchResult(**{**defaults, **kwargs})

    def test_output_is_valid_json(self, capsys):
        display_results_json([self._make_result()])
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert isinstance(parsed, list)
        assert len(parsed) == 1

    def test_method_is_string(self, capsys):
        display_results_json([self._make_result(method=SearchMethod.Keyword)])
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed[0]["method"] == "Keyword"

    def test_non_ascii_preserved(self, capsys):
        display_results_json([self._make_result(text="日本語テキスト")])
        out = capsys.readouterr().out
        assert "日本語テキスト" in out

    def test_empty_list(self, capsys):
        display_results_json([])
        out = capsys.readouterr().out
        assert json.loads(out) == []

    def test_score_preserved(self, capsys):
        display_results_json([self._make_result(score=0.1234)])
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed[0]["score"] == pytest.approx(0.1234)


class TestDisplayListResultsSimple:
    def test_outputs_header(self, capsys):
        display_list_results_simple([])
        out = capsys.readouterr().out
        assert "Source" in out
        assert "Name" in out

    def test_outputs_source_and_doc_name(self, capsys):
        results: list[DocListEntry] = [
            DocListEntry(source="/path/to/doc.md", doc_name="doc.md")
        ]
        display_list_results_simple(results)
        out = capsys.readouterr().out
        assert "/path/to/doc.md" in out
        assert "doc.md" in out

    def test_empty_doc_name_shows_source(self, capsys):
        results: list[DocListEntry] = [DocListEntry(source="/path/to/doc.md", doc_name="")]
        display_list_results_simple(results)
        out = capsys.readouterr().out
        assert "/path/to/doc.md" in out

    def test_multiple_rows(self, capsys):
        results: list[DocListEntry] = [
            DocListEntry(source="/a.md", doc_name="a.md"),
            DocListEntry(source="/b.md", doc_name="b.md"),
        ]
        display_list_results_simple(results)
        out = capsys.readouterr().out
        assert "/a.md" in out
        assert "/b.md" in out
