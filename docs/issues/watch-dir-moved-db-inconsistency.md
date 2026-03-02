# [Bug] ディレクトリ移動時に DB レコードが残る

## 概要

`nidus watch` 実行中にディレクトリをリネーム・移動すると、配下ファイルの DB レコードが古いパスのまま残り続ける。

## 発生条件

- Linux 環境（devcontainer 含む）で再現
- macOS では watchdog バックエンドの違いにより発生しない場合がある

## 再現手順

```bash
nidus watch ./docs
# 別ターミナルで
mv docs/notes docs/archive
# → docs/notes/file.md の DB レコードが残る
#   docs/archive/file.md はインデックスされない
```

## 原因

`watch.py:37` の `on_moved` でディレクトリイベントを無視している。

```python
def on_moved(self, event: FileMovedEvent) -> None:
    if event.is_directory:
        return  # ← ディレクトリ移動を無視
```

Linux では watchdog が `DirMovedEvent` を 1 つ発火するだけで、配下ファイルの個別 `FileMovedEvent` を生成しない。そのため `on_moved` がファイルレベルで呼ばれず DB が更新されない。

## 影響範囲

- `packages/cli/src/cli/watch.py`

## 修正方針

`on_moved` でディレクトリの場合、`src_path` 配下の全ファイルを削除し `dest_path` 配下を追加する。

```python
def on_moved(self, event: FileMovedEvent) -> None:
    if event.is_directory:
        src = Path(event.src_path)
        dest = Path(event.dest_path)
        # src 配下の対象ファイルを DB から削除
        old_files = [f for f in dest.rglob("*") if self._is_supported(str(f))]
        # ただし dest に移動済みなので src パスを手動で組み立てる必要がある
        # → src / relative_path で旧パスを復元して削除
        ...
        return
    ...
```

※ 旧パスのファイルはすでに存在しないため、`delete_files_in_db` が存在チェックをスキップする修正（`ba477c4`）が前提となる。
