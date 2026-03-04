import pytest
from cli.processor.csv_processor import _chunk_rows, _row_to_text, chunk_csv, chunk_tsv


class TestRowToText:
    pytestmark = pytest.mark.small

    def test_basic_conversion(self):
        headers = ["名前", "年齢", "部署"]
        row = ["田中太郎", "30", "開発"]
        result = _row_to_text(headers, row)
        assert result == "名前: 田中太郎, 年齢: 30, 部署: 開発"

    def test_empty_values_skipped(self):
        headers = ["名前", "年齢", "部署"]
        row = ["田中太郎", "", "開発"]
        result = _row_to_text(headers, row)
        assert result == "名前: 田中太郎, 部署: 開発"

    def test_all_empty_returns_empty_string(self):
        headers = ["名前", "年齢"]
        row = ["", "   "]
        result = _row_to_text(headers, row)
        assert result == ""

    def test_row_shorter_than_headers(self):
        headers = ["a", "b", "c"]
        row = ["1", "2"]
        result = _row_to_text(headers, row)
        assert result == "a: 1, b: 2"

    def test_empty_header_cell_skipped(self):
        headers = ["名前", "", "部署"]
        row = ["田中", "値", "開発"]
        result = _row_to_text(headers, row)
        assert result == "名前: 田中, 部署: 開発"


class TestChunkRows:
    pytestmark = pytest.mark.small

    def test_single_chunk_when_small(self):
        row_texts = ["名前: 田中, 年齢: 30", "名前: 佐藤, 年齢: 25"]
        result = _chunk_rows(row_texts, chunk_size=1000)
        assert len(result) == 1
        assert "名前: 田中" in result[0]
        assert "名前: 佐藤" in result[0]

    def test_splits_when_exceeds_chunk_size(self):
        row_texts = ["x" * 600, "y" * 600]
        result = _chunk_rows(row_texts, chunk_size=700)
        assert len(result) == 2

    def test_empty_input_returns_empty(self):
        assert _chunk_rows([], chunk_size=1000) == []

    def test_rows_joined_by_newline(self):
        row_texts = ["row1", "row2", "row3"]
        result = _chunk_rows(row_texts, chunk_size=1000)
        assert result[0] == "row1\nrow2\nrow3"


class TestChunkCsv:
    pytestmark = pytest.mark.medium

    def test_basic_csv(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_text("名前,年齢,部署\n田中太郎,30,開発\n佐藤花子,25,デザイン", encoding="utf-8")
        result = chunk_csv(f)
        assert len(result) > 0
        assert any("名前: 田中太郎" in c for c in result)
        assert any("名前: 佐藤花子" in c for c in result)

    def test_empty_file_returns_empty(self, tmp_path):
        f = tmp_path / "empty.csv"
        f.write_text("", encoding="utf-8")
        assert chunk_csv(f) == []

    def test_header_only_returns_empty(self, tmp_path):
        f = tmp_path / "header_only.csv"
        f.write_text("名前,年齢,部署", encoding="utf-8")
        assert chunk_csv(f) == []

    def test_empty_rows_skipped(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_text("名前,年齢\n田中,30\n,,\n佐藤,25", encoding="utf-8")
        result = chunk_csv(f)
        assert len(result) > 0
        assert not any(",," in c for c in result)

    def test_many_rows_split_into_multiple_chunks(self, tmp_path):
        f = tmp_path / "big.csv"
        header = "col1,col2\n"
        rows = "\n".join([f"{'a' * 100},{'b' * 100}"] * 20)
        f.write_text(header + rows, encoding="utf-8")
        result = chunk_csv(f, chunk_size=500)
        assert len(result) > 1


class TestChunkTsv:
    pytestmark = pytest.mark.medium

    def test_basic_tsv(self, tmp_path):
        f = tmp_path / "data.tsv"
        f.write_text("名前\t年齢\n田中太郎\t30\n佐藤花子\t25", encoding="utf-8")
        result = chunk_tsv(f)
        assert len(result) > 0
        assert any("名前: 田中太郎" in c for c in result)

    def test_empty_file_returns_empty(self, tmp_path):
        f = tmp_path / "empty.tsv"
        f.write_text("", encoding="utf-8")
        assert chunk_tsv(f) == []
