import logging
import re
from pathlib import Path
from pypdf import PdfReader
from pdfminer.high_level import extract_text
from cli.processor.chunker import sentence_boundary_chunker

logging.getLogger("pypdf").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)


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
