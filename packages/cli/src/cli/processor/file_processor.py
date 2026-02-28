from concurrent.futures import ProcessPoolExecutor
import logging
import multiprocessing
import os
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Union
import numpy as np
from common.model import EmbeddingModelManager
from cli.processor.markdown_processor import chunk_markdown
from cli.processor.pdf_processor import chunk_pdf


model = EmbeddingModelManager()
logger = logging.getLogger(__name__)
logging.getLogger("pdfminer").setLevel(logging.ERROR)


def get_embedding(text):
    return model.model.encode(
        text, show_progress_bar=False, convert_to_numpy=True
    ).astype(np.float32)


def chunk_asciidoc(path: Path, chunk_size=500):
    raise NotImplementedError()


def chunk_plain_text(path: Path, chunk_size=500):
    raise NotImplementedError()


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
    path_list: List[Union[str, Path]], batch_size: int = 64
) -> Iterable[List[dict]]:
    """TODO: refactoring"""
    from common.os_utils import flatten_path_to_file

    buffer = []

    for p in path_list:
        targets = flatten_path_to_file(p)

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
                        "chunk_text": chunk,
                        "source": str(file_path.absolute()),
                        "doc_name": file_path.name,
                        "chunk_id": i,
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


def data_generator_multiprocessing(
    path_list: List[Union[str, Path]], batch_size: int = 64
) -> Iterable[List[dict]]:
    """
    NOTE: 実装をしてみたはものの早くならないので未使用
    """
    all_files = []
    for p in path_list:
        path_obj = Path(p).resolve()
        targets = [path_obj] if path_obj.is_file() else path_obj.rglob("*")
        all_files.extend(
            [f for f in targets if f.is_file() and f.suffix.lower() in CHUNK_STRATEGIES]
        )

    pending_items = []
    max_workers = min(os.cpu_count(), len(all_files)) if all_files else 1
    ctx = multiprocessing.get_context("spawn")

    with ProcessPoolExecutor(max_workers=max_workers, mp_context=ctx) as executor:
        for file_path, chunks in zip(all_files, executor.map(get_chunks, all_files)):
            if not chunks:
                continue

            logger.info(f"Parsed: {file_path} ({len(chunks)} chunks)")

            for i, chunk in enumerate(chunks):
                pending_items.append(
                    {"text": chunk, "source": str(file_path.absolute()), "chunk_id": i}
                )

                if len(pending_items) >= batch_size:
                    yield _flush_batch(pending_items)
                    pending_items = []

    if pending_items:
        yield _flush_batch(pending_items)


def _flush_batch(items: List[dict]) -> List[dict]:
    """溜まったアイテムをまとめてベクトル化する"""
    texts = [item["text"] for item in items]
    vectors = model.model.encode(
        texts, show_progress_bar=False, convert_to_numpy=True
    ).astype(np.float32)

    records = []
    for item, vector in zip(items, vectors):
        records.append(
            {
                "vector": vector,
                "text": item["text"],
                "source": item["source"],
                "chunk_id": item["chunk_id"],
            }
        )
    return records
