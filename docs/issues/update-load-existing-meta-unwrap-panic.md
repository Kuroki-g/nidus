# update.rs: load_existing_meta の unwrap() チェーンがパニックを引き起こす

## 問題

`load_existing_meta` はカラム取得とダウンキャストを `unwrap()` で繋いでいる。
スキーマが期待通りでない場合（DB 破損・マイグレーション直後など）にパニックになる。

```rust
let sources = batch
    .column_by_name("source")
    .unwrap()                            // カラムが存在しない場合 panic
    .as_any()
    .downcast_ref::<StringArray>()
    .unwrap();                           // 型が一致しない場合 panic
```

## 影響

- `update_files_in_db` 呼び出し時に予期しないパニックが発生し、プロセスがクラッシュする。
- エラーメッセージが出ないため原因追跡が困難。

## 修正方針

`column_by_name` が `None` を返すケースと `downcast_ref` が失敗するケースをそれぞれ
`with_context(|| ...)` で `Result` に変換し、`?` で呼び出し元に伝播する。

```rust
let sources = batch
    .column_by_name("source")
    .context("doc_meta: column 'source' not found")?
    .as_any()
    .downcast_ref::<StringArray>()
    .context("doc_meta: column 'source' is not StringArray")?;
```

同様に `file_hash` / `created` カラムにも同じ対処を適用する。
