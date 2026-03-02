import pytest
from cli.processor.markdown_processor import chunk_markdown

pytestmark = pytest.mark.medium


def test_empty_file(tmp_path):
    f = tmp_path / "empty.md"
    f.write_text("", encoding="utf-8")
    assert chunk_markdown(f) == []


def test_no_heading_short(tmp_path):
    f = tmp_path / "short.md"
    text = "これは短い本文です。"
    f.write_text(text, encoding="utf-8")
    result = chunk_markdown(f, chunk_size=1000)
    assert result == [text]


def test_no_heading_long(tmp_path):
    f = tmp_path / "long.md"
    # 句点区切りの長いテキスト（見出しなし）
    text = ("あいうえお。" * 20) + ("かきくけこ。" * 20)
    f.write_text(text, encoding="utf-8")
    result = chunk_markdown(f, chunk_size=100, overlap=0, min_chunk=0)
    assert len(result) >= 2
    # 見出しプレフィックスはない
    for chunk in result:
        assert not chunk.startswith("#")


def test_single_section_short(tmp_path):
    f = tmp_path / "section.md"
    f.write_text("# 見出し\n\n本文テキスト。", encoding="utf-8")
    result = chunk_markdown(f, chunk_size=1000)
    assert len(result) == 1
    assert result[0].startswith("# 見出し")
    assert "本文テキスト" in result[0]


def test_single_section_long(tmp_path):
    f = tmp_path / "long_section.md"
    body = "あいうえお。" * 50
    f.write_text(f"# 長い見出し\n\n{body}", encoding="utf-8")
    result = chunk_markdown(f, chunk_size=100, overlap=0, min_chunk=0)
    assert len(result) >= 2
    # 全チャンクに見出しプレフィックスが付く
    for chunk in result:
        assert chunk.startswith("# 長い見出し\n")


def test_multiple_sections(tmp_path):
    f = tmp_path / "multi.md"
    content = "# セクション1\n\nセクション1の本文。\n\n## セクション2\n\nセクション2の本文。"
    f.write_text(content, encoding="utf-8")
    result = chunk_markdown(f, chunk_size=1000)
    assert len(result) == 2
    assert "セクション1の本文" in result[0]
    assert "セクション2の本文" in result[1]


def test_heading_only_section(tmp_path):
    f = tmp_path / "heading_only.md"
    # 本文なしの見出しはスキップされる
    content = "# 見出しのみ\n\n## 本文あり\n\n本文テキスト。"
    f.write_text(content, encoding="utf-8")
    result = chunk_markdown(f, chunk_size=1000)
    assert len(result) == 1
    assert "本文テキスト" in result[0]
    # 本文なし見出し単体はチャンクにならない
    assert not any(c.strip() == "# 見出しのみ" for c in result)


def test_heading_prefix_repeated(tmp_path):
    f = tmp_path / "long_with_heading.md"
    body = "あいうえお。" * 60
    f.write_text(f"## 繰り返し見出し\n\n{body}", encoding="utf-8")
    result = chunk_markdown(f, chunk_size=150, overlap=0, min_chunk=0)
    assert len(result) >= 2
    for chunk in result:
        assert chunk.startswith("## 繰り返し見出し\n")
