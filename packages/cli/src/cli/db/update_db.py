import logging
from datetime import date

from cli.processor.file_processor import data_generator, CHUNK_STRATEGIES
from pathlib import Path
from typing import List

from common.lance_db_manager import LanceDBManager

from common.config import settings
from common.os_utils import flatten_path_to_file

logger = logging.getLogger(__name__)


def create_chunk_fts_index(table) -> None:
    """Create FTS index on chunk_text with Japanese-optimized bigram tokenizer."""
    table.create_fts_index(
        "chunk_text",
        replace=True,
        base_tokenizer="ngram",
        ngram_min_length=2,
        ngram_max_length=2,
        lower_case=False,
        stem=False,
        remove_stop_words=False,
        ascii_folding=False,
    )


def update_files_in_db(
    path_list: List[Path],
    db_path=settings.DB_PATH,
):
    """
    Delete assigned file records and re-insert updated contents.
    """
    from cli.db.schemas import schema_names

    db = LanceDBManager(db_path).db
    doc_meta_table = db.open_table(schema_names.doc_meta)
    doc_chunk_table = db.open_table(schema_names.doc_chunk)

    # collect actual file paths
    files = list(flatten_path_to_file(path_list))
    if not files:
        logger.warning("No valid files found.")
        return

    paths_str = ", ".join([f"'{str(p)}'" for p in files])
    delete_query = f"source IN ({paths_str})"

    doc_meta_table.delete(delete_query)
    doc_chunk_table.delete(delete_query)
    logger.info(f"Deleted old records for: {paths_str}")

    # write doc_meta records (supported files only)
    today = date.today()
    meta_records = [
        {
            "source": str(f.absolute()),
            "doc_name": f.name,
            "created": today,
            "updated": today,
        }
        for f in files
        if f.suffix.lower() in CHUNK_STRATEGIES
    ]
    doc_meta_table.add(meta_records)

    # write doc_chunk records
    doc_chunk_table.add(data_generator(path_list))
    create_chunk_fts_index(doc_chunk_table)

    logger.info("Database update and FTS index optimization complete.")
