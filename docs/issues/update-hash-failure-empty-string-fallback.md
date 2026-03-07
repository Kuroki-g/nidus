# update.rs: ハッシュ計算失敗時の空文字列フォールバックが毎回再インデックスを引き起こす

## 問題

`file_hash` が失敗したとき、空文字列 `""` をハッシュとして使い処理を続けている。

```rust
let hash = file_hash(path).unwrap_or_else(|e| {
    eprintln!("WARN: hash failed for {}: {e}", path.display());
    String::new()   // ← 既存ハッシュとは絶対に一致しない
});
```

`doc_meta` に登録された実際のハッシュと `""` は常に不一致になるため、
`update_files_in_db` を呼ぶたびにそのファイルが「変更あり」と判定される。

## 影響

- 同じファイルを毎回削除 + 再インデックスするため、不要なエンベディング計算とDB書き込みが発生する。
- 変更ファイルの旧レコードを削除するパスを通るため、読み込めないファイルのレコードが消える。

## 修正方針

ハッシュ計算が失敗したファイルは処理対象から除外して `continue` する。

```rust
let hash = match file_hash(path) {
    Ok(h) => h,
    Err(e) => {
        eprintln!("WARN: skipping {} (hash failed: {e})", path.display());
        continue;
    }
};
```
