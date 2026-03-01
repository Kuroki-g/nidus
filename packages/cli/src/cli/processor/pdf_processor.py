import logging
import re
from pathlib import Path
from pypdf import PdfReader
from pdfminer.high_level import extract_text
from cli.processor.chunker import sentence_boundary_chunker

logging.getLogger("pypdf").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)


def _needs_pdfminer(path: Path) -> bool:
    """
    pypdf で文字化けが確定しているフォント構成かどうかを事前に判定する。

    判定条件: 少なくとも1つのページが Type0 + Identity-H + ToUnicode なし のフォントを持つ

    背景:
      Type0 フォント（複合フォント）は CID という独自の文字 ID 体系を使う。
      Identity-H はその CID を 2 バイト big-endian のまま PDF ストリームに格納する
      エンコーディングで、Unicode コードポイントとは異なる値になる。
      ToUnicode テーブルがあれば CID → Unicode の変換ができるが、
      日本語 PDF の一部（特に古い組版ソフト由来）はこのテーブルを省略している。

      pypdf は ToUnicode がない場合、CID バイト列を UTF-16-BE として
      そのままデコードしてしまう（_cmap.py の _parse_to_unicode 参照）。
      CID 値 ≠ Unicode コードポイントなので結果は必ず文字化けする。

      一方 pdfminer は Adobe-Japan1 等の CID 体系ごとの変換テーブルを
      内部に持っており、ToUnicode なしでも正しくデコードできる。
    """
    try:
        reader = PdfReader(path)
        for page in reader.pages:
            if "/Resources" not in page:
                continue
            fonts = page["/Resources"].get("/Font", {})
            for font_ref in fonts.values():
                font = font_ref.get_object()
                if (
                    font.get("/Subtype") == "/Type0"
                    and font.get("/Encoding") == "/Identity-H"
                    and font.get("/ToUnicode") is None
                ):
                    return True
    except Exception:
        pass
    return False


def chunk_pdf(
    path: Path,
    chunk_size: int = 1000,
    overlap: int = 150,
    min_chunk: int = 200,
) -> list[str]:
    """
    Get chunk from PDF.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # フォント構成を事前確認し、pypdf で文字化けする場合は pdfminer に直行する
    if _needs_pdfminer(path):
        logger.debug(
            f"{path.name}: Type0/Identity-H font without ToUnicode detected, using pdfminer directly."
        )
        return chunk_pdf_by_pdfminer(path, chunk_size, overlap, min_chunk)

    chunks = chunk_pdf_by_pypdf(path, chunk_size, overlap, min_chunk)

    if not chunks:
        logger.warning(
            f"pypdf returned no text for {path.name}. Falling back to pdfminer..."
        )
        chunks = chunk_pdf_by_pdfminer(path, chunk_size, overlap, min_chunk)

    return chunks


def _text_to_chunks(
    text: str,
    chunk_size: int,
    overlap: int,
    min_chunk: int,
) -> list[str]:
    """Process extracted text from PDF"""
    if not text or not text.strip():
        return []

    # PDF特有の前処理: 複数の空白を1つに正規化（改行は保持）
    cleaned_text = re.sub(r'[ \t]+', ' ', text).strip()

    return sentence_boundary_chunker(cleaned_text, chunk_size, overlap, min_chunk)


def chunk_pdf_by_pypdf(
    path: Path,
    chunk_size: int = 1000,
    overlap: int = 150,
    min_chunk: int = 200,
) -> list[str]:
    """Extract text by PyPDF"""
    try:
        reader = PdfReader(path)
        texts = []
        for page in reader.pages:
            content = page.extract_text()
            if content:
                texts.append(content)

        return _text_to_chunks("\n".join(texts), chunk_size, overlap, min_chunk)
    except Exception as e:
        logger.debug(f"pypdf error: {e}")
        return []


def chunk_pdf_by_pdfminer(
    path: Path,
    chunk_size: int = 1000,
    overlap: int = 150,
    min_chunk: int = 200,
) -> list[str]:
    """Extract text by pdfminer"""
    try:
        full_text = extract_text(path)
        return _text_to_chunks(full_text, chunk_size, overlap, min_chunk)
    except Exception as e:
        logger.error(f"pdfminer also failed for {path.name}: {e}")
        return []
