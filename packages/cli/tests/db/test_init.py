from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from cli.db.init import create_db_schemas, init_db, init_model

pytestmark = pytest.mark.medium


# ---------------------------------------------------------------------------
# small tests — init_model / init_db (all external calls mocked)
# ---------------------------------------------------------------------------


class TestInitModel:
    @pytest.mark.small
    def test_success_loads_model(self):
        """EmbeddingModelManager() が成功すれば snapshot_download は呼ばれない。"""
        mock_model = MagicMock()
        with (
            patch("common.model.EmbeddingModelManager", return_value=mock_model),
            patch("huggingface_hub.snapshot_download") as mock_dl,
        ):
            init_model()
        mock_dl.assert_not_called()

    @pytest.mark.small
    def test_fallback_downloads_model(self):
        """EmbeddingModelManager() が失敗したら snapshot_download が呼ばれる。"""
        with (
            patch("common.model.EmbeddingModelManager", side_effect=Exception("no model")),
            patch("huggingface_hub.snapshot_download") as mock_dl,
        ):
            init_model()
        mock_dl.assert_called_once()

    @pytest.mark.small
    def test_exits_on_download_failure(self):
        """モデルロードもダウンロードも失敗したら SystemExit が発生する。"""
        with (
            patch("common.model.EmbeddingModelManager", side_effect=Exception("no model")),
            patch("huggingface_hub.snapshot_download", side_effect=Exception("network error")),
            pytest.raises(SystemExit),
        ):
            init_model()


class TestInitDb:
    @pytest.mark.small
    def test_calls_create_schemas_and_update(self):
        """init_db は create_db_schemas と update_files_in_db を呼び出す。"""
        paths = [Path("/tmp/doc.md")]
        with (
            patch("cli.db.init.create_db_schemas") as mock_schema,
            patch("cli.db.init.update_files_in_db") as mock_update,
        ):
            init_db(paths)
        mock_schema.assert_called_once()
        mock_update.assert_called_once_with(paths)


# ---------------------------------------------------------------------------
# medium tests — create_db_schemas (real LanceDB, mocked model)
# ---------------------------------------------------------------------------


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
