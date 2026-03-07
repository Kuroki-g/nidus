use std::path::PathBuf;

use anyhow::Result;
use lancedb::Connection;
use notify::event::{ModifyKind, RenameMode};
use notify::{EventKind, RecursiveMode, Watcher};
use tokio::sync::mpsc;

use crate::db::drop::drop_files_in_db;
use crate::db::update::update_files_in_db;
use crate::embedding::EmbeddingModel;

const SUPPORTED_EXTS: &[&str] = &[
    "md", "adoc", "txt", "pdf", "html", "htm", "docx", "csv", "tsv",
];

fn is_supported(path: &std::path::Path) -> bool {
    path.extension()
        .and_then(|e| e.to_str())
        .map(|e| SUPPORTED_EXTS.contains(&e.to_lowercase().as_str()))
        .unwrap_or(false)
}

/// 指定ディレクトリを再帰的に監視し、ファイル変更を自動インデックスする。
///
/// - 作成・変更 → `update_files_in_db` で差分インデックス
/// - 削除 → `drop_files_in_db` で DB レコード削除
/// - リネーム → 旧パスを削除、新パスを追加
///
/// Ctrl-C を受信するまでブロックする。
pub async fn watch_directories(
    dirs: &[PathBuf],
    db: &Connection,
    model: &EmbeddingModel,
) -> Result<()> {
    let (tx, mut rx) = mpsc::unbounded_channel::<notify::Result<notify::Event>>();

    let mut watcher = notify::RecommendedWatcher::new(
        move |res| {
            let _ = tx.send(res);
        },
        notify::Config::default(),
    )?;

    for dir in dirs {
        watcher.watch(dir, RecursiveMode::Recursive)?;
        tracing::info!("watching: {}", dir.display());
    }

    tracing::info!("Press Ctrl-C to stop.");

    loop {
        tokio::select! {
            Some(res) = rx.recv() => {
                match res {
                    Ok(event) => handle_event(event, db, model).await,
                    Err(e) => tracing::error!("notify error: {e}"),
                }
            }
            _ = tokio::signal::ctrl_c() => {
                tracing::info!("Stopping.");
                break;
            }
        }
    }

    Ok(())
}

async fn handle_event(event: notify::Event, db: &Connection, model: &EmbeddingModel) {
    match event.kind {
        // ファイル作成
        EventKind::Create(_) => {
            let paths: Vec<PathBuf> = event
                .paths
                .into_iter()
                .filter(|p| p.is_file() && is_supported(p))
                .collect();
            if paths.is_empty() {
                return;
            }
            for p in &paths {
                tracing::info!("created: {}", p.display());
            }
            if let Err(e) = update_files_in_db(&paths, db, model).await {
                tracing::error!("add failed: {e}");
            }
        }

        // ファイル内容変更（Data または汎用 Any）
        EventKind::Modify(ModifyKind::Data(_) | ModifyKind::Any) => {
            let paths: Vec<PathBuf> = event
                .paths
                .into_iter()
                .filter(|p| p.is_file() && is_supported(p))
                .collect();
            if paths.is_empty() {
                return;
            }
            for p in &paths {
                tracing::info!("modified: {}", p.display());
            }
            if let Err(e) = update_files_in_db(&paths, db, model).await {
                tracing::error!("update failed: {e}");
            }
        }

        // ファイル削除（ファイルが消えているので拡張子のみで判定）
        EventKind::Remove(_) => {
            let paths: Vec<PathBuf> = event
                .paths
                .into_iter()
                .filter(|p| is_supported(p))
                .collect();
            if paths.is_empty() {
                return;
            }
            for p in &paths {
                tracing::info!("deleted: {}", p.display());
            }
            if let Err(e) = drop_files_in_db(&paths, db).await {
                tracing::error!("delete failed: {e}");
            }
        }

        // 同一ディレクトリ内リネーム（From/To が同一イベントで届く）
        EventKind::Modify(ModifyKind::Name(RenameMode::Both)) => {
            if event.paths.len() < 2 {
                return;
            }
            let from = event.paths[0].clone();
            let to = event.paths[1].clone();

            if is_supported(&from) {
                tracing::info!("renamed (delete old): {}", from.display());
                if let Err(e) = drop_files_in_db(&[from], db).await {
                    tracing::error!("delete failed: {e}");
                }
            }
            if to.is_file() && is_supported(&to) {
                tracing::info!("renamed (add new): {}", to.display());
                if let Err(e) = update_files_in_db(&[to], db, model).await {
                    tracing::error!("add failed: {e}");
                }
            }
        }

        // クロスディレクトリ移動：旧パス通知
        EventKind::Modify(ModifyKind::Name(RenameMode::From)) => {
            let paths: Vec<PathBuf> = event
                .paths
                .into_iter()
                .filter(|p| is_supported(p))
                .collect();
            if paths.is_empty() {
                return;
            }
            for p in &paths {
                tracing::info!("moved away (delete): {}", p.display());
            }
            if let Err(e) = drop_files_in_db(&paths, db).await {
                tracing::error!("delete failed: {e}");
            }
        }

        // クロスディレクトリ移動：新パス通知
        EventKind::Modify(ModifyKind::Name(RenameMode::To)) => {
            let paths: Vec<PathBuf> = event
                .paths
                .into_iter()
                .filter(|p| p.is_file() && is_supported(p))
                .collect();
            if paths.is_empty() {
                return;
            }
            for p in &paths {
                tracing::info!("moved here (add): {}", p.display());
            }
            if let Err(e) = update_files_in_db(&paths, db, model).await {
                tracing::error!("add failed: {e}");
            }
        }

        // メタデータ変更・その他は無視
        _ => {}
    }
}
