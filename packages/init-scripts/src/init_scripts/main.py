import argparse
import os
from pathlib import Path
import numpy as np
import pyarrow as pa  # https://github.com/lancedb/lancedb/issues/2384
from typing import Iterable, List, Optional, Union
from sentence_transformers import SentenceTransformer

import lancedb

# Offline not to access hagging face by mistake
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

# https://huggingface.co/hotchpotch/static-embedding-japanese
model_name = "hotchpotch/static-embedding-japanese"
model = SentenceTransformer(model_name, local_files_only=True)
MODEL_VECTOR_SIZE = 1024

TABLE_NAME = "docs"

def get_embedding(text):
    return model.encode(text).astype(np.float32)


def load_and_chunk_md(file_path: Path, chunk_size=500):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # NOTE: 簡易的な文字数分割
    # セクション単位などにブラッシュアップしたいところ
    chunks = [content[i : i + chunk_size] for i in range(0, len(content), chunk_size)]
    return chunks


def get_chunk(file_path: Path) -> Optional[List[str]]:
    if not file_path.is_file():
        return None
    if file_path.suffix == ".md":
        return load_and_chunk_md(file_path)
    else:
        print("TODO: implement pdf, txt parse")
        return None

def data_generator(
    path_list: List[Union[str, Path]], batch_size: int = 1000
) -> Iterable[List[dict]]:
    """TODO: refactoring"""
    buffer = []

    for p in path_list:
        path_obj = Path(p)
        targets = path_obj.rglob("*") if path_obj.is_dir() else [path_obj]

        for file_path in targets:
            chunks = get_chunk(file_path)
            if not chunks:
                print(f"[Skip] No content or not supported: {file_path}")
                continue

            print(f"Processing: {file_path} ({len(chunks)} chunks)")

            for i, chunk in enumerate(chunks):
                try:
                    # スキーマに合わせてデータを構築
                    vector_data = get_embedding(chunk)
                    record = {
                        "vector": vector_data,
                        "text": chunk,
                        "metadata": {
                            "source": str(file_path.absolute()),
                            "chunk_id": i
                        }
                    }
                    buffer.append(record)

                    # 指定したバッチサイズに達したら yield
                    if len(buffer) >= batch_size:
                        yield buffer
                        buffer = []

                except Exception as e:
                    print(f"[Error] Failed to process chunk {i} in {file_path}: {e}")
    if buffer:
        yield buffer


def init_db(
    path_list: List[Union[str, Path]], table_name: str = TABLE_NAME, db_path="./.lancedb"
):
    """
    Read documents from target directory.
    """
    db = lancedb.connect(db_path)
    schema = pa.schema([
        pa.field("vector", pa.list_(pa.float32(), MODEL_VECTOR_SIZE)),
        pa.field("text", pa.string()),
        pa.field("metadata", pa.struct([
            pa.field("source", pa.string()),
            pa.field("chunk_id", pa.int64()),
        ]))
    ])
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
    init_db(targets)


if __name__ == "__main__":
    main()
