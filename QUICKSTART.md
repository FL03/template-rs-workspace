# Workspace quickstart

Rust 1.99.1+, cargo-generate 0.23.8+, Python 3.11+ for maintainer checks.

```sh
cargo generate --path ./template-rs-workspace --name my-workspace --silent \
  --no-workspace -d with_clients=true -d with_packages=true
cd my-workspace
cargo fmt --all --check
cargo test --workspace --all-features
cargo run -p my-workspace-cli
```

The generated workspace owns metadata, dependency versions, lints, and profiles.
`bin/`, `cmp/`, and `crates/` are always populated; client and web package
directories are optional. Add Rust library members under `crates/` and commands
under `bin/` with `--vcs none --no-workspace -d workspace-member=true`.

```sh
python3 scripts/test-ci-policy.py
python3 scripts/test-generation.py --mode all --base ../template-rs
```

For WASI, install wasm32-wasip2 and build the component command using
`--target wasm32-wasip2 --profile wasm-release`; validate with wasm-tools and run
with wasmtime. Emscripten requires its own SDK and is not installed here.
