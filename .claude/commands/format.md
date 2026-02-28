リポジトリ全体に対して ruff でリントとフォーマットを実行してください。

```bash
uv run ruff check .
uv run ruff format .
```

エラーがあればユーザーに報告し、自動修正できるものは `--fix` オプションで修正してください。
