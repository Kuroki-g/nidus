import logging
from pathlib import Path
from typing import List, TypedDict
from common.config import settings
from common.lance_db_manager import LanceDBManager

logger = logging.getLogger(__name__)


class TableInfo(TypedDict):
    table_name: str
    record_count: int
    schema: int
    version: int


class Metadata(TypedDict):
    database_path: Path
    total_tables: int
    tables: List[TableInfo]


def get_meta(
    db_path=settings.DB_PATH,
) -> Metadata:
    db_m = LanceDBManager(db_path)
    table_names = db_m.db.table_names()

    metadata: Metadata = {
        "database_path": db_m.db_uri,
        "total_tables": len(table_names),
        "tables": [],
    }

    for name in table_names:
        tbl = db_m.db.open_table(name)
        table_info: TableInfo = {
            "table_name": name,
            "record_count": len(tbl),
            "schema": tbl.schema,
            "version": tbl.version,
        }
        metadata["tables"].append(table_info)

    return metadata


def display_meta_simple(meta: Metadata):
    print("\n--- Database Metadata ---")
    print(f"Path:  {meta['database_path']}")
    print(f"Total: {meta['total_tables']} tables")
    print("-" * 80)

    # ヘッダー (Source / Count / Schema)
    header = f"{'Table Name':<20} | {'Count':>8} | {'Schema (Fields)'}"
    print(header)
    print("-" * 80)

    for tbl in meta["tables"]:
        name = tbl["table_name"]
        count = tbl["record_count"]
        fields = ", ".join([field.name for field in tbl["schema"]])
        display_fields = (fields[:50] + "...") if len(fields) > 50 else fields

        print(f"{name:<20} | {count:>8} | {display_fields}")

    print("-" * 80)
