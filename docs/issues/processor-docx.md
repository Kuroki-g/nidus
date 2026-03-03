# DOCX サポート

## 概要

Word 文書（`.docx`）をインデックス対象に追加する。

## 実装方針

- `python-docx` または `mammoth` でテキスト抽出
- 見出し・段落構造を活かしてチャンク分割（Markdown プロセッサに準ずる）
- `packages/cli/src/cli/processor/` に `docx_processor.py` を追加
