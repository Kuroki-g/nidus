import datetime
from unittest.mock import MagicMock, patch

import lancedb
import pytest
from cli.db.reindex_db import get_all_sources, reindex_all_in_db
from cli.db.schemas import get_doc_chunk_schema, get_doc_meta_schema, schema_names
from common.lance_db_manager import LanceDBManager

# ---------------------------------------------------------------------------
# small tests — logic only, no real DB
# ---------------------------------------------------------------------------


class TestGetAllSourcesLogic:
    @pytest.mark.small
    def test_returns_empty_on_exception(self):
        with patch("cli.db.reindex_db.LanceDBManager") as mock_manager_cls:
            mock_db = MagicMock()
            mock_db.open_table.side_effect = Exception("table not found")
            mock_manager_cls.return_value.db = mock_db

            result = get_all_sources("/fake/path")

        assert result == []

    @pytest.mark.small
    def test_returns_sources_from_rows(self):
        with patch("cli.db.reindex_db.LanceDBManager") as mock_manager_cls:
            mock_table = MagicMock()
            mock_table.search.return_value.select.return_value.to_list.return_value = [
                {"source": "/a.md"},
                {"source": "/b.md"},
            ]
            mock_db = MagicMock()
            mock_db.open_table.return_value = mock_table
            mock_manager_cls.return_value.db = mock_db

            result = get_all_sources("/fake/path")

        assert result == ["/a.md", "/b.md"]


class TestReindexAllLogic:
    @pytest.mark.small
    def test_dry_run_prints_files(self, tmp_path, capsys):
        existing = tmp_path / "doc.md"
        existing.write_text("hello")

        with patch("cli.db.reindex_db.get_all_sources", return_value=[str(existing)]):
            reindex_all_in_db(dry_run=True, db_path=str(tmp_path / ".lancedb"))

        out = capsys.readouterr().out
        assert "Would reindex 1 file(s)" in out
        assert str(existing) in out

    @pytest.mark.small
    def test_dry_run_shows_missing_files(self, tmp_path, capsys):
        missing = "/nonexistent/file.md"

        with patch("cli.db.reindex_db.get_all_sources", return_value=[missing]):
            reindex_all_in_db(dry_run=True, db_path=str(tmp_path / ".lancedb"))

        out = capsys.readouterr().out
        assert "Would reindex 0 file(s)" in out
        assert "Missing" in out
        assert missing in out

    @pytest.mark.small
    def test_dry_run_does_not_call_update(self, tmp_path):
        existing = tmp_path / "doc.md"
        existing.write_text("hello")

        with (
            patch("cli.db.reindex_db.get_all_sources", return_value=[str(existing)]),
            patch("cli.db.update_db.update_files_in_db") as mock_update,
        ):
            reindex_all_in_db(dry_run=True, db_path=str(tmp_path / ".lancedb"))

        mock_update.assert_not_called()

    @pytest.mark.small
    def test_no_sources_returns_early(self, tmp_path):
        with (
            patch("cli.db.reindex_db.get_all_sources", return_value=[]),
            patch("cli.db.update_db.update_files_in_db") as mock_update,
        ):
            reindex_all_in_db(db_path=str(tmp_path / ".lancedb"))

        mock_update.assert_not_called()


# ---------------------------------------------------------------------------
# medium tests — real LanceDB
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_lance_singleton():
    LanceDBManager._instance = None
    LanceDBManager._db = None
    yield
    LanceDBManager._instance = None
    LanceDBManager._db = None


def _setup_db(db_path: str) -> None:
    db = lancedb.connect(db_path)
    db.create_table(schema_names.doc_meta, schema=get_doc_meta_schema())
    db.create_table(schema_names.doc_chunk, schema=get_doc_chunk_schema(4))


def _add_records(db_path: str, source: str) -> None:
    today = datetime.date.today()
    db = lancedb.connect(db_path)
    db.open_table(schema_names.doc_meta).add(
        [
            {
                "source": source,
                "doc_name": "test.md",
                "created": today,
                "updated": today,
                "file_hash": "oldhash",
            }
        ]
    )
    db.open_table(schema_names.doc_chunk).add(
        [
            {
                "source": source,
                "doc_name": "test.md",
                "vector": [0.0] * 4,
                "chunk_id": 0,
                "chunk_text": "old content",
            }
        ]
    )


def _count(db_path: str, table_name: str) -> int:
    return lancedb.connect(db_path).open_table(table_name).count_rows()


@pytest.mark.medium
def test_get_all_sources_returns_registered(tmp_path):
    db_path = str(tmp_path / ".lancedb")
    _setup_db(db_path)
    _add_records(db_path, "/some/doc.md")

    sources = get_all_sources(db_path)

    assert sources == ["/some/doc.md"]


@pytest.mark.medium
def test_get_all_sources_empty_db(tmp_path):
    db_path = str(tmp_path / ".lancedb")
    _setup_db(db_path)

    sources = get_all_sources(db_path)

    assert sources == []


@pytest.mark.medium
def test_reindex_clears_and_rebuilds(tmp_path):
    """再インデックス後、チャンクが再生成されること。"""
    db_path = str(tmp_path / ".lancedb")
    _setup_db(db_path)

    # 実在ファイルを作成してDBに登録
    doc = tmp_path / "note.md"
    doc.write_text("# Hello\nThis is content.")
    _add_records(db_path, str(doc))

    assert _count(db_path, schema_names.doc_chunk) == 1

    with patch("cli.db.update_db.update_files_in_db") as mock_update:
        reindex_all_in_db(db_path=db_path)

    # 削除されたことを確認
    assert _count(db_path, schema_names.doc_meta) == 0
    assert _count(db_path, schema_names.doc_chunk) == 0
    # update_files_in_db が正しいファイルで呼ばれたことを確認
    mock_update.assert_called_once()
    called_files = mock_update.call_args[0][0]
    assert doc in called_files


@pytest.mark.medium
def test_reindex_skips_missing_files(tmp_path):
    """ディスク上に存在しないファイルは除外されること。"""
    db_path = str(tmp_path / ".lancedb")
    _setup_db(db_path)
    _add_records(db_path, "/nonexistent/ghost.md")

    with patch("cli.db.update_db.update_files_in_db") as mock_update:
        reindex_all_in_db(db_path=db_path)

    mock_update.assert_not_called()
