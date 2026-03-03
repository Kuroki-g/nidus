# nidus export / import — DB のポータビリティ

## 概要

LanceDB のデータをエクスポート・インポートする `nidus export` / `nidus import` コマンドを追加する。

## ユースケース

- 別マシンへの移行
- バックアップ
- チーム間での DB 共有

## 実装方針

- `nidus export --output nidus-backup.tar.gz`（LanceDB ディレクトリを圧縮）
- `nidus import --input nidus-backup.tar.gz`（既存 DB に上書きまたはマージ）
- マージ戦略（上書き / 追記 / 重複スキップ）は要検討
