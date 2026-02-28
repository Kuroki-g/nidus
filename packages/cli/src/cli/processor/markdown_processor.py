import mistune
from pathlib import Path
from cli.processor.chunker import sections_to_chunks


def _extract_text(node):
    if "raw" in node:
        return node["raw"]
    if "children" in node:
        return "".join(_extract_text(child) for child in node["children"])
    return ""


def _get_heading_level(node) -> int:
    """mistune v3 の attrs.level または直接の level を取得"""
    attrs = node.get("attrs", {})
    return attrs.get("level", node.get("level", 1))


def _extract_sections(ast) -> list[tuple[str, str]]:
    """ASTから [(heading_text, body_text), ...] を抽出。
    heading_text は "## 見出し" 形式。見出しなしの先頭部分は ("", body)。
    """
    sections = []
    current_heading = ""
    current_body_parts: list[str] = []

    for node in ast:
        if node["type"] == "blank_line":
            continue
        if node["type"] == "heading":
            if current_body_parts:
                sections.append((current_heading, "\n\n".join(current_body_parts)))
            level = _get_heading_level(node)
            current_heading = f"{'#' * level} {_extract_text(node).strip()}"
            current_body_parts = []
        else:
            text = _extract_text(node).strip()
            if text:
                current_body_parts.append(text)

    if current_body_parts:
        sections.append((current_heading, "\n\n".join(current_body_parts)))

    return sections


def chunk_markdown(
    path: Path,
    chunk_size: int = 1000,
    overlap: int = 150,
    min_chunk: int = 200,
) -> list[str]:
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []

    parser = mistune.create_markdown(renderer=None)
    ast = parser(content)
    sections = _extract_sections(ast)
    return sections_to_chunks(sections, chunk_size, overlap, min_chunk)
