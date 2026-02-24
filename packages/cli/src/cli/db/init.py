import logging
from pathlib import Path
from typing import List, Union
from cli.db.update_db import update_files_in_db
from common.lance_db_manager import LanceDBManager
from common.config import settings
from lancedb import Table


logger = logging.getLogger(__name__)


def init_model():
    logger.info("Initializing model.")
    try:
        from common.model import EmbeddingModelManager

        EmbeddingModelManager()
    except Exception as _e:
        logger.warning("failed to load model. downloading from HuggingFace.")
        from huggingface_hub import snapshot_download
        from common.model import DEFAULT_MODEL_ID

        try:
            snapshot_download(DEFAULT_MODEL_ID)
        except Exception as download_err:
            logger.error(download_err)
            logger.critical("failed to download model.")
            exit(1)


def init_db(
    path_list: List[Union[str, Path]],
):
    """
    Read documents from target directory.
    """

    (doc_table) = create_db_schemas()
    doc_table_name = settings.TABLE_NAME
    update_files_in_db(
        path_list,
    )
    doc_table.create_fts_index("text", replace=True)
    logger.info(
        f"Database initialized and FTS index created for table: {doc_table_name}"
    )


def create_db_schemas() -> Table:
    from common.model import EmbeddingModelManager

    model = EmbeddingModelManager()

    from cli.db.schemas import get_doc_schema

    schema = get_doc_schema(model.vector_size)

    db = LanceDBManager().db
    table = db.add(
        table_name=settings.TABLE_NAME,
        schema=schema,
        data=None,
        mode="overwrite",
    )

    return table
