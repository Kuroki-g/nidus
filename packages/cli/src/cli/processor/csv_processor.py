import csv
from pathlib import Path


def _row_to_text(headers: list[str], row: list[str]) -> str:
    parts = [f"{h}: {v}" for h, v in zip(headers, row, strict=False) if h.strip() and v.strip()]
    return ", ".join(parts)


def _chunk_rows(row_texts: list[str], chunk_size: int) -> list[str]:
    chunks = []
    current_lines: list[str] = []
    current_len = 0

    for text in row_texts:
        added_len = len(text) + (1 if current_lines else 0)  # +1 for "\n"
        if current_lines and current_len + added_len > chunk_size:
            chunks.append("\n".join(current_lines))
            current_lines = [text]
            current_len = len(text)
        else:
            current_lines.append(text)
            current_len += added_len

    if current_lines:
        chunks.append("\n".join(current_lines))

    return chunks


def chunk_csv(path: Path, chunk_size: int = 1000) -> list[str]:
    return _chunk_delimited(path, delimiter=",", chunk_size=chunk_size)


def chunk_tsv(path: Path, chunk_size: int = 1000) -> list[str]:
    return _chunk_delimited(path, delimiter="\t", chunk_size=chunk_size)


def _chunk_delimited(path: Path, delimiter: str, chunk_size: int) -> list[str]:
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []

    reader = csv.reader(content.splitlines(), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        return []

    headers = rows[0]
    if not headers:
        return []

    row_texts = [
        _row_to_text(headers, row)
        for row in rows[1:]
        if any(v.strip() for v in row)
    ]
    if not row_texts:
        return []

    return _chunk_rows(row_texts, chunk_size)
