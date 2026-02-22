
from pathlib import Path


def chunk_markdown(path: Path, chunk_size=500):
    content = path.read_text(encoding="utf-8")
    # NOTE: 簡易的な文字数分割
    # セクション単位などにブラッシュアップしたいところ
    chunks = [content[i : i + chunk_size] for i in range(0, len(content), chunk_size)]
    return chunks
