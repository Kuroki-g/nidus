import logging
from pathlib import Path
from pypdf import PdfReader
from pdfminer.high_level import extract_text

logging.getLogger("pypdf").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)


def chunk_pdf(path: Path, chunk_size: int = 500) -> list[str]:
    """
    Get chunk from PDF.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    chunks = chunk_pdf_by_pypdf(path, chunk_size)

    if not chunks:
        logger.warning(
            f"pypdf returned no text for {path.name}. Falling back to pdfminer..."
        )
        chunks = chunk_pdf_by_pdfminer(path, chunk_size)

    return chunks


def _text_to_chunks(text: str, chunk_size: int) -> list[str]:
    """Process extracted text from PDF"""
    if not text or not text.strip():
        return []

    cleaned_text = " ".join(text.split())

    return [
        cleaned_text[i : i + chunk_size]
        for i in range(0, len(cleaned_text), chunk_size)
    ]


def chunk_pdf_by_pypdf(path: Path, chunk_size: int = 500) -> list[str]:
    """Extract text by PyPDF"""
    try:
        reader = PdfReader(path)
        texts = []
        for page in reader.pages:
            content = page.extract_text()
            if content:
                texts.append(content)

        return _text_to_chunks("\n".join(texts), chunk_size)
    except Exception as e:
        logger.debug(f"pypdf error: {e}")
        return []


def chunk_pdf_by_pdfminer(path: Path, chunk_size: int = 500) -> list[str]:
    """Extract text by pdfminer"""
    try:
        full_text = extract_text(path)
        return _text_to_chunks(full_text, chunk_size)
    except Exception as e:
        logger.error(f"pdfminer also failed for {path.name}: {e}")
        return []
