import pytest
from cli.db.search_db import (
    DocListEntry,
    SearchMethod,
    SearchResult,
    _rrf_score,
    display_list_results_simple,
    display_results_simple,
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
