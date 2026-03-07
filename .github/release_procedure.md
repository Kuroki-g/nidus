# リリース手順メモ

バイナリは Rust 製 (`rust/crates/nidus-cli`)。手動でビルド → GitHub Release に添付する流れ。

---

## 1. バイナリのビルド

### ローカルビルド（動作確認用）

```bash
make release
# 成果物: rust/target/release/nidus
```

### クロスコンパイル（配布用）

`cross` を使うと Docker 経由でクロスビルドできる。事前に `cargo install cross` が必要。

```bash
# Linux x86_64 (musl: 依存なし・配布推奨)
make cross-linux
# 成果物: rust/target/x86_64-unknown-linux-musl/release/nidus
```

### アーカイブ作成

```bash
make package-linux
# 成果物: nidus-v<version>-x86_64-unknown-linux-musl.tar.gz
```

---

## 2. バージョンの更新

```bash
# Cargo.toml のバージョンを手で編集
# rust/crates/nidus-cli/Cargo.toml
# rust/crates/nidus-core/Cargo.toml
version = "x.y.z"

# lockfile を更新
cd rust/ && cargo build --release
```

---

## 3. タグを打つ

```bash
git tag -a vx.y.z -m "release vx.y.z"
git push origin vx.y.z
```

---

## 4. GitHub Release の作成

1. GitHub → Releases → **Draft a new release**
2. Tag: `vx.y.z`（上で打ったもの）
3. Title: `vx.y.z`
4. Release notes: `manual_release.md` のテンプレートを貼り付けて編集
   - `[Feature/Improvement]` / `[Bug Fixes]` / `[Maintenance]` の各行を埋める
   - `[Old-Tag]...[New-Tag]` を実際のタグに差し替える
5. アーカイブをアップロード（バイナリ添付）
6. **Publish release**

---

## 5. インストール手順（ユーザー向け）

```bash
# Linux / macOS
tar xzf nidus-v<version>-<target>.tar.gz
mv nidus ~/.local/bin/   # PATH が通っている場所に置く

# 初回セットアップ（モデルのダウンロード）
nidus init
```

> `nidus init` はネットワークが必要。以後はオフラインで動作する。

---

## メモ・TODO

- [ ] GitHub Actions でクロスビルドを自動化したい（今は手動）
- [ ] Homebrew tap を作る？
- [ ] `nidus-core` のバージョンは `nidus-cli` に揃えて管理する
