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

check: clippy

fmt-rust:
	cargo fmt $(MANIFEST) --all

clippy:
	cargo clippy $(MANIFEST) --all -- -D warnings

notices:
	python scripts/generate_third_party_notices.py
