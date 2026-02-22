from init_scripts.main import TABLE_NAME
from mcp.server import FastMCP
from common.lance_db_manager import LanceDBManager
import numpy as np
import pyarrow as pa  # noqa: F401 This cannot be removed (# https://github.com/lancedb/lancedb/issues/2384)

from common.model import EmbeddingModelManager


def search_docs(keyword: str) -> str:
    """
    Search documents from database using Hybrid Search (FTS + Vector).
    """
    db = LanceDBManager().db
    try:
        table = db.open_table(TABLE_NAME)
        # 1. まずは全文検索 (FTS) で「ズバリその言葉」が入っているものを探す
        fts_results = table.search(keyword, query_type="fts").limit(3).to_list()

        # 2. 次にベクトル検索で「意味的に近いもの」を探す
        model = EmbeddingModelManager().model
        raw_embedding = model.encode(keyword, show_progress_bar=False)
        query_embed = raw_embedding.astype(np.float32)

        vector_results = (
            table.search(query_embed, vector_column_name="vector").limit(5).to_list()
        )

        # 3. 結果を統合 (FTSの結果を優先しつつ重複を除く)
        seen_texts = set()
        unique_results = []

        for row in fts_results + vector_results:
            content = row.get("text", "")
            if content not in seen_texts:
                unique_results.append(row)
                seen_texts.add(content)

        if not unique_results:
            return f"'{keyword}' に関連する情報は見つかりませんでした。"

        output = [f"【{keyword}】の検索結果 (上位 {len(unique_results[:5])}件):"]
        for row in unique_results[:5]:  # 最終的に5件に絞る
            metadata = row.get("metadata", {})
            source = metadata.get("source", "unknown")
            text_snippet = row.get("text", "").replace("\n", " ")[:300]

            # FTSでヒットしたかどうかの印（任意）
            search_method = "Keyword" if row in fts_results else "Semantic"
            output.append(
                f"--- source: {source} [{search_method}] ---\n{text_snippet}...\n"
            )

        return "\n".join(output)
    except Exception as e:
        return f"検索エラーが発生しました: {str(e)}"


def register_tools(mcp: FastMCP):
    mcp.tool()(search_docs)
