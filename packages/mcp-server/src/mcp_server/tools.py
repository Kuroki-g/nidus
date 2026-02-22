import os

from init_scripts.main import TABLE_NAME
from mcp.server import FastMCP
from mcp_server.lance_db_manager import LanceDBManager
import numpy as np
from sentence_transformers import SentenceTransformer
import pyarrow as pa 

os.environ["TRANSFORMERS_OFFLINE"] = "1"
model_name = "hotchpotch/static-embedding-japanese"
# シングルトン内で使い回せるように、ここでモデルをロード（またはManagerに入れる）
model = SentenceTransformer(model_name, local_files_only=True)

def search_docs(keyword: str) -> str:
    """
    ナレッジベースからベクトル検索で関連ドキュメントを探します。
    """
    db = LanceDBManager().db
    try:
        table = db.open_table(TABLE_NAME)
        raw_embedding = model.encode(keyword)
        query_embed = raw_embedding.astype(np.float32)
        results = (
            table.search(query_embed, vector_column_name="vector")
            .limit(5)
            .to_list()
        )

        if len(results) == 0:
            return f"'{keyword}' に関連する情報は見つかりませんでした。"

        output = [f"【{keyword}】の検索結果:"]
        for row in results:
            # row は辞書型なので、そのままキーでアクセス可能
            # row['metadata'] は初期化時の構造（dict）のまま入っています
            metadata = row.get('metadata', {})
            source = metadata.get('source', 'unknown')
            text_snippet = row.get('text', '')[:200]
            
            output.append(f"--- source: {source} ---\n{text_snippet}\n")
                
        return "\n".join(output)
    except Exception as e:
        return f"検索エラーが発生しました: {str(e)}"

def register_tools(mcp: FastMCP):
    mcp.tool()(search_docs)
