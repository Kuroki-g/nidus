from pathlib import Path

import mammoth
from cli.processor.markdown_processor import chunk_markdown_text


def chunk_docx(
    path: Path,
    chunk_size: int = 1000,
    overlap: int = 150,
    min_chunk: int = 200,
) -> list[str]:
    with path.open("rb") as f:
        result = mammoth.convert_to_markdown(f)
    content = result.value.strip()
    if not content:
        return []
    return chunk_markdown_text(content, chunk_size, overlap, min_chunk)
