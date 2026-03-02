import pytest

from cli.db.init import create_db_schemas

pytestmark = pytest.mark.medium


def test_create_db_schemas(tmp_path):
    test_db_path = tmp_path / "test_db" / ".lancedb"
    doc_meta_table, doc_chunk_table = create_db_schemas(test_db_path)

    assert doc_meta_table is not None
    assert doc_chunk_table is not None
    assert doc_meta_table.name == "doc_meta"
    assert doc_chunk_table.name == "doc_chunk"
