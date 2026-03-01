import logging

from pathlib import Path
from typing import List

from common.lance_db_manager import LanceDBManager

from common.config import settings
from common.os_utils import flatten_path_to_file

logger = logging.getLogger(__name__)


def delete_files_in_db(
    path_list: List[Path],
    db_path=settings.DB_PATH,
):
    """
    Delete assigned file records from all tables.

    Directories are expanded to their contained files. Non-existent paths
    (e.g. files already deleted from disk) are included as-is so that
    delete-on-watch events remove their DB records correctly.
    """
    from cli.db.schemas import schema_names

    db = LanceDBManager(db_path).db
    doc_meta_table = db.open_table(schema_names.doc_meta)
    doc_chunk_table = db.open_table(schema_names.doc_chunk)

    paths: list[Path] = []
    for p in path_list:
        if p.is_dir():
            paths.extend(flatten_path_to_file(p))
        else:
            paths.append(p)

    if not paths:
        logger.warning("No paths to delete.")
        return

    paths_str = ", ".join([f"'{str(p)}'" for p in paths])
    delete_query = f"source IN ({paths_str})"

    doc_meta_table.delete(delete_query)
    doc_chunk_table.delete(delete_query)
    logger.info(f"Deleted records for: {paths_str}")
