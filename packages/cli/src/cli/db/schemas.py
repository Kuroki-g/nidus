import pyarrow as pa


def get_doc_schema(vector_size: int):
    fields = [
        pa.field("vector", pa.list_(pa.float32(), vector_size)),
        pa.field("text", pa.string()),
        pa.field("source", pa.string()),
        pa.field("chunk_id", pa.int64()),
    ]
    schema = pa.schema(fields)

    return schema
