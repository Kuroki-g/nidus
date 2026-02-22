#!/bin/sh
#!/bin/bash
set -e

# モデルの保存先（ snapshots の下のハッシュディレクトリ）
SRC_MODEL_PATH=$(find "$HOME/.cache/huggingface/hub/models--hotchpotch--static-embedding-japanese/snapshots" -mindepth 1 -maxdepth 1 -type d | head -n 1)
TMP_MODEL_DIR="./tmp_model_build"
mkdir -p "$TMP_MODEL_DIR"

echo "Extracting real files from symbolic links..."
# cp -L を使うことで、シンボリックリンクを「実体ファイル」としてコピーします
cp -RL "$SRC_MODEL_PATH/"* "$TMP_MODEL_DIR/"

docker build \
  --build-arg MODEL_MOUNT_PATH="$TMP_MODEL_DIR" \
  --build-arg HF_MODEL_DIR="models--hotchpotch--static-embedding-japanese" \
  --build-arg MODEL_ID="hotchpotch/static-embedding-japanese" \
  --file docker/Dockerfile \
  -t nidus-mcp:latest .

# ビルドが終わったら一時ディレクトリを削除
# rm -rf "$TMP_MODEL_DIR"
