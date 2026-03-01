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

    create_db_schemas()
    update_files_in_db(path_list)
    logger.info("Database initialized and FTS index created for doc_chunk table.")


def create_db_schemas(db_uri: str = settings.DB_PATH) -> tuple[Table, Table]:
    from common.model import EmbeddingModelManager

    db = LanceDBManager(db_uri).db

    model = EmbeddingModelManager()

    from cli.db.schemas import (
        schema_names,
        get_doc_meta_schema,
        get_doc_chunk_schema,
    )

    doc_meta_table = db.create_table(
        name=schema_names.doc_meta,
        schema=get_doc_meta_schema(),
        data=None,
        mode="overwrite",
    )
    doc_chunk_table = db.create_table(
        name=schema_names.doc_chunk,
        schema=get_doc_chunk_schema(model.vector_size),
        data=None,
        mode="overwrite",
    )

    return doc_meta_table, doc_chunk_table
