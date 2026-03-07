# CLAUDE.md

このファイルはリポジトリで作業する際に Claude Code (claude.ai/code) へのガイダンスを提供します。

## コマンド

```bash
# セットアップ
uv sync

# CLI 実行
nidus --help
nidus init
nidus update -f file.txt -f dir/
nidus search "キーワード"

# MCP サーバー起動 (localhost:8000)
nidus-mcp

# テスト実行
uv run pytest -m small                  # 高速フィードバック（毎コミット推奨）
uv run pytest -m "small or medium"      # PR 前
uv run pytest                           # 全テスト

# 単一テストファイルの実行
uv run pytest packages/cli/tests/processor/test_markdown_processor.py

# カバレッジ計測（small + medium、HTMLは .coverage_html/）
make coverage

# Rust ビルド
make build           # デバッグビルド
make release         # リリースビルド（rust/target/release/nidus）
make test-rust       # Rust テスト
make cross-linux     # Linux musl 静的バイナリ（cargo install cross が必要）

# Docker イメージビルド
./build-container.sh
```

## 開発方針

コンセプト: **「AI が使いやすい日本語ローカル検索エンジン」**

差別化の軸: 日本語精度 × AI可読性 × 軽量・ローカル。MCP は AI クライアント向けのアダプター層に過ぎず、コアは `packages/cli` の検索エンジン部分にある。

現在の優先事項: **Milestone 1（AI可読性の改善）** → 詳細は `ROADMAP.md` を参照。

## 既知の不具合

`docs/issues/` ディレクトリに不具合メモを管理している。GitHub Issues の代替。

- ファイル名は `<対象機能>-<概要>.md` の形式
- コードレビューや作業中に見つけたバグを記録し、修正時に削除する
- 修正着手前に該当ファイルを読んで原因・影響範囲を把握すること

## 規約

- `python` / `pip` は直接使わず、`uv run` / `uv add` / `uv remove` を使う

## テスト規約（Google Test Size）

テストには必ず以下のマーカーを付ける。「単体/結合/統合」という用語は使わない。

| マーカー | 制約 | このプロジェクトでの例 |
|----------|------|----------------------|
| `@pytest.mark.small` | I/O なし、ネットワークなし、シングルプロセス | パーサー・チャンカーのロジックテスト |
| `@pytest.mark.medium` | ローカルファイル・LanceDB 可、外部ネットワーク不可 | DB 読み書き、CLI コマンドテスト |
| `@pytest.mark.large` | 外部サービス・ネットワーク可 | （現時点では未使用） |

## ネットワーク制限

devcontainer 内は squid プロキシ（`http://http-proxy:3128`）経由のみアクセス可能。WebFetch はホワイトリスト外ドメインでは失敗する。

**許可ドメイン:**
- `.anthropic.com` / `claude.ai` — Anthropic サービス
- `.github.com` / `.githubusercontent.com` — コード参照
- `.pypi.org` / `.pythonhosted.org` — Python パッケージ
- `.huggingface.co` — ML モデル
- `docs.rs` — Rust クレートドキュメント
- `docs.python.org` — Python 標準ライブラリ
- `docs.astral.sh` — uv / ruff ドキュメント
- `docs.pydantic.dev` — Pydantic ドキュメント
- `modelcontextprotocol.io` — MCP プロトコル仕様
- `.qiita.com` / `.zenn.dev` — 日本語技術記事

## アーキテクチャ

`uv` ワークスペースのモノレポで、`packages/` 配下に 3 つのパッケージがある。

- **`packages/common`** — 共有シングルトンと設定。`EmbeddingModelManager`（日本語 sentence-transformer モデルをロード、シングルトン）、`LanceDBManager`（スレッドセーフな LanceDB 接続、シングルトン）、`Settings`（pydantic-settings、`.env` を読み込み）。CLI と MCP サーバーの両方からインポートされる。
- **`packages/cli`** — Click ベースの CLI。`processor/` 配下のファイルプロセッサが markdown（mistune AST）と PDF（pypdf + pdfminer フォールバック）をチャンクに分割し、エンベディングを生成して LanceDB に書き込む。検索は FTS + ベクター検索のハイブリッドで結果をマージする。DB コマンドは `db/` 配下にある。
- **`packages/mcp-server`** — HTTP トランスポート上の FastMCP サーバー。`tools.py` が CLI のデータベース操作を MCP ツール（`search_docs`、`update_docs`、`list_docs`、`db_show_meta`）としてラップする。`resources.py` は `docs://{name}` URI エンドポイントを公開。`prompts.py` はカスタムインストラクションを提供。

### データフロー

```text
ファイル → processor/（チャンク化 + エンベディング）→ LanceDB (~/.cache/nidus/.lancedb)
                                                              ↑
MCP クライアント / CLI ← tools.py ← search_db.py（FTS + ベクター ハイブリッド）
```

### 主要な詳細

- **エンベディングモデル**: `hotchpotch/static-embedding-japanese`、1024 次元ベクター。`nidus init` でダウンロード後はオフライン動作（`TRANSFORMERS_OFFLINE=1`）。
- **LanceDB スキーマ** (`packages/cli/src/cli/db/schemas.py`): `vector`（float32 × 1024）、`text`、`source`（ファイルパス）、`chunk_id`。`text` フィールドに FTS インデックスあり。
- **ハイブリッド検索**: FTS 結果とベクター結果をマージし、FTS マッチを優先して `(source, chunk_id)` で重複排除。
- **設定** (`packages/common/src/common/config.py`): `DB_PATH`、`TABLE_NAME`、`PORT`（8000）、`HOST`（127.0.0.1）、`SEARCH_LIMIT`（5）は `.env` で上書き可能。
- **Python バージョン**: 3.14 固定（`.python-version` 参照）。
