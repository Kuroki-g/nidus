from enum import Enum
import logging
from typing import List, Literal, TypedDict

from common.lance_db_manager import LanceDBManager
from common.config import settings
from common.model import EmbeddingModelManager
import numpy as np

logger = logging.getLogger(__name__)

# FTS bigram requires at least 2 characters to form a token
_FTS_MIN_QUERY_LENGTH = 2


class SearchMethod(Enum):
    Keyword = Literal["Keyword"]
    Semantic = Literal["Semantic"]
    Hybrid = Literal["Hybrid"]


class SearchResult(TypedDict):
    method: SearchMethod
    source: str
    text: str
    chunk_id: int
    score: float


class DocListEntry(TypedDict):
    source: str
    doc_name: str


def _rrf_score(rank: int, k: int) -> float:
    return 1.0 / (k + rank + 1)


def _get_adjacent_text(table, source: str, chunk_id: int, window: int) -> str:
    """Fetch chunk_id-window to chunk_id+window and concatenate as context."""
    lo = max(0, chunk_id - window)
    hi = chunk_id + window
    where_clause = f"source = '{source}' AND chunk_id >= {lo} AND chunk_id <= {hi}"
    rows = (
        table.search()
        .where(where_clause)
        .select(["chunk_id", "chunk_text"])
        .to_list()
    )
    rows_sorted = sorted(rows, key=lambda r: r["chunk_id"])
    return "\n".join(r["chunk_text"] for r in rows_sorted)


def list_docs_in_db(keyword: str | None) -> List[DocListEntry]:
    from cli.db.schemas import schema_names

    db = LanceDBManager().db
    try:
        table = db.open_table(schema_names.doc_meta)
        query = table.search().select(["source", "doc_name"])
        if keyword is not None:
            query = query.where(f"source LIKE '%{keyword}%'")
        results = query.limit(settings.SEARCH_LIMIT * 10).to_list()
        return results
    except Exception as e:
        logger.critical(e)
        return []


def display_list_results_simple(results: List[DocListEntry]):
    header = f"{'Source':<60} | {'Name'}"
    print(header)
    print("-" * 80)

    for res in results:
        source = res["source"]
        doc_name = res.get("doc_name", "")
        print(f"{source:<60} | {doc_name}")


def search_docs_in_db(keyword: str) -> List[SearchResult]:
    from cli.db.schemas import schema_names

    db = LanceDBManager().db
    try:
        table = db.open_table(schema_names.doc_chunk)

        rrf_k = settings.SEARCH_RRF_K
        adjacent_window = settings.SEARCH_ADJACENT_WINDOW

        # 1. FTS search (bigram requires at least 2 characters)
        # TODO: "_score" は lance の autoprojection 警告を抑制するための workaround。
        #       lancedb Python API に disable_scoring_autoprojection() が公開されたら
        #       "_score" を select から除いてそちらに切り替える。
        use_fts = len(keyword.strip()) >= _FTS_MIN_QUERY_LENGTH
        if use_fts:
            fts_results = (
                table.search(keyword, query_type="fts")
                .select(["source", "chunk_id", "chunk_text", "_score"])
                .limit(settings.SEARCH_LIMIT)
                .to_list()
            )
        else:
            logger.debug(
                f"FTS skipped: query '{keyword}' is shorter than {_FTS_MIN_QUERY_LENGTH} characters."
            )
            fts_results = []

        # 2. Vector search
        # TODO: "_distance" も同様の workaround。上記と同タイミングで解消する。
        model = EmbeddingModelManager().model
        query_embed = model.encode(
            keyword, show_progress_bar=False, convert_to_numpy=True
        ).astype(np.float32)

        vector_results = (
            table.search(query_embed, vector_column_name="vector")
            .select(["source", "chunk_id", "chunk_text", "_distance"])
            .limit(settings.SEARCH_LIMIT)
            .to_list()
        )

        # 3. RRF scoring
        scores: dict[tuple[str, int], float] = {}
        methods: dict[tuple[str, int], SearchMethod] = {}

        for rank, row in enumerate(fts_results):
            key = (row["source"], row["chunk_id"])
            scores[key] = scores.get(key, 0.0) + _rrf_score(rank, rrf_k)
            methods[key] = SearchMethod.Keyword

        for rank, row in enumerate(vector_results):
            key = (row["source"], row["chunk_id"])
            scores[key] = scores.get(key, 0.0) + _rrf_score(rank, rrf_k)
            if key in methods:
                methods[key] = SearchMethod.Hybrid
            else:
                methods[key] = SearchMethod.Semantic

        # 4. Sort by RRF score and build results with adjacent context
        sorted_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)

        unique_results: List[SearchResult] = []
        for source, chunk_id in sorted_keys[: settings.SEARCH_LIMIT]:
            text = _get_adjacent_text(table, source, chunk_id, adjacent_window)
            result: SearchResult = {
                "method": methods[(source, chunk_id)],
                "text": text,
                "source": source,
                "chunk_id": chunk_id,
                "score": scores[(source, chunk_id)],
            }
            unique_results.append(result)

        if not unique_results:
            logger.debug(f"Information to match '{keyword}' was not found.")

        return unique_results
    except Exception as e:
        logger.critical(e)
        return []


def display_results_simple(results: List[SearchResult]):
    header = f"{'Score':<8} | {'Method':<10} | {'Source':<15} | {'Text'}"
    print(header)
    print("-" * 80)

    for res in results:
        score = f"{res['score']:.4f}"
        method = res["method"].name
        source = res["source"][:13] + ".." if len(res["source"]) > 15 else res["source"]
        text = res["text"].replace("\n", " ")[:50] + "..."

        print(f"{score:<8} | {method:<10} | {source:<15} | {text}")
