use std::path::PathBuf;

use anyhow::{Context, Result};
use arrow_array::StringArray;
use futures::TryStreamExt;
use lancedb::query::{ExecutableQuery, QueryBase};
use lancedb::Connection;

use crate::db::connection::{DEFAULT_TABLE_DOC_CHUNK, DEFAULT_TABLE_DOC_META};
use crate::db::update::update_files_in_db;
use crate::embedding::EmbeddingModel;

/// `doc_meta` テーブルから登録済みの全 source パスを収集する。
///
/// テーブルが存在しない場合は空ベクタを返す。
async fn collect_all_sources(db: &Connection) -> Result<Vec<String>> {
    let table_names = db
        .table_names()
        .execute()
        .await
        .context("failed to list table names")?;

    if !table_names.contains(&DEFAULT_TABLE_DOC_META.to_string()) {
        return Ok(vec![]);
    }

    let table = db
        .open_table(DEFAULT_TABLE_DOC_META)
        .execute()
        .await
        .context("failed to open doc_meta")?;

    let batches: Vec<arrow_array::RecordBatch> = table
        .query()
        .select(lancedb::query::Select::Columns(vec!["source".to_string()]))
        .execute()
        .await
        .context("failed to query doc_meta for sources")?
        .try_collect()
        .await
        .context("failed to collect doc_meta stream")?;

    let mut sources = Vec::new();
    for batch in &batches {
        let col = batch
            .column_by_name("source")
            .context("doc_meta: column 'source' not found")?
            .as_any()
            .downcast_ref::<StringArray>()
            .context("doc_meta: 'source' is not StringArray")?;
        for i in 0..batch.num_rows() {
            sources.push(col.value(i).to_string());
        }
    }

    Ok(sources)
}

/// 両テーブルの全レコードを削除する。
///
/// テーブルが存在しない場合はスキップする。
async fn truncate_tables(db: &Connection) -> Result<()> {
    let table_names = db
        .table_names()
        .execute()
        .await
        .context("failed to list table names")?;

    for table_name in [DEFAULT_TABLE_DOC_META, DEFAULT_TABLE_DOC_CHUNK] {
        if !table_names.contains(&table_name.to_string()) {
            continue;
        }
        let table = db
            .open_table(table_name)
            .execute()
            .await
            .with_context(|| format!("failed to open table: {table_name}"))?;
        table
            .delete("true")
            .await
            .with_context(|| format!("failed to truncate table: {table_name}"))?;
    }

    Ok(())
}

/// DB に登録済みのすべてのドキュメントをゼロから再インデックス化する。
///
/// 1. `doc_meta` から全 source パスを収集する。
/// 2. `dry_run = true` の場合は対象ファイルを表示するだけで終了。
/// 3. 両テーブルの全レコードを削除してから `update_files_in_db` で再投入する。
///
/// `dry_run = false` のときは `model` が必要。`None` を渡すとエラーを返す。
///
/// Returns: 再インデックス対象ファイル数（dry_run でも同様）。
pub async fn reindex_db(
    db: &Connection,
    model: Option<&EmbeddingModel>,
    dry_run: bool,
) -> Result<usize> {
    let sources = collect_all_sources(db).await?;

    if sources.is_empty() {
        tracing::info!("No documents registered. Nothing to reindex.");
        return Ok(0);
    }

    tracing::info!("{} document(s) to reindex:", sources.len());
    for s in &sources {
        tracing::info!("  {s}");
    }

    if dry_run {
        tracing::info!("(dry-run: no changes made)");
        return Ok(sources.len());
    }

    let model = model.context("EmbeddingModel is required for reindex (not dry-run)")?;

    truncate_tables(db).await?;

    let paths: Vec<PathBuf> = sources.iter().map(PathBuf::from).collect();
    update_files_in_db(&paths, db, model).await?;

    Ok(sources.len())
}

#[cfg(test)]
mod tests {
    use std::sync::Arc;

    use arrow_array::{Date32Array, RecordBatch, RecordBatchIterator, StringArray};

    use super::*;
    use crate::db::connection::{doc_chunk_schema, doc_meta_schema};

    /// テーブルが存在しない空の DB では collect_all_sources は空ベクタを返す。
    #[tokio::test]
    async fn collect_all_sources_empty_db() {
        let tmp = tempfile::tempdir().unwrap();
        let db = crate::db::connect(&tmp.path().join(".lancedb"))
            .await
            .unwrap();

        let sources = collect_all_sources(&db).await.unwrap();
        assert!(sources.is_empty());
    }

    /// doc_meta にレコードがある場合、collect_all_sources は全 source を返す。
    #[tokio::test]
    async fn collect_all_sources_returns_registered_paths() {
        let tmp = tempfile::tempdir().unwrap();
        let db = crate::db::connect(&tmp.path().join(".lancedb"))
            .await
            .unwrap();

        let schema = doc_meta_schema();
        let batch = RecordBatch::try_new(
            schema.clone(),
            vec![
                Arc::new(StringArray::from(vec!["/docs/a.md", "/docs/b.txt"]))
                    as Arc<dyn arrow_array::Array>,
                Arc::new(StringArray::from(vec!["a.md", "b.txt"])) as Arc<dyn arrow_array::Array>,
                Arc::new(Date32Array::from(vec![19000i32, 19000i32]))
                    as Arc<dyn arrow_array::Array>,
                Arc::new(Date32Array::from(vec![19000i32, 19000i32]))
                    as Arc<dyn arrow_array::Array>,
                Arc::new(StringArray::from(vec!["hash1", "hash2"])) as Arc<dyn arrow_array::Array>,
            ],
        )
        .unwrap();

        db.create_table(
            DEFAULT_TABLE_DOC_META,
            RecordBatchIterator::new(vec![Ok(batch)].into_iter(), schema),
        )
        .execute()
        .await
        .unwrap();

        let mut sources = collect_all_sources(&db).await.unwrap();
        sources.sort();
        assert_eq!(sources, vec!["/docs/a.md", "/docs/b.txt"]);
    }

    /// truncate_tables はテーブルが存在しない場合もエラーにならない。
    #[tokio::test]
    async fn truncate_tables_no_tables_is_noop() {
        let tmp = tempfile::tempdir().unwrap();
        let db = crate::db::connect(&tmp.path().join(".lancedb"))
            .await
            .unwrap();

        let result = truncate_tables(&db).await;
        assert!(result.is_ok());
    }

    /// truncate_tables は両テーブルの全レコードを削除する。
    #[tokio::test]
    async fn truncate_tables_clears_all_records() {
        let tmp = tempfile::tempdir().unwrap();
        let db = crate::db::connect(&tmp.path().join(".lancedb"))
            .await
            .unwrap();

        // doc_meta にレコードを追加
        let schema = doc_meta_schema();
        let batch = RecordBatch::try_new(
            schema.clone(),
            vec![
                Arc::new(StringArray::from(vec!["/docs/a.md"])) as Arc<dyn arrow_array::Array>,
                Arc::new(StringArray::from(vec!["a.md"])) as Arc<dyn arrow_array::Array>,
                Arc::new(Date32Array::from(vec![19000i32])) as Arc<dyn arrow_array::Array>,
                Arc::new(Date32Array::from(vec![19000i32])) as Arc<dyn arrow_array::Array>,
                Arc::new(StringArray::from(vec!["hash1"])) as Arc<dyn arrow_array::Array>,
            ],
        )
        .unwrap();

        db.create_table(
            DEFAULT_TABLE_DOC_META,
            RecordBatchIterator::new(vec![Ok(batch)].into_iter(), schema),
        )
        .execute()
        .await
        .unwrap();

        // doc_chunk にレコードを追加
        let chunk_schema = doc_chunk_schema();
        let empty: Vec<std::result::Result<RecordBatch, arrow_schema::ArrowError>> = vec![];
        db.create_table(
            DEFAULT_TABLE_DOC_CHUNK,
            RecordBatchIterator::new(empty.into_iter(), chunk_schema),
        )
        .execute()
        .await
        .unwrap();

        truncate_tables(&db).await.unwrap();

        let meta_table = db
            .open_table(DEFAULT_TABLE_DOC_META)
            .execute()
            .await
            .unwrap();
        assert_eq!(meta_table.count_rows(None).await.unwrap(), 0);

        let chunk_table = db
            .open_table(DEFAULT_TABLE_DOC_CHUNK)
            .execute()
            .await
            .unwrap();
        assert_eq!(chunk_table.count_rows(None).await.unwrap(), 0);
    }

    /// reindex_db は DB が空のとき 0 を返す。
    #[tokio::test]
    async fn reindex_db_empty_db_returns_zero() {
        let tmp = tempfile::tempdir().unwrap();
        let db = crate::db::connect(&tmp.path().join(".lancedb"))
            .await
            .unwrap();

        let count = reindex_db(&db, None, true).await.unwrap();
        assert_eq!(count, 0);
    }

    /// reindex_db は dry_run=true のとき DB を変更しない。
    #[tokio::test]
    async fn reindex_db_dry_run_does_not_modify() {
        let tmp = tempfile::tempdir().unwrap();
        let db = crate::db::connect(&tmp.path().join(".lancedb"))
            .await
            .unwrap();

        // doc_meta に 1 件登録
        let schema = doc_meta_schema();
        let batch = RecordBatch::try_new(
            schema.clone(),
            vec![
                Arc::new(StringArray::from(vec!["/docs/a.md"])) as Arc<dyn arrow_array::Array>,
                Arc::new(StringArray::from(vec!["a.md"])) as Arc<dyn arrow_array::Array>,
                Arc::new(Date32Array::from(vec![19000i32])) as Arc<dyn arrow_array::Array>,
                Arc::new(Date32Array::from(vec![19000i32])) as Arc<dyn arrow_array::Array>,
                Arc::new(StringArray::from(vec!["hash1"])) as Arc<dyn arrow_array::Array>,
            ],
        )
        .unwrap();

        db.create_table(
            DEFAULT_TABLE_DOC_META,
            RecordBatchIterator::new(vec![Ok(batch)].into_iter(), schema),
        )
        .execute()
        .await
        .unwrap();

        let count = reindex_db(&db, None, true).await.unwrap();
        assert_eq!(count, 1);

        // dry_run なので doc_meta のレコードはそのまま
        let table = db
            .open_table(DEFAULT_TABLE_DOC_META)
            .execute()
            .await
            .unwrap();
        assert_eq!(table.count_rows(None).await.unwrap(), 1);
    }
}
