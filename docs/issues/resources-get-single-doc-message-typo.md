# [Bug] get_single_doc の not-found メッセージに typo

## 概要

`resources.py` の `get_single_doc` で検索結果が空のとき返すメッセージに、
開きクォートが欠落した typo がある。

## 該当コード

`packages/mcp-server/src/mcp_server/resources.py:23`

```python
# 現状（typo）
return f"source match to {path}' was not found."
#                              ↑ ' が閉じクォートになってしまっている

# 正しくは
return f"source match to '{path}' was not found."
```

## 影響範囲

- MCP クライアントが受け取るエラーメッセージが壊れた文字列になる
- `packages/mcp-server/src/mcp_server/resources.py`

## 修正方針

`{path}` の前に `'` を追加するだけ。
