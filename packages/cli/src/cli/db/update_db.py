import logging

from cli.processor.file_processor import data_generator
from pathlib import Path
from typing import List

from common.lance_db_manager import LanceDBManager

from common.config import settings
from common.os_utils import flatten_path_to_file

logger = logging.getLogger(__name__)


def update_files_in_db(
    path_list: List[Path],
    table_name: str = settings.TABLE_NAME,
    db_path=settings.DB_PATH,
):
    """
    Delete assigned file and update contents.
    """
    db = LanceDBManager(db_path).db
    table = db.open_table(table_name)

    # delete target file record
    paths_str = ", ".join([f"'{str(p)}'" for p in flatten_path_to_file(path_list)])
    delete_query = f"source IN ({paths_str})"
    table.delete(delete_query)
    logger.info(f"Deleted old data for: {paths_str}")

    # add new record
    table.add(data_generator(path_list))
    table.create_fts_index("text", replace=True)

    logger.info("Database update and FTS index optimization complete.")
