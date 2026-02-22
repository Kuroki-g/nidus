import argparse
import logging
from pathlib import Path

from cli.processor.pdf_processor import chunk_pdf_by_pdfminer

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP Search Client")
    parser.add_argument("path", nargs="?", default="test", help="PDF path")

    args = parser.parse_args()
    pdf_path = Path(args.path).resolve()
    if pdf_path.exists():
        logger.info(f"Imported {pdf_path}")
    else:
        logger.critical(f"PDFが {pdf_path} に見当たりません")

    try:
        chunk_size = 200
        chunks = chunk_pdf_by_pdfminer(pdf_path, chunk_size=chunk_size)
        for chunk in chunks:
            logger.info(f"Chunk: {chunk}")
    except KeyboardInterrupt:
        print("\nAborted by user.")
