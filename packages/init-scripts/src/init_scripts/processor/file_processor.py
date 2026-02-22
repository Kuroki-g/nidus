import logging
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Union


from common.model import EmbeddingModelManager
from init_scripts.processor.markdown_processor import chunk_markdown
import numpy as np
from pypdf import PdfReader

model = EmbeddingModelManager()
logger = logging.getLogger(__name__)


def get_embedding(text):
    return model.model.encode(text).astype(np.float32)


def chunk_asciidoc(path: Path, chunk_size=500):
    raise NotImplementedError()


def chunk_plain_text(path: Path, chunk_size=500):
    raise NotImplementedError()


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


CHUNK_STRATEGIES: dict[str, Callable[[Path], List[str]]] = {
    ".md": lambda path: chunk_markdown(path),
    ".adoc": lambda path: chunk_asciidoc(path),
    ".txt": lambda path: chunk_plain_text(path),
    ".pdf": lambda path: chunk_pdf(path),
}


def get_chunks(file_path: Path) -> Optional[List[str]]:
    if not file_path.is_file():
        return None

    strategy = CHUNK_STRATEGIES.get(file_path.suffix.lower())

    if not strategy:
        logger.warning(f"Unsupported file type: {file_path.suffix}")
        return None

    try:
        return strategy(file_path)
    except Exception as e:
        logger.critical(f"Error processing {file_path}: {e}")
        return None


def data_generator(
    path_list: List[Union[str, Path]], batch_size: int = 1000
) -> Iterable[List[dict]]:
    """TODO: refactoring"""
    buffer = []

    for p in path_list:
        path_obj = Path(p).resolve()
        if path_obj.is_file():
            targets = [path_obj]
        else:
            targets = (f for f in path_obj.rglob("*") if f.is_file())

        for file_path in targets:
            if file_path.is_dir():
                continue

            chunks = get_chunks(file_path)
            if not chunks:
                logger.warning(f"[Skip] No content or not supported: {file_path}")
                continue

            logger.info(f"Processing: {file_path} ({len(chunks)} chunks)")

            for i, chunk in enumerate(chunks):
                try:
                    # スキーマに合わせてデータを構築
                    vector_data = get_embedding(chunk)
                    record = {
                        "vector": vector_data,
                        "text": chunk,
                        "metadata": {
                            "source": str(file_path.absolute()),
                            "chunk_id": i,
                        },
                    }
                    buffer.append(record)

                    # 指定したバッチサイズに達したら yield
                    if len(buffer) >= batch_size:
                        yield buffer
                        buffer = []

                except Exception as e:
                    logger.critical(
                        f"[Error] Failed to process chunk {i} in {file_path}: {e}"
                    )
    if buffer:
        yield buffer
