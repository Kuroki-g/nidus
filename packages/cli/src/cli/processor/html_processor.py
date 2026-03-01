import re
from html.parser import HTMLParser
from pathlib import Path

from cli.processor.chunker import sections_to_chunks

_SKIP_TAGS = frozenset({"script", "style", "noscript", "iframe", "svg", "head"})
_HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
_BLOCK_TAGS = frozenset({
    "p", "div", "li", "td", "th", "dt", "dd",
    "blockquote", "pre", "section", "article", "main",
    "nav", "footer", "header", "aside",
})


def _normalize_whitespace(text: str) -> str:
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class _HTMLSectionExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._sections: list[tuple[str, str]] = []
        self._current_heading: str = ""
        self._current_body: str = ""
        self._skip_depth: int = 0
        self._in_heading: bool = False
        self._heading_buf: str = ""

    def handle_starttag(self, tag: str, attrs):
        if self._skip_depth > 0:
            if tag in _SKIP_TAGS:
                self._skip_depth += 1
            return
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if tag in _HEADING_TAGS:
            body = _normalize_whitespace(self._current_body)
            if body:
                self._sections.append((self._current_heading, body))
            self._current_heading = ""
            self._current_body = ""
            self._in_heading = True
            self._heading_buf = ""
        elif tag in _BLOCK_TAGS:
            self._current_body += "\n"

    def handle_endtag(self, tag: str):
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag in _HEADING_TAGS and self._in_heading:
            self._current_heading = _normalize_whitespace(self._heading_buf)
            self._in_heading = False
        elif tag in _BLOCK_TAGS:
            self._current_body += "\n"

    def handle_data(self, data: str):
        if self._skip_depth > 0:
            return
        if self._in_heading:
            self._heading_buf += data
        else:
            self._current_body += data

    def get_sections(self) -> list[tuple[str, str]]:
        body = _normalize_whitespace(self._current_body)
        if body:
            self._sections.append((self._current_heading, body))
        return self._sections


def _extract_html_sections(content: str) -> list[tuple[str, str]]:
    extractor = _HTMLSectionExtractor()
    extractor.feed(content)
    return extractor.get_sections()


def chunk_html(
    path: Path,
    chunk_size: int = 1000,
    overlap: int = 150,
    min_chunk: int = 200,
) -> list[str]:
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []

    sections = _extract_html_sections(content)
    if not sections:
        return []

    return sections_to_chunks(sections, chunk_size, overlap, min_chunk)
