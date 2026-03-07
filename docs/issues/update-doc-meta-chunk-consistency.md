# update.rs: doc_meta と doc_chunk の書き込み順序が不整合を起こす

## 問題

`update_files_in_db` は最初に全ファイルの `doc_meta` をまとめて書き込み、
その後で各ファイルの `doc_chunk` をバッチ書き込みする。

`get_chunks(path)` が `None` を返したファイルは `doc_meta` にレコードが入るが
`doc_chunk` には何も入らない状態になる。

```rust
// 先に全ファイル分の meta を書き込む
doc_meta_table.add(...).execute().await?;

// その後でチャンク書き込み
for path in &files {
    let Some(chunks) = get_chunks(path) else {
        eprintln!("[Skip] {}", path.display()); // meta だけ残る
        continue;
    };
    ...
}
```

## 影響

- ステップ 3b（差分更新）でハッシュ比較するとき、
  「meta あり・chunk なし」のファイルを未変更と判定してスキップしてしまう。
- 検索結果に chunk が存在しないファイルのメタデータが残り続ける。

## 修正方針

以下のいずれか：

1. **順序を逆にする**: 各ファイルの `doc_chunk` 書き込みが成功してから `doc_meta` を書き込む
   （ファイル単位で meta + chunk をひとまとめにする）。
2. **skip ファイルを meta 対象から除外する**: チャンク生成が成功したファイルだけを
   `sources` / `doc_names` / `hashes` に含める。

方針 2 のほうが実装変更が小さい。
ステップ 3b 着手前に対応すること。
