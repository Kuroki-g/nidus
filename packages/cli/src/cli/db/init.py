import logging
from pathlib import Path
from typing import List, Union
from cli.processor.file_processor import data_generator
from common.model import EmbeddingModelManager
from common.lance_db_manager import LanceDBManager
from common.config import settings


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
    table_name: str = settings.TABLE_NAME,
    db_path=settings.DB_PATH,
):
    """
    Read documents from target directory.
    """

    model = EmbeddingModelManager()

    db = LanceDBManager(db_path).db
    from cli.db.schemas import get_doc_schema

    schema = get_doc_schema(model.vector_size)
    data = None if len(path_list) == 0 else data_generator(path_list)
    table = db.create_table(
        table_name,
        schema=schema,
        data=data,
        mode="overwrite",
    )
    table.create_fts_index("text", replace=True)
    logger.info(f"Database initialized and FTS index created for table: {table_name}")
