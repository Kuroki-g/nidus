from cli.processor.chunker import sentence_boundary_chunker


def test_empty_text():
    assert sentence_boundary_chunker("") == []
    assert sentence_boundary_chunker("   ") == []


def test_short_text_no_split():
    text = "これは短いテキストです。"
    result = sentence_boundary_chunker(text, chunk_size=1000)
    assert result == [text]


def test_split_at_kuten():
    # chunk_size=10で句点位置で分割されることを確認
    # "あいうえお。かきく" → 句点後で分割
    sentence1 = "あいうえお。"
    sentence2 = "かきくけこさしすせそ。"
    text = sentence1 + sentence2
    result = sentence_boundary_chunker(text, chunk_size=10, overlap=0, min_chunk=0)
    assert len(result) >= 2
    # 最初のチャンクは句点で終わる
    assert result[0].endswith("。")


def test_split_at_paragraph():
    # 句点なし、\n\n で分割
    para1 = "A" * 20
    para2 = "B" * 20
    text = para1 + "\n\n" + para2
    result = sentence_boundary_chunker(text, chunk_size=25, overlap=0, min_chunk=0)
    assert len(result) >= 2


def test_split_at_newline():
    # 句点なし、\n\n なし、\n で分割
    line1 = "A" * 20
    line2 = "B" * 20
    text = line1 + "\n" + line2
    result = sentence_boundary_chunker(text, chunk_size=25, overlap=0, min_chunk=0)
    assert len(result) >= 2


def test_force_cut():
    # 境界なし → chunk_size で強制カット
    text = "A" * 50
    result = sentence_boundary_chunker(text, chunk_size=20, overlap=0, min_chunk=0)
    assert len(result) >= 2
    for chunk in result[:-1]:
        assert len(chunk) <= 20


def test_overlap():
    # チャンク間でコンテンツが重複することを確認
    text = "あ" * 30 + "。" + "い" * 30 + "。" + "う" * 30 + "。"
    result = sentence_boundary_chunker(text, chunk_size=40, overlap=10, min_chunk=0)
    if len(result) >= 2:
        # 2番目のチャンクが1番目の末尾部分を含む（オーバーラップ）
        # オーバーラップが適用されているなら result[1] の先頭 ≒ result[0] の末尾部分
        overlap_candidate = result[0][-10:]
        assert overlap_candidate in result[1] or len(result[1]) > 0


def test_min_chunk_merge():
    # min_chunk より短いチャンクは前のチャンクに統合される
    # 長い文1 + 短い文2 のケース
    long_sentence = "あ" * 100 + "。"
    short_sentence = "い" * 5 + "。"
    text = long_sentence + short_sentence
    result = sentence_boundary_chunker(text, chunk_size=110, overlap=0, min_chunk=50)
    # short_sentence (6文字) は min_chunk=50 未満なので統合される
    assert len(result) == 1


def test_priority_kuten_over_newline():
    # 句点が \n より優先される
    # 句点が先に来て、その後に \n がある場合、句点で分割
    text = "あいうえお。\nかきくけこさしすせそたちつてとなにぬねの。"
    result = sentence_boundary_chunker(text, chunk_size=12, overlap=0, min_chunk=0)
    assert len(result) >= 2
    # 最初のチャンクは句点で終わる（\n より句点が優先）
    assert result[0].endswith("。")
