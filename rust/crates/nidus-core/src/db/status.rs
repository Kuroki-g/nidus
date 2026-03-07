use anyhow::{Context, Result};
use lancedb::Connection;

/// 1 テーブル分のメタ情報。
#[derive(Debug, Clone)]
pub struct TableInfo {
    pub name: String,
    pub row_count: usize,
    pub fields: Vec<String>,
    pub version: u64,
}

/// DB 全体のメタ情報。
#[derive(Debug, Clone)]
pub struct DbStatus {
    pub db_path: String,
    pub tables: Vec<TableInfo>,
}

/// DB の各テーブルの行数・スキーマ・バージョンを収集して返す。
pub async fn db_status(db: &Connection, db_path: &str) -> Result<DbStatus> {
    let table_names = db
        .table_names()
        .execute()
        .await
        .context("failed to list table names")?;

    let mut tables = Vec::new();
    for name in &table_names {
        let table = db
            .open_table(name)
            .execute()
            .await
            .with_context(|| format!("failed to open table: {name}"))?;

        let row_count = table
            .count_rows(None)
            .await
            .with_context(|| format!("failed to count rows in {name}"))?;

        let schema = table.schema().await.with_context(|| format!("failed to get schema for {name}"))?;
        let fields: Vec<String> = schema.fields().iter().map(|f| f.name().to_string()).collect();

        let version = table.version().await.with_context(|| format!("failed to get version for {name}"))?;

        tables.push(TableInfo {
            name: name.clone(),
            row_count,
            fields,
            version,
        });
    }

    Ok(DbStatus {
        db_path: db_path.to_string(),
        tables,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn db_status_empty_db() {
        let tmp = tempfile::tempdir().unwrap();
        let db_path = tmp.path().join(".lancedb");
        let db = crate::db::connect(&db_path).await.unwrap();

        let status = db_status(&db, db_path.to_str().unwrap()).await.unwrap();
        assert!(status.tables.is_empty());
        assert!(status.db_path.contains(".lancedb"));
    }

    #[tokio::test]
    async fn db_status_shows_table_info() {
        use arrow_array::{RecordBatch, RecordBatchIterator};

        use crate::db::connection::{doc_meta_schema, DEFAULT_TABLE_DOC_META};

        let tmp = tempfile::tempdir().unwrap();
        let db_path = tmp.path().join(".lancedb");
        let db = crate::db::connect(&db_path).await.unwrap();

        // テーブルを作成
        let schema = doc_meta_schema();
        let empty: Vec<std::result::Result<RecordBatch, arrow_schema::ArrowError>> = vec![];
        db.create_table(
            DEFAULT_TABLE_DOC_META,
            RecordBatchIterator::new(empty.into_iter(), schema),
        )
        .execute()
        .await
        .unwrap();

        let status = db_status(&db, db_path.to_str().unwrap()).await.unwrap();
        assert_eq!(status.tables.len(), 1);

        let t = &status.tables[0];
        assert_eq!(t.name, DEFAULT_TABLE_DOC_META);
        assert_eq!(t.row_count, 0);
        assert!(t.fields.contains(&"source".to_string()));
    }
}
