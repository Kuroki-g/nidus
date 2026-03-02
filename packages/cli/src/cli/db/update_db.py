import logging
from datetime import date
from pathlib import Path

from cli.processor.file_processor import CHUNK_STRATEGIES, data_generator
from common.config import settings
from common.lance_db_manager import LanceDBManager
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


def _get_existing_meta(doc_meta_table, files: list[Path]) -> dict[str, dict]:
    """Return {source: {created, file_hash}} for files already in doc_meta."""
    if not files:
        return {}

    paths_str = ", ".join([f"'{p!s}'" for p in files])
    try:
        rows = (
            doc_meta_table.search()
            .where(f"source IN ({paths_str})", prefilter=True)
            .select(["source", "created", "file_hash"])
            .to_list()
        )
    except Exception as e:
        logger.warning(f"Could not query existing metadata (treating all as new): {e}")
        return {}

    return {r["source"]: {"created": r["created"], "file_hash": r["file_hash"]} for r in rows}


def update_files_in_db(
    path_list: list[Path],
    db_path=settings.DB_PATH,
) -> None:
    """
    Re-index only files whose content has changed (hash-based incremental update).
    Unchanged files are skipped. The original `created` date is preserved on update.
    """
    from cli.db.schemas import get_file_hash, schema_names

    db = LanceDBManager(db_path).db
    doc_meta_table = db.open_table(schema_names.doc_meta)
    doc_chunk_table = db.open_table(schema_names.doc_chunk)

    files = [
        f
        for f in flatten_path_to_file(path_list)
        if f.suffix.lower() in CHUNK_STRATEGIES
    ]
    if not files:
        logger.warning("No valid files found.")
        return

    existing = _get_existing_meta(doc_meta_table, files)

    # Classify files and cache hashes to avoid reading each file twice
    changed: list[tuple[Path, str, dict | None]] = []  # (path, hash, stored_meta)
    skipped = 0
    for f in files:
        current_hash = get_file_hash(f)
        stored = existing.get(str(f))
        if stored and stored["file_hash"] == current_hash:
            skipped += 1
        else:
            changed.append((f, current_hash, stored))

    if skipped:
        logger.info(f"Skipped {skipped} unchanged file(s).")
    if not changed:
        logger.info("All files are up to date. Nothing to do.")
        return

    changed_paths = [f for f, _, _ in changed]

    # Delete old records for changed files only
    paths_str = ", ".join([f"'{p!s}'" for p in changed_paths])
    delete_query = f"source IN ({paths_str})"
    doc_meta_table.delete(delete_query)
    doc_chunk_table.delete(delete_query)
    logger.info(f"Re-indexing {len(changed)} changed file(s).")

    today = date.today()
    meta_records = [
        {
            "source": str(f),
            "doc_name": f.name,
            "created": stored["created"] if stored else today,
            "updated": today,
            "file_hash": current_hash,
        }
        for f, current_hash, stored in changed
    ]
    doc_meta_table.add(meta_records)

    doc_chunk_table.add(data_generator(changed_paths))
    create_chunk_fts_index(doc_chunk_table)

    logger.info("Database update and FTS index optimization complete.")
