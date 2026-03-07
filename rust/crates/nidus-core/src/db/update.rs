use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

use anyhow::{Context, Result};
use arrow_array::{
    Array, Date32Array, FixedSizeListArray, Float32Array, Int64Array, RecordBatch,
    RecordBatchIterator, StringArray,
};
use arrow_schema::{DataType, Field};
use lancedb::index::scalar::FtsIndexBuilder;
use lancedb::index::Index;
use lancedb::{Connection, Table};

use crate::db::connection::{
    doc_chunk_schema, doc_meta_schema, DEFAULT_TABLE_DOC_CHUNK, DEFAULT_TABLE_DOC_META,
};
use crate::embedding::{EmbeddingModel, VECTOR_SIZE};
use crate::processor::get_chunks;

const BATCH_SIZE: usize = 64;

/// ファイルの SHA-256 ハッシュを計算して16進文字列で返す。
///
/// 大きなファイルでもメモリ消費を抑えるためストリーミングで読み込む。
pub fn file_hash(path: &Path) -> Result<String> {
    use sha2::{Digest, Sha256};
    use std::io::{BufReader, Read};

    let file =
        std::fs::File::open(path).with_context(|| format!("cannot read {}", path.display()))?;
    let mut reader = BufReader::new(file);
    let mut hasher = Sha256::new();
    let mut buf = [0u8; 8192];
    loop {
        let n = reader
            .read(&mut buf)
            .with_context(|| format!("read error for {}", path.display()))?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    Ok(format!("{:x}", hasher.finalize()))
}

/// 現在の日付を Date32 値（Unix epoch からの日数）として返す。
fn today_date32() -> i32 {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    (secs / 86400) as i32
}

/// パスリストからサポート対象ファイルを再帰的に収集する。
///
/// ディレクトリは再帰的に展開し、非対応拡張子はスキップする。
pub fn collect_files(paths: &[PathBuf]) -> Vec<PathBuf> {
    const SUPPORTED: &[&str] = &[
        "md", "adoc", "txt", "pdf", "html", "htm", "docx", "csv", "tsv",
    ];

    fn supported(p: &Path) -> bool {
        p.extension()
            .and_then(|e| e.to_str())
            .map(|e| SUPPORTED.contains(&e.to_lowercase().as_str()))
            .unwrap_or(false)
    }

    fn walk(dir: &Path, out: &mut Vec<PathBuf>) {
        let Ok(entries) = std::fs::read_dir(dir) else {
            return;
        };
        let mut children: Vec<_> = entries.flatten().map(|e| e.path()).collect();
        children.sort();
        for p in children {
            if p.is_dir() {
                walk(&p, out);
            } else if p.is_file() && supported(&p) {
                out.push(p);
            }
        }
    }

    let mut result = Vec::new();
    for path in paths {
        if path.is_file() && supported(path) {
            result.push(path.clone());
        } else if path.is_dir() {
            walk(path, &mut result);
        }
    }
    result
}

/// テーブルが存在する場合はオープン、存在しない場合はスキーマで作成する。
async fn open_or_create(
    db: &Connection,
    name: &str,
    schema: Arc<arrow_schema::Schema>,
) -> Result<Table> {
    let existing = db
        .table_names()
        .execute()
        .await
        .context("failed to list table names")?;

    if existing.contains(&name.to_string()) {
        db.open_table(name)
            .execute()
            .await
            .with_context(|| format!("failed to open table: {name}"))
    } else {
        let empty: Vec<std::result::Result<RecordBatch, arrow_schema::ArrowError>> = vec![];
        db.create_table(name, RecordBatchIterator::new(empty.into_iter(), schema))
            .execute()
            .await
            .with_context(|| format!("failed to create table: {name}"))
    }
}

/// バッファのチャンクレコードを doc_chunk テーブルに書き込む。
///
/// 書き込み後にバッファはクリアされる。
async fn flush_chunks(
    buffer: &mut Vec<(String, String, Vec<f32>, i64, String)>,
    table: &Table,
    schema: Arc<arrow_schema::Schema>,
) -> Result<()> {
    if buffer.is_empty() {
        return Ok(());
    }

    let n = buffer.len();
    let mut sources = Vec::with_capacity(n);
    let mut doc_names = Vec::with_capacity(n);
    let mut flat_vectors: Vec<f32> = Vec::with_capacity(n * VECTOR_SIZE);
    let mut chunk_ids: Vec<i64> = Vec::with_capacity(n);
    let mut chunk_texts = Vec::with_capacity(n);

    for (source, doc_name, vector, chunk_id, chunk_text) in buffer.drain(..) {
        sources.push(source);
        doc_names.push(doc_name);
        flat_vectors.extend(vector);
        chunk_ids.push(chunk_id);
        chunk_texts.push(chunk_text);
    }

    let values = Arc::new(Float32Array::from(flat_vectors));
    let item_field = Arc::new(Field::new("item", DataType::Float32, true));
    let list_array = FixedSizeListArray::new(item_field, VECTOR_SIZE as i32, values, None);

    let batch = RecordBatch::try_new(
        schema.clone(),
        vec![
            Arc::new(StringArray::from(sources)) as Arc<dyn Array>,
            Arc::new(StringArray::from(doc_names)) as Arc<dyn Array>,
            Arc::new(list_array) as Arc<dyn Array>,
            Arc::new(Int64Array::from(chunk_ids)) as Arc<dyn Array>,
            Arc::new(StringArray::from(chunk_texts)) as Arc<dyn Array>,
        ],
    )
    .context("failed to build doc_chunk batch")?;

    table
        .add(RecordBatchIterator::new(
            vec![Ok(batch)].into_iter(),
            schema,
        ))
        .execute()
        .await
        .context("failed to add doc_chunk records")?;

    Ok(())
}

/// `doc_chunk` テーブルの `chunk_text` 列に FTS インデックスを作成する（バイグラム）。
async fn create_chunk_fts_index(table: &Table) -> Result<()> {
    table
        .create_index(&["chunk_text"], Index::FTS(FtsIndexBuilder::default()))
        .replace(true)
        .execute()
        .await
        .context("failed to create FTS index on chunk_text")?;
    Ok(())
}

/// ファイルリストを全インデックス化する（差分なし）。
///
/// - テーブルが未存在なら作成、存在すればオープンして追記
/// - ファイルをチャンク化し embedding を生成して `doc_chunk` に書き込む
/// - `doc_meta` にメタデータを書き込む
/// - FTS インデックスを再構築する
pub async fn update_files_in_db(
    paths: &[PathBuf],
    db: &Connection,
    model: &EmbeddingModel,
) -> Result<()> {
    let doc_meta_table = open_or_create(db, DEFAULT_TABLE_DOC_META, doc_meta_schema()).await?;
    let doc_chunk_table = open_or_create(db, DEFAULT_TABLE_DOC_CHUNK, doc_chunk_schema()).await?;

    let files = collect_files(paths);
    if files.is_empty() {
        eprintln!("No valid files found.");
        return Ok(());
    }
    eprintln!("Indexing {} file(s)...", files.len());

    let today = today_date32();

    // doc_meta 一括書き込み
    {
        let n = files.len();
        let sources: Vec<String> = files
            .iter()
            .map(|p| p.to_string_lossy().into_owned())
            .collect();
        let doc_names: Vec<String> = files
            .iter()
            .map(|p| {
                p.file_name()
                    .map(|n| n.to_string_lossy().into_owned())
                    .unwrap_or_default()
            })
            .collect();
        let hashes: Vec<String> = files
            .iter()
            .map(|p| {
                file_hash(p).unwrap_or_else(|e| {
                    eprintln!("WARN: hash failed for {}: {e}", p.display());
                    String::new()
                })
            })
            .collect();

        let schema = doc_meta_schema();
        let batch = RecordBatch::try_new(
            schema.clone(),
            vec![
                Arc::new(StringArray::from(sources)) as Arc<dyn Array>,
                Arc::new(StringArray::from(doc_names)) as Arc<dyn Array>,
                Arc::new(Date32Array::from(vec![today; n])) as Arc<dyn Array>,
                Arc::new(Date32Array::from(vec![today; n])) as Arc<dyn Array>,
                Arc::new(StringArray::from(hashes)) as Arc<dyn Array>,
            ],
        )
        .context("failed to build doc_meta batch")?;

        doc_meta_table
            .add(RecordBatchIterator::new(
                vec![Ok(batch)].into_iter(),
                schema,
            ))
            .execute()
            .await
            .context("failed to add doc_meta records")?;
    }

    // doc_chunk 書き込み（バッチ処理）
    let chunk_schema = doc_chunk_schema();
    let mut buffer: Vec<(String, String, Vec<f32>, i64, String)> = Vec::with_capacity(BATCH_SIZE);

    for path in &files {
        let source = path.to_string_lossy().into_owned();
        let doc_name = path
            .file_name()
            .map(|n| n.to_string_lossy().into_owned())
            .unwrap_or_default();

        let Some(chunks) = get_chunks(path) else {
            eprintln!("[Skip] {}", path.display());
            continue;
        };
        eprintln!("  {} ({} chunks)", doc_name, chunks.len());

        for (i, chunk) in chunks.iter().enumerate() {
            let vector = model.embed(chunk);
            buffer.push((
                source.clone(),
                doc_name.clone(),
                vector,
                i as i64,
                chunk.clone(),
            ));

            if buffer.len() >= BATCH_SIZE {
                flush_chunks(&mut buffer, &doc_chunk_table, chunk_schema.clone()).await?;
            }
        }
    }
    flush_chunks(&mut buffer, &doc_chunk_table, chunk_schema).await?;

    create_chunk_fts_index(&doc_chunk_table).await?;
    eprintln!("Indexing complete.");

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn collect_files_single_file() {
        let tmp = tempfile::tempdir().unwrap();
        let f = tmp.path().join("test.md");
        std::fs::write(&f, b"# hello").unwrap();

        let result = collect_files(&[f.clone()]);
        assert_eq!(result, vec![f]);
    }

    #[test]
    fn collect_files_unsupported_ext_excluded() {
        let tmp = tempfile::tempdir().unwrap();
        let f = tmp.path().join("binary.exe");
        std::fs::write(&f, b"not a doc").unwrap();

        let result = collect_files(&[f]);
        assert!(result.is_empty());
    }

    #[test]
    fn collect_files_directory_recursive() {
        let tmp = tempfile::tempdir().unwrap();
        let sub = tmp.path().join("sub");
        std::fs::create_dir(&sub).unwrap();
        std::fs::write(tmp.path().join("a.md"), b"# a").unwrap();
        std::fs::write(sub.join("b.txt"), b"b").unwrap();
        std::fs::write(tmp.path().join("c.exe"), b"c").unwrap();

        let result = collect_files(&[tmp.path().to_path_buf()]);
        let names: Vec<&str> = result
            .iter()
            .map(|p| p.file_name().unwrap().to_str().unwrap())
            .collect();
        assert!(names.contains(&"a.md"));
        assert!(names.contains(&"b.txt"));
        assert!(!names.contains(&"c.exe"));
    }

    #[test]
    fn file_hash_is_deterministic_and_correct_length() {
        let tmp = tempfile::tempdir().unwrap();
        let f = tmp.path().join("test.txt");
        std::fs::write(&f, b"hello world").unwrap();

        let h1 = file_hash(&f).unwrap();
        let h2 = file_hash(&f).unwrap();
        assert_eq!(h1, h2);
        assert_eq!(h1.len(), 64); // SHA-256 = 32 bytes = 64 hex chars
    }

    #[test]
    fn file_hash_differs_for_different_content() {
        let tmp = tempfile::tempdir().unwrap();
        let f1 = tmp.path().join("a.txt");
        let f2 = tmp.path().join("b.txt");
        std::fs::write(&f1, b"hello").unwrap();
        std::fs::write(&f2, b"world").unwrap();

        assert_ne!(file_hash(&f1).unwrap(), file_hash(&f2).unwrap());
    }

    #[test]
    fn today_date32_is_plausible() {
        let d = today_date32();
        // 2020-01-01 = day 18262 since epoch
        assert!(d > 18_000, "expected date after 2019, got {d}");
    }

    #[tokio::test]
    async fn open_or_create_creates_then_opens() {
        let tmp = tempfile::tempdir().unwrap();
        let db_path = tmp.path().join(".lancedb");
        let db = crate::db::connect(&db_path).await.unwrap();
        let schema = doc_meta_schema();

        // 1回目: 作成
        let t1 = open_or_create(&db, "test_meta", schema.clone()).await;
        assert!(t1.is_ok(), "create failed: {:?}", t1.err());

        // 2回目: 既存テーブルをオープン
        let t2 = open_or_create(&db, "test_meta", schema).await;
        assert!(t2.is_ok(), "open failed: {:?}", t2.err());
    }

    #[tokio::test]
    async fn flush_chunks_empty_buffer_is_noop() {
        let tmp = tempfile::tempdir().unwrap();
        let db = crate::db::connect(&tmp.path().join(".lancedb"))
            .await
            .unwrap();
        let table = open_or_create(&db, "doc_chunk", doc_chunk_schema())
            .await
            .unwrap();

        let mut buffer: Vec<(String, String, Vec<f32>, i64, String)> = vec![];
        let result = flush_chunks(&mut buffer, &table, doc_chunk_schema()).await;

        assert!(result.is_ok());
        // バッファが空のまま（書き込みが発生していない）
        assert!(buffer.is_empty());
        assert_eq!(table.count_rows(None).await.unwrap(), 0);
    }

    #[tokio::test]
    async fn flush_chunks_writes_records_and_clears_buffer() {
        let tmp = tempfile::tempdir().unwrap();
        let db = crate::db::connect(&tmp.path().join(".lancedb"))
            .await
            .unwrap();
        let table = open_or_create(&db, "doc_chunk", doc_chunk_schema())
            .await
            .unwrap();

        let vector = vec![0.0f32; VECTOR_SIZE];
        let mut buffer = vec![
            (
                "path/a.md".to_string(),
                "a.md".to_string(),
                vector.clone(),
                0i64,
                "first chunk".to_string(),
            ),
            (
                "path/a.md".to_string(),
                "a.md".to_string(),
                vector.clone(),
                1i64,
                "second chunk".to_string(),
            ),
        ];

        let result = flush_chunks(&mut buffer, &table, doc_chunk_schema()).await;

        assert!(result.is_ok());
        // flush 後にバッファがクリアされている
        assert!(buffer.is_empty());
        // テーブルに2件書き込まれている
        assert_eq!(table.count_rows(None).await.unwrap(), 2);
    }
}
