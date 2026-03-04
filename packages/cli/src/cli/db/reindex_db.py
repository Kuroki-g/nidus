import logging
from pathlib import Path

from common.config import settings
from common.lance_db_manager import LanceDBManager

logger = logging.getLogger(__name__)


def get_all_sources(db_path: str | Path = settings.DB_PATH) -> list[str]:
    """Return all source paths registered in doc_meta."""
    from cli.db.schemas import schema_names

    db = LanceDBManager(db_path).db
    try:
        table = db.open_table(schema_names.doc_meta)
        rows = table.search().select(["source"]).to_list()
        return [r["source"] for r in rows]
    except Exception as e:
        logger.warning(f"Could not read doc_meta: {e}")
        return []


def reindex_all_in_db(
    dry_run: bool = False,
    db_path: str | Path = settings.DB_PATH,
) -> None:
    """Re-index all registered documents, bypassing hash-based skip logic.

    Deletes all records from both tables, then re-processes every source
    that still exists on disk. Files that no longer exist are logged and
    skipped.
    """
    from cli.db.schemas import schema_names
    from cli.db.update_db import update_files_in_db

    sources = get_all_sources(db_path)
    if not sources:
        logger.info("No documents registered. Nothing to reindex.")
        return

    existing_files: list[Path] = []
    missing: list[str] = []
    for s in sources:
        p = Path(s)
        if p.exists():
            existing_files.append(p)
        else:
            missing.append(s)

    for m in missing:
        logger.warning(f"File not found (skipping): {m}")

    if dry_run:
        print(f"Would reindex {len(existing_files)} file(s):")
        for f in existing_files:
            print(f"  {f}")
        if missing:
            print(f"\nMissing ({len(missing)} file(s) would be skipped):")
            for m in missing:
                print(f"  {m}")
        return

    if not existing_files:
        logger.warning("No existing files to reindex.")
        return

    db = LanceDBManager(db_path).db
    doc_meta_table = db.open_table(schema_names.doc_meta)
    doc_chunk_table = db.open_table(schema_names.doc_chunk)
    doc_meta_table.delete("1 = 1")
    doc_chunk_table.delete("1 = 1")
    logger.info(f"Cleared all records. Re-indexing {len(existing_files)} file(s).")

    update_files_in_db(existing_files, db_path=db_path)
