`/clear` 前の締め作業。メモリを整理し、clear 後にすぐ貼り付けられるレビュープロンプトを生成する。

## 手順

### 1. 今セッションの作業内容を把握

Run `git log --oneline -10` to identify commits from this session/

Note: commit hashed, modules names. and test count changes - facts only.

### 2. Update auto-memory

Update auto-memory with factual changes only:
- Which modules were completed (name, test counts)
- What the next action should be
- Any design decisions that were explicitly made

DO NOT SAVE:
- Your own analysis or opinions about the code
- "Discoveries" or "gotchas" - those should come from fresh review
- Temporary or in-process state

Clean up:
- Remove outdated entries
- Duplicate
- Keep under 200 lines

### 3. Next session prompt

Generate a prompt the use can paste after `/clear`.
The next session's Claude weill have a fresh context - leverage that for honest review.

- DO NOT include your own review conclusions - let the fresh session find issues independently
- DO NOT include implementation instructions - the user decides what to do next

Example:

```
前回 <何を実装したか 1 文> を実装した（コミット: <hash>, <hash>, ...）。
このコミットの差分を読んでレビューしてください。
```
