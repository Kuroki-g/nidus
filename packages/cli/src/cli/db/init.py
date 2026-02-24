import logging
from pathlib import Path
from typing import List, Union
from cli.processor.file_processor import data_generator
from common.model import EmbeddingModelManager
from common.lance_db_manager import LanceDBManager
from common.config import settings


logger = logging.getLogger(__name__)


def init_db(
    path_list: List[Union[str, Path]],
    table_name: str = settings.TABLE_NAME,
    db_path=settings.DB_PATH,
):
    """
    Read documents from target directory.
    """

    model = EmbeddingModelManager()
    import pyarrow as pa

    db = LanceDBManager(db_path).db
    schema = pa.schema(
        [
            pa.field("vector", pa.list_(pa.float32(), model.vector_size)),
            pa.field("text", pa.string()),
            pa.field("source", pa.string()),
            pa.field("chunk_id", pa.int64()),
        ]
    )

    data = None if len(path_list) == 0 else data_generator(path_list)
    table = db.create_table(
        table_name,
        schema=schema,
        data=data,
        mode="overwrite",
    )
    table.create_fts_index("text", replace=True)
    logger.info(f"Database initialized and FTS index created for table: {table_name}")
