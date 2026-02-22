from pathlib import Path

from pathlib import Path
from pdfminer.high_level import extract_text

def chunk_pdf_by_pdfminer(path: Path, chunk_size=500):
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    full_text = extract_text(str(path))

    # あとは元のロジックと同じ
    cleaned_text = " ".join(full_text.split())

    chunks = [
        cleaned_text[i : i + chunk_size]
        for i in range(0, len(cleaned_text), chunk_size)
    ]

    return chunks
