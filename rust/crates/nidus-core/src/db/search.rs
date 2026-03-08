use std::collections::HashMap;

use anyhow::{Context, Result};
use arrow_array::{Int64Array, RecordBatch, StringArray};
use futures_util::TryStreamExt;
use lance_index::scalar::FullTextSearchQuery;
use lancedb::query::{ExecutableQuery, QueryBase};
use lancedb::{Connection, Table};

use crate::db::connection::DEFAULT_TABLE_DOC_CHUNK;
use crate::embedding::EmbeddingModel;

/// FTS バイグラムは最低 2 文字のトークンが必要。
const FTS_MIN_QUERY_LENGTH: usize = 2;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SearchMethod {
    Keyword,
    Semantic,
    Hybrid,
}

impl std::fmt::Display for SearchMethod {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SearchMethod::Keyword => write!(f, "Keyword"),
            SearchMethod::Semantic => write!(f, "Semantic"),
            SearchMethod::Hybrid => write!(f, "Hybrid"),
        }
    }
}

#[derive(Debug, Clone)]
pub struct SearchResult {
    pub source: String,
    pub chunk_id: i64,
    pub text: String,
    pub score: f64,
    pub method: SearchMethod,
}

/// RRF スコア: 1 / (k + rank + 1)
fn rrf_score(rank: usize, k: usize) -> f64 {
    1.0 / (k + rank + 1) as f64
}

/// RecordBatch リストから `(source, chunk_id)` のペアを抽出する。
fn extract_source_chunk(batches: &[RecordBatch]) -> Vec<(String, i64)> {
    let mut result = Vec::new();
    for batch in batches {
        let Some(src_col) = batch.column_by_name("source") else {
            continue;
        };
        let Some(id_col) = batch.column_by_name("chunk_id") else {
            continue;
        };
        let Some(sources) = src_col.as_any().downcast_ref::<StringArray>() else {
            continue;
        };
        let Some(ids) = id_col.as_any().downcast_ref::<Int64Array>() else {
            continue;
        };
        for i in 0..batch.num_rows() {
            result.push((sources.value(i).to_string(), ids.value(i)));
        }
    }
    result
}

/// `chunk_id` の前後 `window` 個のチャンクを連結してコンテキストテキストを返す。
async fn get_adjacent_text(
    table: &Table,
    source: &str,
    chunk_id: i64,
    window: usize,
) -> Result<String> {
    let lo = (chunk_id - window as i64).max(0);
    let hi = chunk_id + window as i64;
    let escaped = source.replace('\'', "''");
    let filter = format!(
        "source = '{}' AND chunk_id >= {} AND chunk_id <= {}",
        escaped, lo, hi
    );

    let batches: Vec<RecordBatch> = table
        .query()
        .only_if(filter)
        .execute()
        .await
        .context("adjacent text query failed")?
        .try_collect()
        .await
        .context("adjacent text collect failed")?;

    let mut rows: Vec<(i64, String)> = Vec::new();
    for batch in &batches {
        let Some(id_col) = batch.column_by_name("chunk_id") else {
            continue;
        };
        let Some(text_col) = batch.column_by_name("chunk_text") else {
            continue;
        };
        let Some(ids) = id_col.as_any().downcast_ref::<Int64Array>() else {
            continue;
        };
        let Some(texts) = text_col.as_any().downcast_ref::<StringArray>() else {
            continue;
        };
        for i in 0..batch.num_rows() {
            rows.push((ids.value(i), texts.value(i).to_string()));
        }
    }
    rows.sort_by_key(|(id, _)| *id);
    Ok(rows
        .into_iter()
        .map(|(_, t)| t)
        .collect::<Vec<_>>()
        .join("\n"))
}

/// FTS + ベクターハイブリッド検索を実行して RRF スコアで統合した結果を返す。
///
/// - クエリが 2 文字未満の場合は FTS をスキップしてベクター検索のみ行う。
/// - 上位 `limit` 件について前後 `adjacent_window` チャンクを結合したテキストを返す。
pub async fn search_docs(
    query: &str,
    db: &Connection,
    model: &EmbeddingModel,
    limit: usize,
    rrf_k: usize,
    adjacent_window: usize,
) -> Result<Vec<SearchResult>> {
    let table = db
        .open_table(DEFAULT_TABLE_DOC_CHUNK)
        .execute()
        .await
        .context("failed to open doc_chunk table")?;

    // 1. FTS 検索（バイグラムのため 2 文字以上のクエリのみ）
    let use_fts = query.chars().count() >= FTS_MIN_QUERY_LENGTH;
    let fts_keys: Vec<(String, i64)> = if use_fts {
        let batches: Vec<RecordBatch> = table
            .query()
            .full_text_search(FullTextSearchQuery::new(query.to_string()))
            .limit(limit)
            .execute()
            .await
            .context("FTS query failed")?
            .try_collect()
            .await
            .context("FTS collect failed")?;
        extract_source_chunk(&batches)
    } else {
        Vec::new()
    };

    // 2. ベクター検索
    let query_vec = model.embed(query);
    let vector_batches: Vec<RecordBatch> = table
        .vector_search(query_vec.as_slice())?
        .limit(limit)
        .execute()
        .await
        .context("vector query failed")?
        .try_collect()
        .await
        .context("vector collect failed")?;
    let vector_keys = extract_source_chunk(&vector_batches);

    // 3. RRF スコアリング
    let mut scores: HashMap<(String, i64), f64> = HashMap::new();
    let mut methods: HashMap<(String, i64), SearchMethod> = HashMap::new();

    for (rank, key) in fts_keys.into_iter().enumerate() {
        *scores.entry(key.clone()).or_default() += rrf_score(rank, rrf_k);
        methods.insert(key, SearchMethod::Keyword);
    }

    for (rank, key) in vector_keys.into_iter().enumerate() {
        *scores.entry(key.clone()).or_default() += rrf_score(rank, rrf_k);
        methods
            .entry(key)
            .and_modify(|m| *m = SearchMethod::Hybrid)
            .or_insert(SearchMethod::Semantic);
    }

    // 4. スコア降順ソート → 上位 limit 件に adjacent context を付与
    let mut sorted_keys: Vec<(String, i64)> = scores.keys().cloned().collect();
    sorted_keys.sort_by(|a, b| {
        scores[b]
            .partial_cmp(&scores[a])
            .unwrap_or(std::cmp::Ordering::Equal)
    });

    let mut results = Vec::new();
    for key in sorted_keys.into_iter().take(limit) {
        let text = get_adjacent_text(&table, &key.0, key.1, adjacent_window).await?;
        results.push(SearchResult {
            source: key.0.clone(),
            chunk_id: key.1,
            text,
            score: scores[&key],
            method: methods[&key].clone(),
        });
    }

    Ok(results)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rrf_score_formula() {
        // rank=0, k=60 → 1/(60+0+1) = 1/61
        let s = rrf_score(0, 60);
        assert!((s - 1.0 / 61.0).abs() < 1e-12);
    }

    #[test]
    fn rrf_score_decreases_with_rank() {
        assert!(rrf_score(0, 60) > rrf_score(1, 60));
        assert!(rrf_score(1, 60) > rrf_score(10, 60));
    }

    #[test]
    fn search_method_display() {
        assert_eq!(SearchMethod::Keyword.to_string(), "Keyword");
        assert_eq!(SearchMethod::Semantic.to_string(), "Semantic");
        assert_eq!(SearchMethod::Hybrid.to_string(), "Hybrid");
    }

    #[test]
    fn extract_source_chunk_empty() {
        let result = extract_source_chunk(&[]);
        assert!(result.is_empty());
    }
}
