#!/usr/bin/env bash
# PostToolUse hook: .rs ファイルが編集されたら cargo fmt + clippy を実行
set -euo pipefail

REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
MANIFEST="$REPO_ROOT/rust/Cargo.toml"

# stdin から tool_input.file_path を取得
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)

# .rs ファイルでなければスキップ
if [[ "$FILE_PATH" != *.rs ]]; then
  exit 0
fi

echo "[hook-rust] $FILE_PATH が変更されました。fmt + clippy を実行します..."

cargo fmt --manifest-path "$MANIFEST" --all
cargo clippy --manifest-path "$MANIFEST" --all -- -D warnings

echo "[hook-rust] 完了"
