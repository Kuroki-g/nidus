import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import lancedb
import pytest
from cli.db.schemas import get_doc_chunk_schema, get_doc_meta_schema, schema_names
from cli.db.update_db import _get_existing_meta, create_chunk_fts_index, update_files_in_db
from common.lance_db_manager import LanceDBManager

# ---------------------------------------------------------------------------
# small tests — logic only, no real DB
# ---------------------------------------------------------------------------


class TestCreateChunkFtsIndex:
    @pytest.mark.small
    def test_calls_create_fts_index_with_bigram(self):
        mock_table = MagicMock()
        create_chunk_fts_index(mock_table)
        mock_table.create_fts_index.assert_called_once_with(
            "chunk_text",
            replace=True,
            base_tokenizer="ngram",
            ngram_min_length=2,
            ngram_max_length=2,
            lower_case=False,
            stem=False,
            remove_stop_words=False,
            ascii_folding=False,
        )


class TestGetExistingMeta:
    @pytest.mark.small
    def test_empty_files_returns_empty_dict(self):
        mock_table = MagicMock()
        result = _get_existing_meta(mock_table, [])
        assert result == {}
        mock_table.search.assert_not_called()

    @pytest.mark.small
    def test_returns_dict_keyed_by_source(self):
        today = datetime.date.today()
        mock_table = MagicMock()
        (
            mock_table.search.return_value.where.return_value.select.return_value.to_list
        ).return_value = [{"source": "/a.md", "created": today, "file_hash": "abc123"}]

        result = _get_existing_meta(mock_table, [Path("/a.md")])

        assert "/a.md" in result
        assert result["/a.md"]["file_hash"] == "abc123"
        assert result["/a.md"]["created"] == today

    @pytest.mark.small
    def test_exception_returns_empty_dict(self):
        mock_table = MagicMock()
        mock_table.search.side_effect = Exception("DB error")
        result = _get_existing_meta(mock_table, [Path("/a.md")])
        assert result == {}

    @pytest.mark.small
    def test_multiple_files_all_returned(self):
        today = datetime.date.today()
        mock_table = MagicMock()
        (
            mock_table.search.return_value.where.return_value.select.return_value.to_list
        ).return_value = [
            {"source": "/a.md", "created": today, "file_hash": "hash_a"},
            {"source": "/b.md", "created": today, "file_hash": "hash_b"},
        ]
        result = _get_existing_meta(mock_table, [Path("/a.md"), Path("/b.md")])
        assert len(result) == 2
        assert result["/a.md"]["file_hash"] == "hash_a"
        assert result["/b.md"]["file_hash"] == "hash_b"


# ---------------------------------------------------------------------------
# medium tests — real LanceDB, mocked model / data_generator
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


def _count(db_path: str, table_name: str) -> int:
    return lancedb.connect(db_path).open_table(table_name).count_rows()


def _add_meta(db_path: str, source: str, file_hash: str = "oldhash") -> None:
    today = datetime.date.today()
    db = lancedb.connect(db_path)
    db.open_table(schema_names.doc_meta).add(
        [
            {
                "source": source,
                "doc_name": "test.md",
                "created": today,
                "updated": today,
                "file_hash": file_hash,
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


def _fake_chunk(source: str) -> dict:
    return {
        "source": source,
        "doc_name": "doc.md",
        "vector": [0.0] * 4,
        "chunk_id": 0,
        "chunk_text": "test content",
    }


@pytest.mark.medium
def test_update_no_valid_files(tmp_path):
    """対応外拡張子のみのファイルは何もしない。"""
    db_path = str(tmp_path / ".lancedb")
    _setup_db(db_path)
    unsupported = tmp_path / "file.xyz"
    unsupported.write_text("content")

    with patch("cli.db.update_db.create_chunk_fts_index") as mock_fts:
        update_files_in_db([unsupported], db_path=db_path)

    mock_fts.assert_not_called()
    assert _count(db_path, schema_names.doc_meta) == 0


@pytest.mark.medium
def test_update_all_up_to_date(tmp_path):
    """ファイルが未変更ならインデックスを再構築しない。"""
    from cli.db.schemas import get_file_hash

    db_path = str(tmp_path / ".lancedb")
    _setup_db(db_path)
    md = tmp_path / "doc.md"
    md.write_text("# Hello")
    _add_meta(db_path, str(md), file_hash=get_file_hash(md))

    with patch("cli.db.update_db.create_chunk_fts_index") as mock_fts:
        update_files_in_db([md], db_path=db_path)

    mock_fts.assert_not_called()
    assert _count(db_path, schema_names.doc_meta) == 1


@pytest.mark.medium
def test_update_new_file_adds_records(tmp_path):
    """新規ファイルが meta と chunk に登録される。"""
    db_path = str(tmp_path / ".lancedb")
    _setup_db(db_path)
    md = tmp_path / "doc.md"
    md.write_text("# Hello")

    with (
        patch("cli.db.update_db.data_generator", return_value=iter([[_fake_chunk(str(md))]])),
        patch("cli.db.update_db.create_chunk_fts_index"),
    ):
        update_files_in_db([md], db_path=db_path)

    assert _count(db_path, schema_names.doc_meta) == 1
    assert _count(db_path, schema_names.doc_chunk) == 1


@pytest.mark.medium
def test_update_changed_file_replaces_records(tmp_path):
    """変更済みファイルは古いレコードが削除されて新しいものに置き換わる。"""
    db_path = str(tmp_path / ".lancedb")
    _setup_db(db_path)
    md = tmp_path / "doc.md"
    md.write_text("# Hello")
    _add_meta(db_path, str(md), file_hash="oldhash")  # 意図的に古いハッシュ
    assert _count(db_path, schema_names.doc_chunk) == 1

    with (
        patch("cli.db.update_db.data_generator", return_value=iter([[_fake_chunk(str(md))]])),
        patch("cli.db.update_db.create_chunk_fts_index"),
    ):
        update_files_in_db([md], db_path=db_path)

    assert _count(db_path, schema_names.doc_meta) == 1
    assert _count(db_path, schema_names.doc_chunk) == 1


@pytest.mark.medium
def test_update_preserves_created_date_on_change(tmp_path):
    """更新時に created 日付が引き継がれる。"""
    import datetime

    db_path = str(tmp_path / ".lancedb")
    _setup_db(db_path)
    md = tmp_path / "doc.md"
    md.write_text("# Hello")
    original_created = datetime.date(2020, 1, 1)

    db = lancedb.connect(db_path)
    db.open_table(schema_names.doc_meta).add(
        [
            {
                "source": str(md),
                "doc_name": "doc.md",
                "created": original_created,
                "updated": original_created,
                "file_hash": "oldhash",
            }
        ]
    )
    db.open_table(schema_names.doc_chunk).add([_fake_chunk(str(md))])

    with (
        patch("cli.db.update_db.data_generator", return_value=iter([[_fake_chunk(str(md))]])),
        patch("cli.db.update_db.create_chunk_fts_index"),
    ):
        update_files_in_db([md], db_path=db_path)

    rows = lancedb.connect(db_path).open_table(schema_names.doc_meta).search().to_list()
    assert rows[0]["created"] == original_created


@pytest.mark.medium
def test_update_auto_creates_tables_if_missing(tmp_path):
    """テーブルが存在しない場合は自動で作成してからレコードを追加する。"""
    db_path = str(tmp_path / ".lancedb")
    # テーブルを作らずに実行
    md = tmp_path / "doc.md"
    md.write_text("# Hello")

    mock_model = MagicMock()
    mock_model.vector_size = 4

    with (
        patch("common.model.EmbeddingModelManager", return_value=mock_model),
        patch("cli.db.update_db.data_generator", return_value=iter([[_fake_chunk(str(md))]])),
        patch("cli.db.update_db.create_chunk_fts_index"),
    ):
        update_files_in_db([md], db_path=db_path)

    assert _count(db_path, schema_names.doc_meta) == 1
    assert _count(db_path, schema_names.doc_chunk) == 1
