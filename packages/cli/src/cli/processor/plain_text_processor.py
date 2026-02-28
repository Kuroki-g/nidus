import re
from pathlib import Path
from cli.processor.chunker import sentence_boundary_chunker, sections_to_chunks

ADOC_HEADING_PATTERN = re.compile(r'^(={1,6})\s+(.+)$', re.MULTILINE)


def _extract_asciidoc_sections(text: str) -> list[tuple[str, str]]:
    matches = list(ADOC_HEADING_PATTERN.finditer(text))
    if not matches:
        return [("", text)]

    sections = []
    if matches[0].start() > 0:
        preamble = text[:matches[0].start()].strip()
        if preamble:
            sections.append(("", preamble))

    for i, match in enumerate(matches):
        heading = f"{'=' * len(match.group(1))} {match.group(2).strip()}"
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        sections.append((heading, body))

    return sections


def chunk_asciidoc(
    path: Path,
    chunk_size: int = 1000,
    overlap: int = 150,
    min_chunk: int = 200,
) -> list[str]:
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []

    sections = _extract_asciidoc_sections(content)
    return sections_to_chunks(sections, chunk_size, overlap, min_chunk)


def chunk_plain_text(
    path: Path,
    chunk_size: int = 1000,
    overlap: int = 150,
    min_chunk: int = 200,
) -> list[str]:
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []
    return sentence_boundary_chunker(content, chunk_size, overlap, min_chunk)
