from init_scripts.processor.markdown_processor import chunk_markdown
import pytest
from pathlib import Path
# プログラムのファイル名に合わせて適宜変更してください
# from your_module import chunk_markdown 

def test_chunk_markdown_basic(tmp_path):
    # 1. テストデータの準備
    test_file = tmp_path / "test.md"
    content = "0123456789" * 10  # 合計100文字
    test_file.write_text(content, encoding="utf-8")

    # 2. 実行（50文字ずつ分割）
    chunk_size = 50
    chunks = chunk_markdown(test_file, chunk_size=chunk_size)

    # 3. 検証
    assert len(chunks) == 2
    assert chunks[0] == content[:50]
    assert chunks[1] == content[50:]

def test_chunk_markdown_short_content(tmp_path):
    # コンテンツがchunk_sizeより短い場合
    test_file = tmp_path / "short.md"
    content = "Hello World"
    test_file.write_text(content, encoding="utf-8")

    chunks = chunk_markdown(test_file, chunk_size=500)

    assert len(chunks) == 1
    assert chunks[0] == content

def test_chunk_markdown_empty_file(tmp_path):
    # 空ファイルの場合
    test_file = tmp_path / "empty.md"
    test_file.write_text("", encoding="utf-8")

    chunks = chunk_markdown(test_file)

    assert chunks == []