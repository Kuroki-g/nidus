import pytest
from cli.processor.plain_text_processor import (
    _extract_asciidoc_sections,
    chunk_asciidoc,
    chunk_plain_text,
)


class TestExtractAsciidocSections:
    pytestmark = pytest.mark.small

    def test_no_headings_returns_single_section(self):
        text = "本文のみのテキスト。"
        sections = _extract_asciidoc_sections(text)
        assert sections == [("", "本文のみのテキスト。")]

    def test_single_level1_heading(self):
        text = "= タイトル\n本文です。"
        sections = _extract_asciidoc_sections(text)
        assert len(sections) == 1
        assert sections[0][0] == "= タイトル"
        assert "本文です。" in sections[0][1]

    def test_multiple_headings(self):
        text = "= 第1章\n内容1。\n== 第2節\n内容2。"
        sections = _extract_asciidoc_sections(text)
        assert len(sections) == 2
        assert sections[0][0] == "= 第1章"
        assert sections[1][0] == "== 第2節"

    def test_preamble_before_first_heading(self):
        text = "序文テキスト。\n= 見出し\n本文。"
        sections = _extract_asciidoc_sections(text)
        # preamble + heading の 2 セクション
        assert len(sections) == 2
        assert sections[0][0] == ""
        assert "序文テキスト" in sections[0][1]

    def test_heading_levels_preserved(self):
        text = "=== 3レベル見出し\n本文。"
        sections = _extract_asciidoc_sections(text)
        assert sections[0][0] == "=== 3レベル見出し"

    def test_empty_body_after_heading(self):
        text = "= 見出しのみ"
        sections = _extract_asciidoc_sections(text)
        assert len(sections) == 1
        assert sections[0][0] == "= 見出しのみ"
        assert sections[0][1] == ""

    def test_body_text_assigned_to_correct_section(self):
        text = "= 章A\n章Aの本文。\n= 章B\n章Bの本文。"
        sections = _extract_asciidoc_sections(text)
        assert "章Aの本文" in sections[0][1]
        assert "章Bの本文" in sections[1][1]

    def test_deep_heading_level(self):
        text = "====== 深い見出し\n本文。"
        sections = _extract_asciidoc_sections(text)
        assert sections[0][0] == "====== 深い見出し"


class TestChunkAsciidoc:
    pytestmark = pytest.mark.medium

    def test_basic_chunking(self, tmp_path):
        f = tmp_path / "doc.adoc"
        f.write_text(
            "= 導入\n" + "あ" * 200 + "。\n== 詳細\n" + "い" * 200 + "。",
            encoding="utf-8",
        )
        result = chunk_asciidoc(f)
        assert len(result) > 0
        assert all(isinstance(c, str) for c in result)

    def test_empty_file_returns_empty(self, tmp_path):
        f = tmp_path / "empty.adoc"
        f.write_text("", encoding="utf-8")
        result = chunk_asciidoc(f)
        assert result == []

    def test_heading_prefix_in_chunk(self, tmp_path):
        f = tmp_path / "doc.adoc"
        f.write_text("= マニュアル\n概要テキスト。", encoding="utf-8")
        result = chunk_asciidoc(f)
        assert any("= マニュアル" in c for c in result)

    def test_no_heading_file(self, tmp_path):
        f = tmp_path / "plain.adoc"
        f.write_text("見出しのないテキストです。内容が続きます。", encoding="utf-8")
        result = chunk_asciidoc(f)
        assert len(result) > 0


class TestChunkPlainText:
    pytestmark = pytest.mark.medium

    def test_basic_chunking(self, tmp_path):
        f = tmp_path / "doc.txt"
        f.write_text("あいうえお。かきくけこ。さしすせそ。", encoding="utf-8")
        result = chunk_plain_text(f)
        assert len(result) > 0
        assert all(isinstance(c, str) for c in result)

    def test_empty_file_returns_empty(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        result = chunk_plain_text(f)
        assert result == []

    def test_long_text_splits(self, tmp_path):
        f = tmp_path / "long.txt"
        f.write_text(("あ" * 100 + "。") * 20, encoding="utf-8")
        result = chunk_plain_text(f, chunk_size=500)
        assert len(result) > 1

    def test_whitespace_only_returns_empty(self, tmp_path):
        f = tmp_path / "ws.txt"
        f.write_text("   \n\n\t  ", encoding="utf-8")
        result = chunk_plain_text(f)
        assert result == []
