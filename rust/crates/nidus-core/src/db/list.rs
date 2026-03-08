use anyhow::{Context, Result};
use arrow_array::StringArray;
use futures_util::TryStreamExt;
use lancedb::query::{ExecutableQuery, QueryBase};
use lancedb::Connection;

use crate::db::connection::DEFAULT_TABLE_DOC_META;

/// `doc_meta` テーブルから取得するドキュメント一覧エントリ。
#[derive(Debug, Clone)]
pub struct DocListEntry {
    pub source: String,
    pub doc_name: String,
}

/// DB に登録されているドキュメントを一覧する。
///
/// `keyword` を指定すると `source` パスが部分一致するものだけに絞り込む。
/// テーブルが存在しない場合は空リストを返す。
pub async fn list_docs_in_db(
    db: &Connection,
    keyword: Option<&str>,
    limit: usize,
) -> Result<Vec<DocListEntry>> {
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

    let mut q = table
        .query()
        .select(lancedb::query::Select::Columns(vec![
            "source".to_string(),
            "doc_name".to_string(),
        ]))
        .limit(limit * 10);

    if let Some(kw) = keyword {
        let escaped = kw.replace('\'', "''");
        q = q.only_if(format!("source LIKE '%{escaped}%'"));
    }

    let batches: Vec<arrow_array::RecordBatch> = q
        .execute()
        .await
        .context("failed to execute list query")?
        .try_collect()
        .await
        .context("failed to collect list results")?;

    let mut entries = Vec::new();
    for batch in &batches {
        let sources = batch
            .column_by_name("source")
            .context("doc_meta: column 'source' not found")?
            .as_any()
            .downcast_ref::<StringArray>()
            .context("doc_meta: 'source' is not StringArray")?;
        let doc_names = batch
            .column_by_name("doc_name")
            .context("doc_meta: column 'doc_name' not found")?
            .as_any()
            .downcast_ref::<StringArray>()
            .context("doc_meta: 'doc_name' is not StringArray")?;

        for i in 0..batch.num_rows() {
            entries.push(DocListEntry {
                source: sources.value(i).to_string(),
                doc_name: doc_names.value(i).to_string(),
            });
        }
    }

    Ok(entries)
}

#[cfg(test)]
mod tests {
    use std::sync::Arc;

    use arrow_array::{Date32Array, RecordBatch, RecordBatchIterator};

    use super::*;
    use crate::db::connection::doc_meta_schema;

    async fn insert_docs(db: &Connection, sources: &[&str], doc_names: &[&str]) {
        let schema = doc_meta_schema();
        let n = sources.len();

        // テーブルを作成または開く
        let existing = db.table_names().execute().await.unwrap();
        let table = if existing.contains(&DEFAULT_TABLE_DOC_META.to_string()) {
            db.open_table(DEFAULT_TABLE_DOC_META)
                .execute()
                .await
                .unwrap()
        } else {
            let empty: Vec<std::result::Result<RecordBatch, arrow_schema::ArrowError>> = vec![];
            db.create_table(
                DEFAULT_TABLE_DOC_META,
                RecordBatchIterator::new(empty.into_iter(), schema.clone()),
            )
            .execute()
            .await
            .unwrap()
        };

        let batch = RecordBatch::try_new(
            schema.clone(),
            vec![
                Arc::new(StringArray::from(sources.to_vec())) as Arc<dyn arrow_array::Array>,
                Arc::new(StringArray::from(doc_names.to_vec())) as Arc<dyn arrow_array::Array>,
                Arc::new(Date32Array::from(vec![19000i32; n])) as Arc<dyn arrow_array::Array>,
                Arc::new(Date32Array::from(vec![19000i32; n])) as Arc<dyn arrow_array::Array>,
                Arc::new(StringArray::from(vec!["hash"; n])) as Arc<dyn arrow_array::Array>,
            ],
        )
        .unwrap();

        table
            .add(RecordBatchIterator::new(
                vec![Ok(batch)].into_iter(),
                schema,
            ))
            .execute()
            .await
            .unwrap();
    }

    #[tokio::test]
    async fn list_docs_no_table_returns_empty() {
        let tmp = tempfile::tempdir().unwrap();
        let db = crate::db::connect(&tmp.path().join(".lancedb"))
            .await
            .unwrap();

        let result = list_docs_in_db(&db, None, 5).await.unwrap();
        assert!(result.is_empty());
    }

    #[tokio::test]
    async fn list_docs_returns_all_when_no_keyword() {
        let tmp = tempfile::tempdir().unwrap();
        let db = crate::db::connect(&tmp.path().join(".lancedb"))
            .await
            .unwrap();

        insert_docs(&db, &["/docs/a.md", "/docs/b.md"], &["a.md", "b.md"]).await;

        let result = list_docs_in_db(&db, None, 5).await.unwrap();
        assert_eq!(result.len(), 2);
    }

    #[tokio::test]
    async fn list_docs_filters_by_keyword() {
        let tmp = tempfile::tempdir().unwrap();
        let db = crate::db::connect(&tmp.path().join(".lancedb"))
            .await
            .unwrap();

        insert_docs(
            &db,
            &["/docs/alpha.md", "/docs/beta.md", "/notes/alpha.txt"],
            &["alpha.md", "beta.md", "alpha.txt"],
        )
        .await;

        let result = list_docs_in_db(&db, Some("alpha"), 5).await.unwrap();
        assert_eq!(result.len(), 2);
        assert!(result.iter().all(|e| e.source.contains("alpha")));
    }
}
