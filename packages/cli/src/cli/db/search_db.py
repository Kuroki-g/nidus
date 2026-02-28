from enum import Enum
import logging
from typing import List, Literal, TypedDict

from common.lance_db_manager import LanceDBManager
from common.config import settings
from common.model import EmbeddingModelManager
import numpy as np

logger = logging.getLogger(__name__)


class SearchMethod(Enum):
    Keyword = Literal["Keyword"]
    Semantic = Literal["Semantic"]
    Unknown = Literal["Unknown"]


class SearchResult(TypedDict):
    method: SearchMethod
    source: str
    text: str
    chunk_id: int


def get_single_doc_in_db(keyword: str | None) -> SearchResult | None:
    db = LanceDBManager().db
    try:
        table = db.open_table(settings.TABLE_NAME)
        query = (
            table.search().select(["source", "chunk_id", "text"]).where("chunk_id = 0")
        )
        if keyword is not None:
            query = query.where("source = '{keyword}'")
        results = query.limit(1).to_list()

        if not results:
            logger.debug(f"Information to match '{keyword}' was not found.")
            return results

        return results
    except Exception as e:
        logger.critical(e)
        return None


def list_docs_in_db(keyword: str | None) -> List[SearchResult]:
    db = LanceDBManager().db
    try:
        table = db.open_table(settings.TABLE_NAME)
        query = (
            table.search().select(["source", "chunk_id", "text"]).where("chunk_id = 0")
        )
        if keyword is not None:
            query = query.where(f"source LIKE '%{keyword}%'")
        results = query.limit(settings.SEARCH_LIMIT * 10).to_list()

        if not results:
            logger.debug(f"Information to match '{keyword}' was not found.")
            return []

        return results
    except Exception as e:
        logger.critical(e)
        return []


def display_list_results_simple(results: list[SearchResult]):
    header = f"{'Source':<15} | {'Text'}"
    print(header)
    print("-" * 80)

    for res in results:
        source = res["source"][:13] + ".." if len(res["source"]) > 15 else res["source"]
        text = res["text"].replace("\n", " ")[:50] + "..."

        print(f"{source:<15} | {text}")


def search_docs_in_db(keyword: str) -> List[SearchResult]:
    db = LanceDBManager().db
    try:
        table = db.open_table(settings.TABLE_NAME)
        # 1. Search by FTS
        fts_results = (
            table.search(keyword, query_type="fts")
            .limit(settings.SEARCH_LIMIT)
            .to_list()
        )

        # 2. Search by vector search
        model = EmbeddingModelManager().model
        raw_embedding = model.encode(keyword, show_progress_bar=False)
        query_embed = raw_embedding.astype(np.float32)

        vector_results = (
            table.search(query_embed, vector_column_name="vector")
            .limit(settings.SEARCH_LIMIT)
            .to_list()
        )

        # 3. Merge results
        seen_texts = set()
        unique_results: List[SearchResult] = []
        for row in fts_results + vector_results:
            text = row.get("text", "")
            if text in seen_texts:
                continue
            seen_texts.add(text)
            source = row.get(
                "source", "unknown"
            )  # get source else filled with "unknown"
            chunk_id = row.get("chunk_id", "unknown")

            # get first 300 words
            text_snippet = text.replace("\n", " ")[:300]
            search_method = (
                SearchMethod.Keyword if row in fts_results else SearchMethod.Semantic
            )
            result: SearchResult = {
                "method": search_method,
                "text": text_snippet,
                "source": source,
                "chunk_id": chunk_id,
            }
            unique_results.append(result)

        if not unique_results:
            logger.debug(f"Information to match '{keyword}' was not found.")
            return []

        return unique_results
    except Exception as e:
        logger.critical(e)
        return []


def display_results_simple(results: list[SearchResult]):
    header = f"{'ID':<5} | {'Method':<10} | {'Source':<15} | {'Text'}"
    print(header)
    print("-" * 80)

    for res in results:
        method = res["method"].name
        source = res["source"][:13] + ".." if len(res["source"]) > 15 else res["source"]
        text = res["text"].replace("\n", " ")[:50] + "..."

        print(f"{res['chunk_id']:<4} | {method:<8} | {source:<15} | {text}")
