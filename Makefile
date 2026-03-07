CARGO := cargo --manifest-path rust/Cargo.toml
CROSS := cross --manifest-path rust/Cargo.toml

## Rust
build:
	$(CARGO) build --all

release:
	$(CARGO) build --release --all

test-rust:
	$(CARGO) test --all

# クロスコンパイル（cross が必要: cargo install cross）
cross-linux:
	$(CROSS) build --release --target x86_64-unknown-linux-musl

## Python
lint:
	uv run ruff check packages/

type:
	uv run pyright packages/

check: lint type

fmt:
	uv run ruff format packages/ && uv run ruff check packages/ --fix

fmt-rust:
	cargo fmt --manifest-path rust/Cargo.toml --all

clippy:
	cargo clippy --manifest-path rust/Cargo.toml --all -- -D warnings

coverage:
	uv run pytest -m "small or medium" --cov=cli --cov=common --cov=mcp_server --cov-report=term-missing --cov-report=html:.coverage_html

bump:
	@uv tree --depth 1 --no-dev | grep -oP '^[a-zA-Z0-9_-]+' | grep -v "^nidus" | xargs uv add --upgrade

notices:
	uv run python scripts/generate_third_party_notices.py
