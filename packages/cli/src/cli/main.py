import logging
from pathlib import Path
import click
from common.logger_setup import setup_logging
from common.model import EmbeddingModelManager
from common.config import settings
from cli.processor.file_processor import data_generator
import pyarrow as pa  # https://github.com/lancedb/lancedb/issues/2384
from typing import List, Union

from common.lance_db_manager import LanceDBManager

model = EmbeddingModelManager()


def init_db(
    path_list: List[Union[str, Path]],
    table_name: str = settings.TABLE_NAME,
    db_path=settings.DB_PATH,
):
    """
    Read documents from target directory.
    """
    db = LanceDBManager(db_path).db
    schema = pa.schema(
        [
            pa.field("vector", pa.list_(pa.float32(), model.vector_size)),
            pa.field("text", pa.string()),
            pa.field(
                "metadata",
                pa.struct(
                    [
                        pa.field("source", pa.string()),
                        pa.field("chunk_id", pa.int64()),
                    ]
                ),
            ),
        ]
    )

    table = db.create_table(
        table_name,
        schema=schema,
        data=data_generator(path_list),
        mode="overwrite",
    )
    table.create_fts_index("text", replace=True)
    logger.info(f"Database initialized and FTS index created for table: {table_name}")


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
    paths_str = ", ".join([f"'{str(p)}'" for p in path_list])
    delete_query = f"metadata.source IN ({paths_str})"
    table.delete(delete_query)
    logger.info(f"Deleted old data for: {paths_str}")

    # add new record
    table.add(data_generator(path_list))
    table.create_fts_index("text", replace=True)

    logger.info("Database update and FTS index optimization complete.")


setup_logging(level="INFO")
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Nidus CLI - Document MCP server CLI"""
    pass


@cli.command()
@click.option(
    "--doc_dir",
    help="document directory path(s)",
    multiple=True,
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
def init(doc_dir):
    """init database"""
    targets = [str(Path(p).resolve()) for p in doc_dir]
    if len(targets) == 0:
        logger.warning("Document list is empty.")
        return

    init_db(targets)


@cli.command()
@click.option(
    "--file",
    "-f",
    help="update file(s)",
    multiple=True,
    required=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
)
def update(file):
    """init database"""
    file_paths = [Path(f).resolve() for f in file]
    valid_paths = [p for p in file_paths if p.exists()]
    if not valid_paths:
        logger.warning("No valid files found to update.")
        return

    update_files_in_db(valid_paths)


def main():
    cli()


if __name__ == "__main__":
    main()
