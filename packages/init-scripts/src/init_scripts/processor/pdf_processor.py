from pathlib import Path

from pypdf import PdfReader


def chunk_pdf(path: Path, chunk_size=500):
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    reader = PdfReader(path)
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"

    cleaned_text = " ".join(full_text.split())

    chunks = [
        cleaned_text[i : i + chunk_size]
        for i in range(0, len(cleaned_text), chunk_size)
    ]

    return chunks
