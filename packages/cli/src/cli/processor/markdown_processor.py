import mistune
from pathlib import Path


def extract_text(node):
    """ASTノードから再帰的にテキスト(rawキー)を抽出する"""
    # テキストノードの場合
    if "raw" in node:
        return node["raw"]

    # 子ノードを持つ場合（paragraph, heading, strong等）
    if "children" in node:
        return "".join(extract_text(child) for child in node["children"])

    return ""


def chunk_markdown(path: Path, chunk_size=500):
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []

    # renderer=None で構造解析のみ実行
    parser = mistune.create_markdown(renderer=None)
    ast = parser(content)

    chunks = []
    current_chunk = ""

    for node in ast:
        # 空行(blank_line)は無視するか、セパレータとして扱う
        if node["type"] == "blank_line":
            continue

        # ブロック単位でテキストを抽出
        block_text = extract_text(node).strip()
        if not block_text:
            continue

        # 見出し(heading)の場合は記号を復元
        if node["type"] == "heading":
            level = node.get("level", 1)
            block_text = f"{'#' * level} {block_text}"

        separator = "\n\n" if current_chunk else ""

        # 判定：現在のチャンクに足してサイズオーバーするか
        if current_chunk and (
            len(current_chunk) + len(separator) + len(block_text) > chunk_size
        ):
            chunks.append(current_chunk)
            current_chunk = block_text
        else:
            current_chunk += separator + block_text

    if current_chunk:
        chunks.append(current_chunk)

    return chunks
