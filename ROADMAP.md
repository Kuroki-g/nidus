# ROADMAP

## コンセプト

**「AI が使いやすい日本語ローカル検索エンジン」**

差別化の軸：日本語精度 × AI可読性 × 軽量・ローカル

**主なユースケース**: Claude Code・Gemini CLI などの AI エージェントが Bash ツール経由で `nidus search` を直接呼び出す。MCP サーバー（`nidus-mcp`）はサブ機能として提供し、MCP 対応クライアント向けの利便性向上に寄与する。

---

## リリース済み（〜 v0.2.0）

| バージョン | 主な内容 |
|---|---|
| v0.1.0 | init / add / search / drop / list / status（基本 CLI） |
| v0.2.0 | reindex / watch・DOCX / CSV / TSV 対応・インクリメンタル更新・Rust 実装に一本化 |

---

## Milestone 5: ビルド時間の短縮

**ゴール**: 現状 40 分超のビルドを削減し、開発サイクルを快適にする

**背景**: 依存クレート総数 675。最大のボトルネックは `lancedb` が無条件で引き込む **DataFusion（32 クレート）**。mold リンカーはすでに設定済み。

### 案1: 小さな依存整理（低コスト）

- [ ] `futures = "0.3"` → `futures-util`（`StreamExt` / `TryStreamExt` のみ使用）
- [ ] `tokio` features を `"full"` から実使用分のみに絞る（`rt-multi-thread`, `macros`, `sync`, `signal`）

### 案2: lancedb サブモジュール化（高コスト・高効果）

- [ ] `lancedb` を git submodule としてベンダリング
- [ ] DataFusion 依存を feature-gate に移す改修を lancedb 側に加える
- [ ] `default-features = false` でパス依存に切り替え

### 案3: lance 直接利用（高コスト）

- [ ] `lancedb`（高レベルラッパー）を使わず `lance` クレートを直接使う
- [ ] `nidus-core` の DB 層を書き換え、DataFusion 依存を回避できるか検証
