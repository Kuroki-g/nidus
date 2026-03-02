lint:
	uv run ruff check packages/

type:
	uv run pyright packages/

check: lint type

fmt:
	uv run ruff format packages/ && uv run ruff check packages/ --fix

bump:
	@uv tree --depth 1 --no-dev | grep -oP '^[a-zA-Z0-9_-]+' | grep -v "^nidus" | xargs uv add --upgrade

notices:
	uv run python scripts/generate_third_party_notices.py
