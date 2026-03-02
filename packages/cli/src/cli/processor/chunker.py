import re

SENTENCE_ENDINGS_PATTERN = re.compile(r'[。！？]+')


def sentence_boundary_chunker(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 150,
    min_chunk: int = 200,
) -> list[str]:
    """文境界を優先してテキストをチャンクに分割する。

    分割点優先順: 。！？ → \\n\\n → \\n → 強制カット
    overlap: 前チャンク末尾のoverlap文字を次チャンク先頭に追加
    min_chunk: min_chunk未満のチャンクは前チャンクに統合
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    pos = 0

    while pos < len(text):
        end = pos + chunk_size
        if end >= len(text):
            remaining = text[pos:].strip()
            if remaining:
                chunks.append(remaining)
            break

        split_at = _find_split_point(text, pos, end)
        chunk = text[pos:split_at].strip()
        if chunk:
            chunks.append(chunk)

        next_pos = split_at - overlap
        pos = next_pos if next_pos > pos else split_at

    return _merge_short_chunks(chunks, min_chunk)


def _find_split_point(text: str, start: int, end: int) -> int:
    """start〜end の範囲で最適な分割点を後ろから探す"""
    # 1. 句点・感嘆符・疑問符（最後の一致の直後）
    # pos/endpos を使って部分文字列コピーを避ける
    _last_match = None
    for _last_match in SENTENCE_ENDINGS_PATTERN.finditer(text, start, end):
        pass
    if _last_match is not None:
        return _last_match.end()

    # 2. 段落境界 \n\n
    idx = text.rfind('\n\n', start, end)
    if idx != -1:
        return idx + 2

    # 3. 行境界 \n
    idx = text.rfind('\n', start, end)
    if idx != -1:
        return idx + 1

    # 4. 強制カット
    return end


def _merge_short_chunks(chunks: list[str], min_chunk: int) -> list[str]:
    """min_chunk未満のチャンクを前のチャンクに統合"""
    if not chunks or min_chunk <= 0:
        return chunks
    result = []
    for chunk in chunks:
        if result and len(chunk) < min_chunk:
            result[-1] = result[-1] + "\n\n" + chunk
        else:
            result.append(chunk)
    return result


def sections_to_chunks(
    sections: list[tuple[str, str]],
    chunk_size: int,
    overlap: int,
    min_chunk: int,
) -> list[str]:
    """[(heading, body), ...] からチャンクリストを生成する共通ロジック。
    body が空のセクションはスキップ。heading がある場合は各チャンクにプレフィックスとして付与。
    """
    chunks = []
    for heading, body in sections:
        if not body.strip():
            continue
        body_chunks = sentence_boundary_chunker(body, chunk_size, overlap, min_chunk)
        for body_chunk in body_chunks:
            chunks.append(f"{heading}\n{body_chunk}" if heading else body_chunk)
    return chunks
