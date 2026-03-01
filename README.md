# nidus

**Nidus** は日本語に最適化されたローカル文書検索エンジンです。
Claude Code・Gemini CLI などの AI エージェントが Bash ツール経由で `nidus search` を直接呼び出すことを主なユースケースとして設計されています。MCP サーバーとしても起動でき、MCP 対応クライアントからも利用できます。

Markdown・PDF・テキスト・AsciiDoc・HTML をチャンクに分割してインデックスし、FTS + ベクターのハイブリッド検索で結果を返します。

## Features

- **日本語向けチャンク分割**: 句点（。！？）→ 段落 → 改行の優先順で文境界を検出。見出しをチャンクのプレフィックスとして付与し、検索結果の文脈を保持
- **ハイブリッド検索**: FTS + ベクター検索を RRF (Reciprocal Rank Fusion) でスコアリング・統合
- **Adjacent chunks**: ヒットチャンクの前後を結合してスニペットを生成し、AI に十分な文脈を渡す
- **完全ローカル**: `nidus init` でモデルをキャッシュ後はオフライン動作
- **MCP 対応**: `nidus-mcp` で HTTP トランスポートの MCP サーバーとして起動可能（サブ機能）

## Supported File Types

| 拡張子 | 処理 |
|--------|------|
| `.md`  | 見出し単位でセクション分割 → 文境界チャンク化 |
| `.adoc` | 見出し単位でセクション分割 → 文境界チャンク化 |
| `.txt` | 文境界チャンク化 |
| `.pdf` | テキスト抽出 (pypdf / pdfminer フォールバック) → 文境界チャンク化 |
| `.html` / `.htm` | テキスト抽出 (html.parser) → 文境界チャンク化 |

## Quick Start

### インストール

```bash
uv tool install git+https://github.com/Kuroki-g/nidus.git
```

### 初期化（初回のみ）

```bash
nidus init
```

埋め込みモデル (`hotchpotch/static-embedding-japanese`) をダウンロードし、LanceDB を初期化します。以降はオフラインで動作します。

### ドキュメントを追加

```bash
nidus add -f README.md -f docs/
```

### 検索

```bash
nidus search "チャンク分割"
```

### MCP サーバーとして起動

```bash
nidus-mcp
```

AI クライアントの設定に追記します（例: Claude Code `settings.json`）:

```json
{
  "mcpServers": {
    "nidus": {
      "httpUrl": "http://localhost:8000/mcp"
    }
  }
}
```

## CLI Commands

グローバルオプション（全コマンド共通）:

| オプション | 説明 |
|-----------|------|
| `-v` / `--verbose` | INFO ログを表示 |
| `--debug` | DEBUG ログを表示 |

コマンド一覧:

| コマンド | 説明 |
|---------|------|
| `nidus init [--dir DIR]` | DB 初期化・モデルダウンロード。`--dir` でファイルも同時追加可 |
| `nidus add -f FILE/DIR`  | ファイルをインデックスに追加・更新（複数指定可） |
| `nidus drop -f FILE/DIR` | ファイルをインデックスから削除（複数指定可） |
| `nidus search KEYWORD`   | キーワードでハイブリッド検索 |
| `nidus list [KEYWORD]`   | インデックス済みファイル一覧（キーワードでパスを絞り込み） |
| `nidus status`           | DB のメタ情報（テーブル・レコード数など）を表示 |
| `nidus debug parse FILE` | ファイルのチャンク分割結果を確認 |

## MCP Tools

`nidus-mcp` で起動したサーバー (`http://localhost:8000/mcp`) は以下のツールを提供します:

| ツール | 説明 |
|--------|------|
| `search_docs` | キーワードでハイブリッド検索し、スニペットを返す |
| `update_docs` | ドキュメントを追加・更新 |
| `list_docs`   | インデックス済みドキュメントの一覧を返す |

## Configuration

`.env` ファイルで設定を上書きできます:

```env
DB_PATH=~/.cache/nidus/.lancedb   # DB 保存先
SEARCH_LIMIT=5                     # 検索結果の最大件数
SEARCH_RRF_K=60                    # RRF スコアリングの k パラメータ
SEARCH_ADJACENT_WINDOW=1           # Adjacent chunks の前後ウィンドウ幅（チャンク数）
PORT=8000                          # MCP サーバーポート
HOST=127.0.0.1                     # MCP サーバーホスト
```

## Technical Details

- **埋め込みモデル**: `hotchpotch/static-embedding-japanese` (model2vec, 1024 次元)
- **ベクター DB**: LanceDB
- **チャンク設定**: `chunk_size=1000 / overlap=150 / min_chunk=200`
- **FTS**: bigram（ngram）トークナイザーによる日本語全文検索
- **ランキング**: RRF (k=60) で FTS・ベクター検索結果を統合
- **Python**: 3.14 / パッケージ管理: uv ワークスペース

## Docker

Docker イメージをビルドして使うことができます:

```bash
./build-container.sh
```

## Notice

データはすべて `$HOME/.cache/nidus/` に保存されます。クリーンアップするにはこのディレクトリを削除してください。

## License

[Apache License 2.0](LICENSE)
