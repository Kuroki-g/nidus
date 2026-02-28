bump:
	@uv tree --depth 1 --no-dev | grep -oP '^[a-zA-Z0-9_-]+' | grep -v "^nidus" | xargs uv add --upgrade
