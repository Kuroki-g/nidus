from unittest.mock import MagicMock, patch

import pytest
from cli.db.init import create_db_schemas

pytestmark = pytest.mark.medium


def test_create_db_schemas(tmp_path):
    test_db_path = tmp_path / "test_db" / ".lancedb"

    mock_model = MagicMock()
    mock_model.vector_size = 1024

    with patch("common.model.EmbeddingModelManager", return_value=mock_model):
        doc_meta_table, doc_chunk_table = create_db_schemas(test_db_path)

    assert doc_meta_table is not None
    assert doc_chunk_table is not None
    assert doc_meta_table.name == "doc_meta"
    assert doc_chunk_table.name == "doc_chunk"
