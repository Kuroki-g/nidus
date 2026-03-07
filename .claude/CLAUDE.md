# CLAUDE.md

このファイルはリポジトリで作業する際に Claude Code (claude.ai/code) へのガイダンスを提供します。

## コマンド

```bash
# Rust ビルド
make build           # デバッグビルド
make release         # リリースビルド（rust/target/release/nidus）
make test-rust       # Rust テスト
make cross-linux     # Linux musl 静的バイナリ（cargo install cross が必要）

# CLI 実行（Rust 版）
nidus init
nidus add -f file.txt -f dir/
nidus search "キーワード"

# Docker イメージビルド
./build-container.sh
```

## 開発方針

コンセプト: **「AI が使いやすい日本語ローカル検索エンジン」**

差別化の軸: 日本語精度 × AI可読性 × 軽量・ローカル。

現在の優先事項: **Milestone 1（AI可読性の改善）** → 詳細は `ROADMAP.md` を参照。

## 既知の不具合

`docs/issues/` ディレクトリに不具合メモを管理している。GitHub Issues の代替。

- ファイル名は `<対象機能>-<概要>.md` の形式
- コードレビューや作業中に見つけたバグを記録し、修正時に削除する
- 修正着手前に該当ファイルを読んで原因・影響範囲を把握すること

## テスト規約（Google Test Size）

「単体/結合/統合」という用語は使わない。small / medium / large の 3 段階で分類する。

| サイズ | 制約 |
|--------|------|
| small  | I/O なし、ネットワークなし、シングルプロセス |
| medium | ローカルファイル・DB 可、外部ネットワーク不可 |
| large  | 外部サービス・ネットワーク可（現時点では未使用） |

**Rust**: ソースファイル内 `#[test]` = small 相当、`tests/` ディレクトリ = medium 相当

## ネットワーク制限

devcontainer 内は squid プロキシ（`http://http-proxy:3128`）経由のみアクセス可能。WebFetch はホワイトリスト外ドメインでは失敗する。

**許可ドメイン:**
- `.anthropic.com` / `claude.ai` — Anthropic サービス
- `.github.com` / `.githubusercontent.com` — コード参照
- `.huggingface.co` — ML モデル
- `docs.rs` / `doc.rust-lang.org` — Rust ドキュメント
- `modelcontextprotocol.io` — MCP プロトコル仕様
- `.qiita.com` / `.zenn.dev` — 日本語技術記事
