from pathlib import Path

import pyarrow as pa
from pydantic_settings import BaseSettings


class SchemaNames(BaseSettings):
    doc_meta: str = "doc_meta"
    doc_chunk: str = "doc_chunk"
    doc_full_text: str = "doc_full_text"


schema_names = SchemaNames()


def _doc_index_fields():
    return [
        pa.field("source", pa.string()),
        pa.field("doc_name", pa.string()),
    ]


def get_doc_meta_schema_fields():
    fields = [
        *_doc_index_fields(),
        pa.field("created", pa.date32()),
        pa.field("updated", pa.date32()),
    ]

    return fields


def get_doc_meta_schema():
    fields = get_doc_meta_schema_fields()
    schema = pa.schema(fields)

    return schema


def get_doc_full_text_schema_fields():
    fields = [
        *_doc_index_fields(),
        pa.field("full_text", pa.string()),
    ]

    return fields


def get_doc_full_text_schema():
    fields = get_doc_full_text_schema_fields()
    schema = pa.schema(fields)

    return schema


def get_doc_chunk_schema_fields(vector_size: int):
    fields = [
        *_doc_index_fields(),
        pa.field("vector", pa.list_(pa.float32(), vector_size)),
        pa.field("chunk_id", pa.int64()),
        pa.field("chunk_text", pa.string()),
    ]

    return fields


def get_doc_chunk_schema(vector_size: int):
    fields = get_doc_chunk_schema_fields(vector_size)
    schema = pa.schema(fields)

    return schema


def get_file_hash(file_path: Path, algorithm="sha256"):
    import hashlib

    hash_func = hashlib.new(algorithm)

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)

    return hash_func.hexdigest()
