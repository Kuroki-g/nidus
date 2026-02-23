from cli.processor.markdown_processor import chunk_markdown


def test_chunk_markdown_basic(tmp_path):
    test_file = tmp_path / "test.md"
    # 合計82文字（改行含む）
    content = ("A" * 40) + "\n\n" + ("B" * 40)
    test_file.write_text(content, encoding="utf-8")

    # chunk_sizeを「1つのブロック（40文字）」は入るが
    # 「2つのブロック（80文字以上）」は入らないサイズに設定
    chunk_size = 50
    chunks = chunk_markdown(test_file, chunk_size=chunk_size)

    # 検証
    assert len(chunks) == 2
    assert chunks[0] == "A" * 40
    assert chunks[1] == "B" * 40


def test_chunk_markdown_large_block_fallback(tmp_path):
    # 巨大な1ブロック（構造的に切れない）がchunk_sizeを超えた場合
    test_file = tmp_path / "large_block.md"
    content = "C" * 100
    test_file.write_text(content, encoding="utf-8")

    chunks = chunk_markdown(test_file, chunk_size=50)

    # 「構造優先」なので 1 になる
    assert len(chunks) == 1


def test_chunk_markdown_empty_file(tmp_path):
    # 空ファイルの場合
    test_file = tmp_path / "empty.md"
    test_file.write_text("", encoding="utf-8")

    chunks = chunk_markdown(test_file)

    assert chunks == []
