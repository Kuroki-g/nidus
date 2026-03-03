# 検索結果のスコア表示・フィルタリング（ファイルタイプ・日付）

## 課題

現在のスキーマ（`packages/cli/src/cli/db/schemas.py`）に `file_type` や
`updated_at` フィールドがなく、以下の絞り込みができない。

- `nidus search "キーワード" --type md`（Markdown のみ）
- `nidus search "キーワード" --after 2025-01-01`（日付フィルタ）

## 実装に必要な変更

1. **スキーマ拡張**
   - `doc_chunk` テーブルに `file_type: str`（拡張子）、`indexed_at: timestamp` を追加
   - 既存 DB はマイグレーションが必要（または再インデックス）

2. **`file_processor.py` の更新**
   - チャンク生成時に `file_type`、`indexed_at` をメタデータとして付与

3. **`search_db.py` の更新**
   - `search_docs_in_db` にフィルタ引数を追加
   - LanceDB の `.where()` に条件を渡す

4. **`main.py` の更新**
   - `nidus search` に `--type`, `--after`, `--before` オプションを追加

## スコア表示について

`search --json` で `score` フィールドは既に出力される。
端末向けの `display_results_simple` でも score は表示済み。
「フィルタリング by スコア閾値」（`--min-score 0.05` 等）は JSON 出力と組み合わせて
シェルスクリプト側でも対応可能なので、CLI オプション化の優先度は低い。

## 保留理由

- スキーマ変更はマイグレーション戦略の検討が必要（破壊的変更）
- `indexed_at` vs `file_mtime`（ファイルの更新日時）どちらを持つべきか未決定
- ユースケースが具体化してから設計を固めたい
