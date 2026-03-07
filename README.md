# nidus

**Nidus** は日本語に最適化されたローカル文書検索エンジンです。
Claude Code・Gemini CLI などの AI エージェントが Bash ツール経由で `nidus search` を直接呼び出すことを主なユースケースとして設計されています。

Markdown・PDF・テキスト・AsciiDoc・HTML・DOCX・CSV をチャンクに分割してインデックスし、FTS + ベクターのハイブリッド検索で結果を返します。

> [!WARNING]
> This project is published for personal use only. Breaking changes may occur at any release.
> Issues and pull requests are not accepted.

## Features

- **日本語向けチャンク分割**: 句点（。！？）→ 段落 → 改行の優先順で文境界を検出。見出しをチャンクのプレフィックスとして付与し、検索結果の文脈を保持
- **ハイブリッド検索**: FTS + ベクター検索を RRF (Reciprocal Rank Fusion) でスコアリング・統合
- **Adjacent chunks**: ヒットチャンクの前後を結合してスニペットを生成し、AI に十分な文脈を渡す
- **完全ローカル**: `nidus init` でモデルをキャッシュ後はオフライン動作

## Supported File Types

| 拡張子 | 処理 |
|--------|------|
| `.md`  | 見出し単位でセクション分割 → 文境界チャンク化 |
| `.adoc` | 見出し単位でセクション分割 → 文境界チャンク化 |
| `.txt` | 文境界チャンク化 |
| `.pdf` | テキスト抽出 (pdf-extract) → 文境界チャンク化 |
| `.html` / `.htm` | テキスト抽出 (scraper) → 文境界チャンク化 |
| `.docx` | テキスト抽出 (quick-xml) → 文境界チャンク化 |
| `.csv` | ヘッダー付き行単位でチャンク化 |
| `.tsv` | ヘッダー付き行単位でチャンク化 |

## Quick Start

### インストール

```bash
cargo install --git https://github.com/Kuroki-g/nidus.git --manifest-path rust/Cargo.toml nidus-cli
```

### モデルのダウンロード（初回のみ）

```bash
nidus init
```

埋め込みモデル (`hotchpotch/static-embedding-japanese`) をダウンロードします。以降はオフラインで動作します。DB の初期化は初回の `nidus add` 実行時に自動で行われます。

### ドキュメントを追加

```bash
nidus add -f README.md -f docs/
```

### 検索

```bash
nidus search "チャンク分割"
```

JSON 形式で出力する場合:

```bash
nidus search "チャンク分割" --json
```

## CLI Commands

| コマンド | 説明 |
|---------|------|
| `nidus init`              | 埋め込みモデルをダウンロード（初回のみ必要） |
| `nidus add -f FILE/DIR`   | ファイルをインデックスに追加・更新（複数指定可） |
| `nidus search QUERY`      | キーワードでハイブリッド検索 |
| `nidus search QUERY --json` | 検索結果を JSON 形式で出力 |

## Configuration

`.env` ファイルで設定を上書きできます:

```env
DB_PATH=~/.cache/nidus/.lancedb   # DB 保存先
MODEL_DIR=~/.cache/nidus/model    # 埋め込みモデルの保存先
SEARCH_LIMIT=5                     # 検索結果の最大件数
SEARCH_RRF_K=60                    # RRF スコアリングの k パラメータ
SEARCH_ADJACENT_WINDOW=1           # Adjacent chunks の前後ウィンドウ幅（チャンク数）
```

## Technical Details

- **埋め込みモデル**: `hotchpotch/static-embedding-japanese` (model2vec, 1024 次元)
- **ベクター DB**: LanceDB
- **チャンク設定**: `chunk_size=1000 / overlap=150 / min_chunk=200`
- **FTS**: bigram（ngram）トークナイザーによる日本語全文検索
- **ランキング**: RRF (k=60) で FTS・ベクター検索結果を統合
- **言語**: Rust / パッケージ管理: Cargo ワークスペース

## Notice

データはすべて `$HOME/.cache/nidus/` に保存されます。クリーンアップするにはこのディレクトリを削除してください。

## License

[Apache License 2.0](LICENSE)
