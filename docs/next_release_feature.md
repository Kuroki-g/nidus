# Next Release Features

リリース時のリリースノート作成の参考用。完了済みマイルストーンの内容をまとめる。

---

## DOCX / CSV / TSV サポート

**ゴール**: オフィスドキュメントと表形式データをインデックス対象に追加

- **DOCX サポート**: `python-docx` でテキスト抽出し、文境界チャンク化。`packages/cli/src/cli/processor/docx_processor.py`
- **CSV/TSV サポート**: ヘッダー行を各チャンクに付与した行単位チャンク化。`packages/cli/src/cli/processor/csv_processor.py`

## reindex コマンド

**ゴール**: 埋め込みモデル変更・スキーマ更新後に全ドキュメントを再構築できるコマンド

- **`nidus reindex`**: DB に登録済みのファイルパス一覧を取得し、全レコードを削除してゼロから再インデックス
- **`--dry-run`**: 実際の処理をせず、対象ファイル一覧のみ表示

---

## Docker サポート

**ゴール**: `docker run` で nidus をそのまま使える状態

- **Docker イメージ刷新**: multi-stage build（`ghcr.io/astral-sh/uv:python3.14-trixie-slim` → `python:3.14-slim-trixie`）。埋め込みモデルをビルド時に焼き込み、`ENTRYPOINT ["nidus"]` でコマンドをそのまま渡せる形式
- **Docker 権限修正**: `appuser`（HOME=`/app`）で動作するため `XDG_CACHE_HOME=/app/.cache` を固定し、`/app/.cache/nidus` を事前作成して named volume の書き込み権限を保証
- **`nidus add` の自動 DB 初期化**: テーブル未存在時に自動 `create_table`。`nidus init` を実行しなくても `add` がそのまま動作
