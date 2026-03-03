# TeX サポート

## 概要

TeX / LaTeX ファイル（`.tex`）をインデックス対象に追加する。

## 実装方針

- TeX コマンドを除去してプレーンテキストを抽出（`pylatexenc` など）
- セクション・サブセクション単位でチャンク分割
- `packages/cli/src/cli/processor/` に `tex_processor.py` を追加
