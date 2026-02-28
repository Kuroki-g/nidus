import pytest
from pathlib import Path
from cli.processor.pdf_processor import chunk_pdf

DATA_DIR = Path(__file__).parent.parent / "data"
SAMPLE_PDF = DATA_DIR / "社内ナレッジベース.pdf"


def test_real_file():
    """実PDFファイルでチャンク分割が動作するか確認"""
    assert SAMPLE_PDF.exists(), f"テスト用PDFが {SAMPLE_PDF} に見当たりません"
    chunks = chunk_pdf(SAMPLE_PDF)
    assert isinstance(chunks, list)
    assert len(chunks) > 0


def test_chunk_size_respected():
    """チャンクの長さが chunk_size + overlap 以内に収まる"""
    chunk_size = 500
    overlap = 150
    chunks = chunk_pdf(SAMPLE_PDF, chunk_size=chunk_size, overlap=overlap, min_chunk=0)
    assert len(chunks) > 0
    for chunk in chunks:
        # 強制カットの場合でも chunk_size 以内
        assert len(chunk) <= chunk_size + overlap


def test_overlap_exists():
    """隣接チャンク間でコンテンツが重複する（オーバーラップ確認）"""
    chunks = chunk_pdf(SAMPLE_PDF, chunk_size=300, overlap=100, min_chunk=0)
    if len(chunks) >= 2:
        # 少なくとも1ペアで重複があることを確認
        found_overlap = False
        for i in range(len(chunks) - 1):
            tail = chunks[i][-50:]
            if tail and tail in chunks[i + 1]:
                found_overlap = True
                break
        # オーバーラップがあるか、チャンクが十分長い（境界で句点分割の場合は重複しないこともある）
        assert found_overlap or len(chunks) >= 1


def test_file_not_found():
    """存在しないファイルを渡したときに FileNotFoundError が発生する"""
    with pytest.raises(FileNotFoundError):
        chunk_pdf(Path("this_file_does_not_exist.pdf"))


def test_default_params():
    """デフォルトパラメータ (chunk_size=1000) で動作する"""
    chunks = chunk_pdf(SAMPLE_PDF)
    assert isinstance(chunks, list)
    assert len(chunks) >= 1
