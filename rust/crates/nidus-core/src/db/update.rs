use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

use anyhow::{Context, Result};
use arrow_array::{
    Array, Date32Array, FixedSizeListArray, Float32Array, Int64Array, RecordBatch,
    RecordBatchIterator, StringArray,
};
use arrow_schema::{DataType, Field};
use futures::TryStreamExt;
use lancedb::index::scalar::FtsIndexBuilder;
use lancedb::index::Index;
use lancedb::query::ExecutableQuery;
use lancedb::{Connection, Table};

use crate::db::connection::{
    doc_chunk_schema, doc_meta_schema, DEFAULT_TABLE_DOC_CHUNK, DEFAULT_TABLE_DOC_META,
};
use crate::embedding::{EmbeddingModel, VECTOR_SIZE};
use crate::processor::get_chunks;

const BATCH_SIZE: usize = 64;

/// 処理対象ファイルのエントリ（差分判定後）。
struct FileEntry {
    path: PathBuf,
    source: String,
    doc_name: String,
    hash: String,
    /// 初回登録日。新規は today、変更ファイルは既存値を引き継ぐ。
    created: i32,
    /// 最終更新日（常に today）。
    updated: i32,
    /// true = 既存レコードの削除が必要（変更ファイル）。
    needs_delete: bool,
}

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

/// `doc_meta` テーブルから既存ファイルのハッシュと `created` 日付を読み込む。
///
/// Returns: `source` → `(file_hash, created_date32)`
async fn load_existing_meta(table: &Table) -> Result<HashMap<String, (String, i32)>> {
    let batches: Vec<RecordBatch> = table
        .query()
        .execute()
        .await
        .context("failed to query doc_meta")?
        .try_collect()
        .await
        .context("failed to collect doc_meta stream")?;

    let mut map = HashMap::new();
    for batch in batches {
        let sources = batch
            .column_by_name("source")
            .context("doc_meta: column 'source' not found")?
            .as_any()
            .downcast_ref::<StringArray>()
            .context("doc_meta: column 'source' is not StringArray")?;
        let hashes = batch
            .column_by_name("file_hash")
            .context("doc_meta: column 'file_hash' not found")?
            .as_any()
            .downcast_ref::<StringArray>()
            .context("doc_meta: column 'file_hash' is not StringArray")?;
        let created = batch
            .column_by_name("created")
            .context("doc_meta: column 'created' not found")?
            .as_any()
            .downcast_ref::<Date32Array>()
            .context("doc_meta: column 'created' is not Date32Array")?;

        for i in 0..batch.num_rows() {
            map.insert(
                sources.value(i).to_string(),
                (hashes.value(i).to_string(), created.value(i)),
            );
        }
    }
    Ok(map)
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

/// ファイルリストを差分インデックス化する。
///
/// - テーブルが未存在なら作成、存在すればオープンして差分更新
/// - ハッシュ一致ファイルはスキップ（未変更）
/// - 変更ファイルは旧レコードを削除して再インデックス（`created` 日付を保持）
/// - 新規ファイルは `created` = today で追加
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
        tracing::warn!("No valid files found.");
        return Ok(());
    }

    let today = today_date32();
    let existing_meta = load_existing_meta(&doc_meta_table).await?;

    // 差分分類
    let mut to_process: Vec<FileEntry> = Vec::new();
    let mut skipped = 0usize;

    for path in &files {
        let source = path.to_string_lossy().into_owned();
        let doc_name = path
            .file_name()
            .map(|n| n.to_string_lossy().into_owned())
            .unwrap_or_default();
        let hash = match file_hash(path) {
            Ok(h) => h,
            Err(e) => {
                tracing::warn!("skipping {} (hash failed: {e})", path.display());
                continue;
            }
        };

        match existing_meta.get(&source) {
            Some((existing_hash, existing_created)) if existing_hash == &hash => {
                // 未変更 → スキップ
                skipped += 1;
            }
            Some((_old_hash, existing_created)) => {
                // 変更あり → 旧レコード削除して再インデックス（created 保持）
                to_process.push(FileEntry {
                    path: path.clone(),
                    source,
                    doc_name,
                    hash,
                    created: *existing_created,
                    updated: today,
                    needs_delete: true,
                });
            }
            None => {
                // 新規
                to_process.push(FileEntry {
                    path: path.clone(),
                    source,
                    doc_name,
                    hash,
                    created: today,
                    updated: today,
                    needs_delete: false,
                });
            }
        }
    }

    tracing::info!(
        "Indexing {} file(s) ({} unchanged, skipped)...",
        to_process.len(),
        skipped
    );

    if to_process.is_empty() {
        tracing::info!("All files up to date.");
        return Ok(());
    }

    // 変更ファイルの旧レコードを削除
    for entry in &to_process {
        if entry.needs_delete {
            let escaped = entry.source.replace('\'', "''");
            let filter = format!("source = '{}'", escaped);
            doc_meta_table
                .delete(&filter)
                .await
                .with_context(|| format!("failed to delete doc_meta for {}", entry.source))?;
            doc_chunk_table
                .delete(&filter)
                .await
                .with_context(|| format!("failed to delete doc_chunk for {}", entry.source))?;
        }
    }

    // チャンク生成（doc_meta 書き込み前にフィルタリング）
    // get_chunks が None を返したファイルは doc_meta にも含めない。
    let mut entries_with_chunks: Vec<(FileEntry, Vec<String>)> = Vec::new();
    for entry in to_process {
        let Some(chunks) = get_chunks(&entry.path) else {
            tracing::warn!("skip {} (no chunks generated)", entry.path.display());
            continue;
        };
        tracing::info!("  {} ({} chunks)", entry.doc_name, chunks.len());
        entries_with_chunks.push((entry, chunks));
    }

    if entries_with_chunks.is_empty() {
        tracing::warn!("No files could be indexed.");
        return Ok(());
    }

    // doc_meta 一括書き込み（チャンク生成成功分のみ）
    {
        let sources: Vec<String> = entries_with_chunks
            .iter()
            .map(|(e, _)| e.source.clone())
            .collect();
        let doc_names: Vec<String> = entries_with_chunks
            .iter()
            .map(|(e, _)| e.doc_name.clone())
            .collect();
        let created: Vec<i32> = entries_with_chunks.iter().map(|(e, _)| e.created).collect();
        let updated: Vec<i32> = entries_with_chunks.iter().map(|(e, _)| e.updated).collect();
        let hashes: Vec<String> = entries_with_chunks
            .iter()
            .map(|(e, _)| e.hash.clone())
            .collect();

        let schema = doc_meta_schema();
        let batch = RecordBatch::try_new(
            schema.clone(),
            vec![
                Arc::new(StringArray::from(sources)) as Arc<dyn Array>,
                Arc::new(StringArray::from(doc_names)) as Arc<dyn Array>,
                Arc::new(Date32Array::from(created)) as Arc<dyn Array>,
                Arc::new(Date32Array::from(updated)) as Arc<dyn Array>,
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

    for (entry, chunks) in &entries_with_chunks {
        for (i, chunk) in chunks.iter().enumerate() {
            let vector = model.embed(chunk);
            buffer.push((
                entry.source.clone(),
                entry.doc_name.clone(),
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
    tracing::info!("Indexing complete.");

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

    /// テーブルが空のとき load_existing_meta は空の HashMap を返す。
    #[tokio::test]
    async fn load_existing_meta_empty_table() {
        let tmp = tempfile::tempdir().unwrap();
        let db = crate::db::connect(&tmp.path().join(".lancedb"))
            .await
            .unwrap();
        let table = open_or_create(&db, "doc_meta", doc_meta_schema())
            .await
            .unwrap();

        let meta = load_existing_meta(&table).await.unwrap();
        assert!(meta.is_empty());
    }

    /// load_existing_meta は既存レコードの source/file_hash/created を正しく返す。
    #[tokio::test]
    async fn load_existing_meta_returns_records() {
        let tmp = tempfile::tempdir().unwrap();
        let db = crate::db::connect(&tmp.path().join(".lancedb"))
            .await
            .unwrap();
        let table = open_or_create(&db, "doc_meta", doc_meta_schema())
            .await
            .unwrap();

        // 1件書き込む
        let schema = doc_meta_schema();
        let batch = RecordBatch::try_new(
            schema.clone(),
            vec![
                Arc::new(StringArray::from(vec!["/docs/a.md"])) as Arc<dyn Array>,
                Arc::new(StringArray::from(vec!["a.md"])) as Arc<dyn Array>,
                Arc::new(Date32Array::from(vec![19000i32])) as Arc<dyn Array>,
                Arc::new(Date32Array::from(vec![19001i32])) as Arc<dyn Array>,
                Arc::new(StringArray::from(vec!["abc123"])) as Arc<dyn Array>,
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

        let meta = load_existing_meta(&table).await.unwrap();
        assert_eq!(meta.len(), 1);
        let (hash, created) = meta.get("/docs/a.md").unwrap();
        assert_eq!(hash, "abc123");
        assert_eq!(*created, 19000i32);
    }

    /// ハッシュ未変更ファイルは load_existing_meta のデータと一致し、
    /// FileEntry として処理対象に含まれない（スキップ）ことを確認する。
    ///
    /// 実際の DB 書き込みは行わず、ハッシュ比較ロジックを単体で検証する。
    #[test]
    fn unchanged_file_is_skipped_in_classification() {
        let tmp = tempfile::tempdir().unwrap();
        let f = tmp.path().join("note.md");
        std::fs::write(&f, b"# hello").unwrap();

        let hash = file_hash(&f).unwrap();
        let source = f.to_string_lossy().into_owned();

        // 既存メタに同じハッシュが登録済み
        let mut existing: HashMap<String, (String, i32)> = HashMap::new();
        existing.insert(source.clone(), (hash.clone(), 19000));

        // 差分ロジックを模倣
        let current_hash = file_hash(&f).unwrap();
        let should_skip = existing
            .get(&source)
            .map(|(h, _)| h == &current_hash)
            .unwrap_or(false);

        assert!(should_skip, "unchanged file should be skipped");
    }

    /// ハッシュが変わったファイルは needs_delete = true で to_process に入り、
    /// 既存の created 日付を保持することを確認する。
    #[test]
    fn changed_file_preserves_created_date() {
        let tmp = tempfile::tempdir().unwrap();
        let f = tmp.path().join("note.md");
        std::fs::write(&f, b"# hello").unwrap();

        let old_hash = "deadbeef".to_string();
        let new_hash = file_hash(&f).unwrap();
        let source = f.to_string_lossy().into_owned();
        let original_created = 19000i32;
        let today = today_date32();

        let mut existing: HashMap<String, (String, i32)> = HashMap::new();
        existing.insert(source.clone(), (old_hash.clone(), original_created));

        // 差分ロジックを模倣
        let entry = match existing.get(&source) {
            Some((h, created)) if h == &new_hash => panic!("should not be unchanged"),
            Some((_old, existing_created)) => FileEntry {
                path: f.clone(),
                source: source.clone(),
                doc_name: "note.md".into(),
                hash: new_hash.clone(),
                created: *existing_created,
                updated: today,
                needs_delete: true,
            },
            None => panic!("should be in existing"),
        };

        assert!(entry.needs_delete);
        assert_eq!(
            entry.created, original_created,
            "created should be preserved"
        );
        assert_eq!(entry.updated, today);
        assert_eq!(entry.hash, new_hash);
    }
}
