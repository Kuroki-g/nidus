import pytest

from cli.processor.html_processor import chunk_html

pytestmark = pytest.mark.medium


def test_empty_file(tmp_path):
    f = tmp_path / "empty.html"
    f.write_text("", encoding="utf-8")
    assert chunk_html(f) == []


def test_no_heading_short(tmp_path):
    f = tmp_path / "short.html"
    f.write_text("<p>これは短い本文です。</p>", encoding="utf-8")
    result = chunk_html(f, chunk_size=1000)
    assert len(result) == 1
    assert "これは短い本文です" in result[0]


def test_no_heading_long(tmp_path):
    f = tmp_path / "long.html"
    body = "<p>" + "あいうえお。" * 20 + "</p>" + "<p>" + "かきくけこ。" * 20 + "</p>"
    f.write_text(body, encoding="utf-8")
    result = chunk_html(f, chunk_size=100, overlap=0, min_chunk=0)
    assert len(result) >= 2
    for chunk in result:
        assert "あいうえお" in chunk or "かきくけこ" in chunk


def test_single_section_short(tmp_path):
    f = tmp_path / "section.html"
    f.write_text("<h1>見出し</h1><p>本文テキスト。</p>", encoding="utf-8")
    result = chunk_html(f, chunk_size=1000)
    assert len(result) == 1
    assert "見出し" in result[0]
    assert "本文テキスト" in result[0]


def test_single_section_long(tmp_path):
    f = tmp_path / "long_section.html"
    body = "あいうえお。" * 50
    f.write_text(f"<h1>長い見出し</h1><p>{body}</p>", encoding="utf-8")
    result = chunk_html(f, chunk_size=100, overlap=0, min_chunk=0)
    assert len(result) >= 2
    for chunk in result:
        assert chunk.startswith("長い見出し\n")


def test_multiple_sections(tmp_path):
    f = tmp_path / "multi.html"
    content = (
        "<h1>セクション1</h1><p>セクション1の本文。</p>"
        "<h2>セクション2</h2><p>セクション2の本文。</p>"
    )
    f.write_text(content, encoding="utf-8")
    result = chunk_html(f, chunk_size=1000)
    assert len(result) == 2
    assert "セクション1の本文" in result[0]
    assert "セクション2の本文" in result[1]


def test_heading_only_section(tmp_path):
    f = tmp_path / "heading_only.html"
    content = "<h1>見出しのみ</h1><h2>本文あり</h2><p>本文テキスト。</p>"
    f.write_text(content, encoding="utf-8")
    result = chunk_html(f, chunk_size=1000)
    assert len(result) == 1
    assert "本文テキスト" in result[0]


def test_script_style_ignored(tmp_path):
    f = tmp_path / "with_script.html"
    content = (
        "<h1>本文</h1>"
        "<script>alert('XSS');</script>"
        "<style>.foo { color: red; }</style>"
        "<p>本文テキスト。</p>"
    )
    f.write_text(content, encoding="utf-8")
    result = chunk_html(f, chunk_size=1000)
    assert len(result) == 1
    assert "alert" not in result[0]
    assert "color" not in result[0]
    assert "本文テキスト" in result[0]


def test_full_html_document(tmp_path):
    f = tmp_path / "full.html"
    content = """<!DOCTYPE html>
<html>
<head><title>テストページ</title></head>
<body>
  <h1>メインタイトル</h1>
  <p>最初の段落です。</p>
  <h2>サブセクション</h2>
  <p>サブセクションの内容です。</p>
</body>
</html>"""
    f.write_text(content, encoding="utf-8")
    result = chunk_html(f, chunk_size=1000)
    assert len(result) == 2
    assert "メインタイトル" in result[0]
    assert "最初の段落" in result[0]
    assert "サブセクション" in result[1]
    assert "サブセクションの内容" in result[1]


def test_heading_prefix_repeated(tmp_path):
    f = tmp_path / "long_with_heading.html"
    body = "あいうえお。" * 60
    f.write_text(f"<h2>繰り返し見出し</h2><p>{body}</p>", encoding="utf-8")
    result = chunk_html(f, chunk_size=150, overlap=0, min_chunk=0)
    assert len(result) >= 2
    for chunk in result:
        assert chunk.startswith("繰り返し見出し\n")
