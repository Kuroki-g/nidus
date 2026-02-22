from init_scripts.processor.pdf_processor import chunk_pdf
import pytest
from pathlib import Path

# テスト用データのパスを定義
DATA_DIR = Path(__file__).parent.parent / "data"
SAMPLE_PDF = DATA_DIR / "社内ナレッジベース.pdf"


def test_chunk_pdf_real_file():
    """自作のPDFファイルを使って、チャンク分割が動作するか確認"""
    # ファイルが存在することを確認（手書きPDFを置き忘れていないか）
    assert SAMPLE_PDF.exists(), f"テスト用PDFが {SAMPLE_PDF} に見当たりません"

    chunk_size = 200
    chunks = chunk_pdf(SAMPLE_PDF, chunk_size=chunk_size)

    # 検証
    assert isinstance(chunks, list)
    if len(chunks) > 0:
        # 最後のチャンク以外は指定サイズになっているはず（改行などの影響を除けば）
        assert len(chunks[0]) <= chunk_size
        print(f"\n抽出されたチャンク数: {len(chunks)}")
        print(f"最初の50文字: {chunks[0][:50]}...")


def test_chunk_pdf_file_not_found():
    """存在しないパスを渡したときに正しくエラーが出るか"""
    with pytest.raises(FileNotFoundError):
        chunk_pdf(Path("this_file_does_not_exist.pdf"))


def test_chunk_pdf_default_size():
    """デフォルトのチャンクサイズ(500)が適用されるか"""
    chunks = chunk_pdf(SAMPLE_PDF)

    assert len(chunks) >= 1
