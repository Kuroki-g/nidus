MANIFEST := --manifest-path rust/Cargo.toml

## Rust
build:
	cargo build $(MANIFEST) --all

release:
	cargo build $(MANIFEST) --release --all

test-rust:
	cargo test $(MANIFEST) --all

# クロスコンパイル（cross が必要: cargo install cross）
cross-linux:
	cross build $(MANIFEST) --release --target x86_64-unknown-linux-musl

## Python
lint:
	uv run ruff check packages/

type:
	uv run pyright packages/

check: lint type

fmt:
	uv run ruff format packages/ && uv run ruff check packages/ --fix

fmt-rust:
	cargo fmt $(MANIFEST) --all

clippy:
	cargo clippy $(MANIFEST) --all -- -D warnings

coverage:
	uv run pytest -m "small or medium" --cov=cli --cov=common --cov=mcp_server --cov-report=term-missing --cov-report=html:.coverage_html

bump:
	@uv tree --depth 1 --no-dev | grep -oP '^[a-zA-Z0-9_-]+' | grep -v "^nidus" | xargs uv add --upgrade

notices:
	uv run python scripts/generate_third_party_notices.py
