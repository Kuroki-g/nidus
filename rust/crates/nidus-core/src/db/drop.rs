use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use lancedb::Connection;

use crate::db::connection::{DEFAULT_TABLE_DOC_CHUNK, DEFAULT_TABLE_DOC_META};

/// 指定パスのリストを削除対象ファイルパス（文字列）に展開する。
///
/// - ディレクトリは再帰的に展開してすべてのファイルを列挙する。
/// - 存在しないパスはそのまま含める（watch イベントによるファイル削除後も
///   DB レコードを消せるように）。
fn expand_paths(paths: &[PathBuf]) -> Vec<String> {
    fn walk(dir: &Path, out: &mut Vec<String>) {
        let Ok(entries) = std::fs::read_dir(dir) else {
            return;
        };
        let mut children: Vec<_> = entries.flatten().map(|e| e.path()).collect();
        children.sort();
        for p in children {
            if p.is_dir() {
                walk(&p, out);
            } else {
                out.push(p.to_string_lossy().into_owned());
            }
        }
    }

    let mut result = Vec::new();
    for path in paths {
        if path.is_dir() {
            walk(path, &mut result);
        } else {
            result.push(path.to_string_lossy().into_owned());
        }
    }
    result
}

/// 指定ファイルのレコードを `doc_meta` と `doc_chunk` の両テーブルから削除する。
///
/// - テーブルが存在しない場合はスキップする。
/// - ディレクトリは再帰的にファイルへ展開される。
/// - 存在しないパスも削除対象に含めるため、watch による削除後の後処理にも使える。
pub async fn drop_files_in_db(paths: &[PathBuf], db: &Connection) -> Result<()> {
    let sources = expand_paths(paths);
    if sources.is_empty() {
        eprintln!("No paths to delete.");
        return Ok(());
    }

    // SQL の IN 句を構築（シングルクォートをエスケープ）
    let escaped: Vec<String> = sources
        .iter()
        .map(|s| format!("'{}'", s.replace('\'', "''")))
        .collect();
    let filter = format!("source IN ({})", escaped.join(", "));

    let existing_tables = db
        .table_names()
        .execute()
        .await
        .context("failed to list table names")?;

    for table_name in [DEFAULT_TABLE_DOC_META, DEFAULT_TABLE_DOC_CHUNK] {
        if !existing_tables.contains(&table_name.to_string()) {
            continue;
        }
        let table = db
            .open_table(table_name)
            .execute()
            .await
            .with_context(|| format!("failed to open table: {table_name}"))?;
        table
            .delete(&filter)
            .await
            .with_context(|| format!("failed to delete from {table_name}"))?;
    }

    eprintln!("Deleted records for {} path(s).", sources.len());
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn expand_paths_single_file() {
        let tmp = tempfile::tempdir().unwrap();
        let f = tmp.path().join("note.md");
        std::fs::write(&f, b"# hello").unwrap();

        let result = expand_paths(&[f.clone()]);
        assert_eq!(result, vec![f.to_string_lossy().to_string()]);
    }

    #[test]
    fn expand_paths_nonexistent_file_included() {
        let path = PathBuf::from("/nonexistent/path/file.md");
        let result = expand_paths(&[path.clone()]);
        assert_eq!(result, vec![path.to_string_lossy().to_string()]);
    }

    #[test]
    fn expand_paths_directory_recursive() {
        let tmp = tempfile::tempdir().unwrap();
        let sub = tmp.path().join("sub");
        std::fs::create_dir(&sub).unwrap();
        std::fs::write(tmp.path().join("a.md"), b"a").unwrap();
        std::fs::write(sub.join("b.txt"), b"b").unwrap();

        let mut result = expand_paths(&[tmp.path().to_path_buf()]);
        result.sort();

        assert!(result.iter().any(|s| s.ends_with("a.md")));
        assert!(result.iter().any(|s| s.ends_with("b.txt")));
    }

    #[test]
    fn expand_paths_empty_input() {
        let result = expand_paths(&[]);
        assert!(result.is_empty());
    }

    #[tokio::test]
    async fn drop_files_no_tables_is_noop() {
        let tmp = tempfile::tempdir().unwrap();
        let db = crate::db::connect(&tmp.path().join(".lancedb"))
            .await
            .unwrap();

        let f = tmp.path().join("note.md");
        std::fs::write(&f, b"# hello").unwrap();

        // テーブルが存在しなくてもエラーにならない
        let result = drop_files_in_db(&[f], &db).await;
        assert!(result.is_ok());
    }
}
