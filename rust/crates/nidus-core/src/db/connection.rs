use std::path::Path;
use std::sync::Arc;

use anyhow::{Context, Result};
use arrow_schema::{DataType, Field, Schema};
use lancedb::Connection;

use crate::embedding::VECTOR_SIZE;

/// doc_chunk テーブル名のデフォルト値。
pub const DEFAULT_TABLE_DOC_CHUNK: &str = "doc_chunk";
/// doc_meta テーブル名のデフォルト値。
pub const DEFAULT_TABLE_DOC_META: &str = "doc_meta";

/// LanceDB への非同期接続を開く。
///
/// `db_path` が存在しない場合は自動的に作成する。
pub async fn connect(db_path: &Path) -> Result<Connection> {
    if let Some(parent) = db_path.parent() {
        std::fs::create_dir_all(parent)
            .with_context(|| format!("failed to create directory: {}", parent.display()))?;
    }

    let path_str = db_path
        .to_str()
        .with_context(|| format!("invalid db_path (non-UTF-8): {}", db_path.display()))?;

    lancedb::connect(path_str)
        .execute()
        .await
        .with_context(|| format!("failed to connect to LanceDB at {}", db_path.display()))
}

/// doc_chunk テーブルの Arrow スキーマ。
///
/// | フィールド | 型             | 説明                         |
/// |------------|----------------|------------------------------|
/// | source     | Utf8           | ファイルパス（主キー相当）   |
/// | doc_name   | Utf8           | ドキュメント名               |
/// | vector     | FixedSizeList  | 1024 次元 f32 埋め込みベクター |
/// | chunk_id   | Int64          | チャンク通し番号             |
/// | chunk_text | Utf8           | チャンクのテキスト本文       |
pub fn doc_chunk_schema() -> Arc<Schema> {
    Arc::new(Schema::new(vec![
        Field::new("source", DataType::Utf8, false),
        Field::new("doc_name", DataType::Utf8, false),
        Field::new(
            "vector",
            DataType::FixedSizeList(
                Arc::new(Field::new("item", DataType::Float32, true)),
                VECTOR_SIZE as i32,
            ),
            false,
        ),
        Field::new("chunk_id", DataType::Int64, false),
        Field::new("chunk_text", DataType::Utf8, false),
    ]))
}

/// doc_meta テーブルの Arrow スキーマ。
///
/// | フィールド | 型     | 説明                        |
/// |------------|--------|-----------------------------|
/// | source     | Utf8   | ファイルパス（主キー相当）  |
/// | doc_name   | Utf8   | ドキュメント名              |
/// | created    | Date32 | 初回登録日                  |
/// | updated    | Date32 | 最終更新日                  |
/// | file_hash  | Utf8   | SHA-256 ハッシュ値          |
pub fn doc_meta_schema() -> Arc<Schema> {
    Arc::new(Schema::new(vec![
        Field::new("source", DataType::Utf8, false),
        Field::new("doc_name", DataType::Utf8, false),
        Field::new("created", DataType::Date32, false),
        Field::new("updated", DataType::Date32, false),
        Field::new("file_hash", DataType::Utf8, false),
    ]))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn doc_chunk_schema_has_correct_fields() {
        let schema = doc_chunk_schema();
        let names: Vec<&str> = schema.fields().iter().map(|f| f.name().as_str()).collect();
        assert_eq!(
            names,
            ["source", "doc_name", "vector", "chunk_id", "chunk_text"]
        );

        // vector フィールドが FixedSizeList(Float32, 1024) であることを確認
        let vector_field = schema.field_with_name("vector").unwrap();
        match vector_field.data_type() {
            DataType::FixedSizeList(item_field, size) => {
                assert_eq!(*size, VECTOR_SIZE as i32);
                assert_eq!(item_field.data_type(), &DataType::Float32);
            }
            other => panic!("unexpected vector dtype: {other:?}"),
        }
    }

    #[test]
    fn doc_meta_schema_has_correct_fields() {
        let schema = doc_meta_schema();
        let names: Vec<&str> = schema.fields().iter().map(|f| f.name().as_str()).collect();
        assert_eq!(
            names,
            ["source", "doc_name", "created", "updated", "file_hash"]
        );

        assert_eq!(
            schema.field_with_name("created").unwrap().data_type(),
            &DataType::Date32
        );
        assert_eq!(
            schema.field_with_name("updated").unwrap().data_type(),
            &DataType::Date32
        );
    }

    /// 一時ディレクトリへの実際の接続テスト（ファイル I/O あり）。
    #[tokio::test]
    async fn connect_creates_db_directory() {
        let tmp = tempfile::tempdir().unwrap();
        let db_path = tmp.path().join("sub").join(".lancedb");

        let conn = connect(&db_path).await;
        assert!(conn.is_ok(), "connect failed: {:?}", conn.err());
        // 接続後にパスが存在することを確認
        assert!(db_path.exists() || db_path.parent().unwrap().exists());
    }
}
