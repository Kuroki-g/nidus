# [Bug] アポストロフィを含むファイルパスで delete クエリが破損する

## 概要

ファイルパスにアポストロフィ（`'`）が含まれる場合、`delete_files_in_db` が生成するクエリが壊れて削除処理が失敗する。

## 発生条件

- ファイル名またはディレクトリ名にアポストロフィを含むパス
- 例: `it's_notes.md`、`user's docs/` など

## 再現手順

```bash
touch "it's_notes.md"
nidus add -f "it's_notes.md"
nidus drop -f "it's_notes.md"
# → クエリ破損により削除されない（または例外）
```

`nidus watch` でファイル削除イベントが発生した場合も同様に失敗する。

## 原因

`delete_db_record.py:42–43` でパスを文字列結合によりクエリに埋め込んでいる。

```python
paths_str = ", ".join([f"'{str(p)}'" for p in paths])
delete_query = f"source IN ({paths_str})"
```

`it's_notes.md` の場合、生成されるクエリは：

```
source IN ('/home/user/it's_notes.md')
```

クォートが閉じず不正なクエリになる。

## 影響範囲

- `packages/cli/src/cli/db/delete_db_record.py`
- `nidus drop` コマンドと `nidus watch` の削除イベント両方に影響

## 修正方針

パス文字列内の `'` を `''` にエスケープする。

```python
def _escape(p: Path) -> str:
    return str(p).replace("'", "''")

paths_str = ", ".join([f"'{_escape(p)}'" for p in paths])
```

または LanceDB がパラメータバインディングをサポートしている場合はそちらを使う。
