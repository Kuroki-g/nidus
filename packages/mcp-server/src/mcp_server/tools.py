import logging
from pathlib import Path
from typing import List

from common.format import format_mes
from mcp.server import FastMCP

from cli.db.search_db import search_docs_in_db, SearchMethod
from cli.db.update_db import update_files_in_db

logger = logging.getLogger(__name__)


def update_docs(path_list: List[Path]) -> None:
    """
    Update documents using all files assigned path_list.

    Args:
        path_list (List[Path]): target path to be analyzed.
    """
    try:
        update_files_in_db(path_list)
    except Exception as e:
        logger.error(e)
        return f"failed to update documents information: {str(e)}"


def search_docs(keyword: str) -> str:
    """
    Search documents from database using Hybrid Search (FTS + Vector).
    """
    try:
        unique_results = search_docs_in_db(keyword)

        if not unique_results:
            return f"'{keyword}' was not found."

        # 1. 検索手法ごとにグループ化
        keyword_matches = [
            r for r in unique_results if r["method"] == SearchMethod.Keyword
        ]
        semantic_matches = [
            r for r in unique_results if r["method"] == SearchMethod.Semantic
        ]

        # 2. Keywordを優先して最大5件抽出
        # まずKeywordを入れ、足りない枠（5 - len）をSemanticから取得
        display_results = keyword_matches[:5]

        if len(display_results) < 5:
            needed = 5 - len(display_results)
            display_results.extend(semantic_matches[:needed])

        # 3. テキスト整形
        output = []  # リストを初期化
        for row in display_results:
            source = row["source"]
            search_method = row["method"]
            text_snippet = row.get("text", "").replace("\n", " ")[:300]

            output.append(
                f"--- source: {source} [{search_method}] ---\n{text_snippet}...\n"
            )

        return "\n".join(output)
    except Exception as e:
        return f"検索エラーが発生しました: {str(e)}"


def list_docs(keyword: str) -> str:
    try:
        from cli.db.search_db import list_docs_in_db

        results = list_docs_in_db(keyword)

        if not results:
            return f"source match to {keyword}' was not found."

        output = []
        for row in results:
            source = row["source"]
            text_snippet = row.get("text", "").replace("\n", " ")[:300]

            output.append(f"--- source: {source} ---\n{text_snippet}...\n")
        return "\n".join(output)
    except Exception as e:
        return format_mes(str(e))


def db_show_meta() -> str:
    """show metadata for database file"""
    from cli.meta.db_info import get_meta, Metadata

    def get_meta_summary_str(meta: Metadata, max_fields: int = 10) -> str:
        """
        convert database metadata to structured txt.
        truncate files if too much fields.
        """
        lines = [
            f"Database Path: {meta['database_path']}",
            f"Total Tables: {meta['total_tables']}",
            "--- Table Details ---",
        ]

        for tbl in meta["tables"]:
            # extract schema as "name(type)" format
            # 例: id(int64), vector(fixed_size_list[float32]), text(string)
            fields = [f"{f.name}({f.type})" for f in tbl["schema"]]

            # truncate fields if there is too many
            if len(fields) > max_fields:
                fields_str = (
                    ", ".join(fields[:max_fields])
                    + f" ... (+{len(fields) - max_fields} more)"
                )
            else:
                fields_str = ", ".join(fields)

            table_line = (
                f"- Table: {tbl['table_name']}\n"
                f"  Count: {tbl['record_count']}\n"
                f"  Version: {tbl['version']}\n"
                f"  Schema: [{fields_str}]"
            )
            lines.append(table_line)

        return "\n".join(lines)

    meta = get_meta()

    return get_meta_summary_str(meta)


def register_tools(mcp: FastMCP):
    mcp.tool()(search_docs)
    mcp.tool()(update_docs)
    mcp.tool()(list_docs)
