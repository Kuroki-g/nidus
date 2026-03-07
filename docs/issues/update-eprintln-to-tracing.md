# update.rs: ライブラリ関数から eprintln! で直接 stderr 出力している

## 問題

`update_files_in_db` は `nidus-core`（lib crate）の関数だが、
進捗・警告を `eprintln!` で直接 stderr に書いている。

```rust
eprintln!("Indexing {} file(s)...", files.len());
eprintln!("[Skip] {}", path.display());
eprintln!("  {} ({} chunks)", doc_name, chunks.len());
eprintln!("Indexing complete.");
```

ライブラリは呼び出し側が出力を制御できるべきで、
`eprintln!` を使うと CLI / MCP サーバー / テストなど
どの呼び出し元でも同じ出力が強制される。

## 影響

- テストで不要なノイズが出力される。
- 将来 GUI やログ集約システムと組み合わせるときに制御できない。

## 修正方針

`tracing` クレートに移行する。

```toml
# nidus-core/Cargo.toml
tracing = { workspace = true }
```

```rust
tracing::info!("Indexing {} file(s)...", files.len());
tracing::warn!("[Skip] {}", path.display());
tracing::info!("  {} ({} chunks)", doc_name, chunks.len());
tracing::info!("Indexing complete.");
```

CLI バイナリ（`nidus-cli`）側で `tracing_subscriber` を初期化することで
出力フォーマットや出力先を制御できるようになる。

ステップ 3c（`main.rs` CLI 接続）のタイミングで合わせて対応する。
