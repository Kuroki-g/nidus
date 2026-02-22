import argparse
from pathlib import Path
from common.model import EmbeddingModelManager
from init_scripts.file_processor import data_generator
import pyarrow as pa  # https://github.com/lancedb/lancedb/issues/2384
from typing import List, Union

from common.lance_db_manager import LanceDBManager

TABLE_NAME = "docs"
model = EmbeddingModelManager()


def init_db(
    path_list: List[Union[str, Path]],
    table_name: str = TABLE_NAME,
    db_path="./.lancedb",
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
    db.create_table(
        table_name,
        schema=schema,
        data=data_generator(path_list),
        mode="overwrite",
    )


def parse_args():
    parser = argparse.ArgumentParser(description="init database")
    parser.add_argument(
        "--doc_dir", help="document directory path(s)", nargs="+", required=True
    )

    args = parser.parse_args()
    targets = [str(Path(p).resolve()) for p in args.doc_dir]

    return targets


def main():
    (targets) = parse_args()
    if len(targets) == 0:
        print("Document list is empty.")
        return
    init_db(targets)


if __name__ == "__main__":
    main()
