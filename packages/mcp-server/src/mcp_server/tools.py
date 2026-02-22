from mcp.server import FastMCP

from cli.db.search_db import search_docs_in_db, SearchMethod


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


def register_tools(mcp: FastMCP):
    mcp.tool()(search_docs)
