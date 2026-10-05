# Local workspace quickstart

Use Rust 1.96.0+, cargo-generate 0.23.8+, and sibling checkouts of the existing
FL03 repositories. These commands use local template files, so they also test
changes before publishing them.

```sh
git clone https://github.com/FL03/template-rs-workspace
git clone https://github.com/FL03/template-rs
git clone https://github.com/FL03/template-rs-cli
git clone https://github.com/FL03/template-rs-mcp

cargo generate --path ./template-rs-workspace --name demo-workspace \
  --silent --vcs none --no-workspace
cargo generate --path ./template-rs --name demo-lib \
  --destination ./demo-workspace/crates --silent --vcs none --no-workspace \
  -d workspace-member=true
cargo generate --path ./template-rs-cli --name demo-cli \
  --destination ./demo-workspace/crates --silent --vcs none --no-workspace \
  -d workspace-member=true
cargo generate --path ./template-rs-mcp --name demo-mcp \
  --destination ./demo-workspace/crates --silent --vcs none --no-workspace \
  -d workspace-member=true

cd demo-workspace
cargo metadata --no-deps --format-version 1
cargo fmt --all -- --check
cargo check --workspace --all-features
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace --all-features
cargo run -p demo-cli -- --help
```

There should be four workspace members: the starter library plus the three
generated packages. All share one root lockfile, target directory, and dependency
version catalogue. The root `Cargo.toml` stays unchanged when adding members.
Do not generate member mode into a directory outside this workspace.

For a standalone package, omit `-d workspace-member=true` and choose a destination
outside the workspace. The library, CLI, and MCP templates each generate one
package without creating their own workspace.

The local generator contract can retain its output for further validation:

```sh
python3 template-rs-workspace/scripts/test-generation.py \
  --base template-rs --cli template-rs-cli --mcp template-rs-mcp \
  --output /tmp/template-workspace-check
```

`--output` must identify a new directory. Inspect its `results.json` for exact
commands and exit statuses, then compile the composed `workspace-contract`
directory using the commands above. Keep heavy Cargo builds sequentially so they
reuse caches without competing for resources.
