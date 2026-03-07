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
	cd rust && cargo about generate -o ../THIRD-PARTY-NOTICES.txt about.hbs

# パッケージング
VERSION := $(shell grep '^version' rust/crates/nidus-cli/Cargo.toml | head -1 | sed 's/version = "\(.*\)"/\1/')
package-linux: release
	tar czf nidus-v$(VERSION)-x86_64-unknown-linux-gnu.tar.gz \
		-C rust/target/release nidus
