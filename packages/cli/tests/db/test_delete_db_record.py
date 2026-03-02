import datetime
from pathlib import Path

import lancedb
import pytest

from cli.db.delete_db_record import delete_files_in_db
from cli.db.schemas import get_doc_chunk_schema, get_doc_meta_schema, schema_names
from common.lance_db_manager import LanceDBManager

pytestmark = pytest.mark.medium


@pytest.fixture(autouse=True)
def reset_lance_singleton():
    LanceDBManager._instance = None
    LanceDBManager._db = None
    yield
    LanceDBManager._instance = None
    LanceDBManager._db = None


def _setup_db(tmp_path):
    db_path = str(tmp_path / ".lancedb")
    db = lancedb.connect(db_path)
    db.create_table(schema_names.doc_meta, schema=get_doc_meta_schema())
    db.create_table(schema_names.doc_chunk, schema=get_doc_chunk_schema(4))
    return db_path


def _count(db_path: str, table_name: str) -> int:
    """テーブルの行数を新規コネクションで取得する。"""
    return lancedb.connect(db_path).open_table(table_name).count_rows()


def _meta(source: str) -> dict:
    today = datetime.date.today()
    return {
        "source": source,
        "doc_name": "test",
        "created": today,
        "updated": today,
        "file_hash": "abc",
    }


def _chunk(source: str, chunk_id: int = 0) -> dict:
    return {
        "source": source,
        "doc_name": "test",
        "vector": [0.0] * 4,
        "chunk_id": chunk_id,
        "chunk_text": "hello",
    }


def _add(db_path: str, rows_meta: list[dict], rows_chunk: list[dict]):
    db = lancedb.connect(db_path)
    db.open_table(schema_names.doc_meta).add(rows_meta)
    db.open_table(schema_names.doc_chunk).add(rows_chunk)


def test_delete_path_with_apostrophe(tmp_path):
    """アポストロフィを含むパスでもクエリが壊れず削除できる。"""
    db_path = _setup_db(tmp_path)
    source = "/home/user/it's_notes.md"
    _add(db_path, [_meta(source)], [_chunk(source)])

    assert _count(db_path, schema_names.doc_meta) == 1

    delete_files_in_db([Path(source)], db_path=db_path)

    assert _count(db_path, schema_names.doc_meta) == 0
    assert _count(db_path, schema_names.doc_chunk) == 0


def test_delete_normal_path(tmp_path):
    """アポストロフィなしの通常パスで削除できる。"""
    db_path = _setup_db(tmp_path)
    source = "/home/user/notes.md"
    _add(db_path, [_meta(source)], [_chunk(source)])

    delete_files_in_db([Path(source)], db_path=db_path)

    assert _count(db_path, schema_names.doc_meta) == 0
    assert _count(db_path, schema_names.doc_chunk) == 0


def test_delete_only_target_path(tmp_path):
    """対象パスのみ削除され、他のレコードは残る。"""
    db_path = _setup_db(tmp_path)
    target = "/home/user/it's file.md"
    other = "/home/user/other.md"
    _add(db_path, [_meta(target), _meta(other)], [_chunk(target), _chunk(other)])

    delete_files_in_db([Path(target)], db_path=db_path)

    assert _count(db_path, schema_names.doc_meta) == 1
    assert _count(db_path, schema_names.doc_chunk) == 1
