# {{ project-name }}

{{ description }}

A Rust 2024 virtual workspace with root-owned metadata, dependency versions,
lints, and profiles. Requires Rust 1.99.1 and cargo-generate 0.23.8 or newer.

```text
bin/cli/          native command
cmp/command/      WASI command component
crates/starter/   shared library
clients/starter/  optional client library (with_clients=true)
packages/         optional web packaging area (with_packages=true)
```

The three default members are real packages. `bin/*`, `cmp/*`, and `crates/*`
are workspace members; the default selection is the library and native command.
The optional client becomes a member when generated. `packages/*` is excluded
from Cargo membership and is reserved for JavaScript/TypeScript wrappers and
Emscripten packaging. No application framework or provider is required.

## Generate and run

```sh
cargo generate --git https://github.com/FL03/template-rs-workspace \
  --name my-workspace --silent --no-workspace \
  -d alias=FL03 -d description='My Rust workspace'
cd my-workspace
cargo metadata --no-deps --format-version 1
cargo fmt --all --check
cargo test --workspace --all-features
cargo run -p my-workspace-cli
```

The command prints the workspace name and version through the shared library.
Enable optional directories at generation with `-d with_clients=true` and/or
`-d with_packages=true`. The starter packages are not publishable until replaced
with your intended public packages and publishing policy.

## Metadata and profiles

The root defines authors, categories, documentation, edition, homepage, keywords,
license, publish policy, README, repository, Rust minimum, and version. Members
inherit these fields; package names and specific descriptions remain local.
The included demo packages explicitly keep `publish = false`. The shared
`starter` path dependency also carries the root version for Cargo publication
semantics. README inheritance resolves relative to the workspace root.

Cargo profiles exist only at this root: `dev` for fast iteration, `release` for
optimized native builds, and `wasm-dev`/`wasm-release` for WebAssembly builds.
Wasm profiles retain symbols needed for wasm-bindgen postprocessing. Members
must not define their own profiles. Native panic behavior remains unwind;
Wasm profiles select abort. Cargo-release metadata uses shared versions and a
version tag; this configuration does not initiate a release.

```sh
cargo build --workspace --release
cargo build -p my-workspace-component --target wasm32-wasip2 --profile wasm-release
wasm-tools validate target/wasm32-wasip2/wasm-release/my-workspace-component.wasm
wasmtime run target/wasm32-wasip2/wasm-release/my-workspace-component.wasm
```

Install `wasm32-wasip2` for the selected Rust toolchain first. The component is a
WASI CLI command using the shared library, not a custom WIT service interface.
For browser bindings use `wasm32-unknown-unknown` and wasm-bindgen.
`wasm32-unknown-emscripten` requires a separately installed/activated emsdk;
`packages/` does not install one or claim an Emscripten build.

## Add library or command members

From the workspace root:

```sh
cargo generate --git https://github.com/FL03/template-rs \
  --name domain-lib --lib --destination crates --silent --vcs none --no-workspace \
  -d workspace-member=true
cargo test -p domain-lib --all-features
cargo generate --git https://github.com/FL03/template-rs-cli \
  --name tools-cli --destination bin --silent --vcs none --no-workspace \
  -d workspace-member=true
```

Use the same `bin/` route for std-only MCP servers. Use `cmp/` for component
consumers, and `clients/` for optional client libraries when enabled. The root's
member globs discover new packages without rewriting the manifest. Keep
`--vcs none --no-workspace` to avoid nested Git/workspace roots.

The library template inherits the complete metadata/dependency/lint contract
and emits no member profiles. Its optional Serde/JSON/wasm-bindgen dependencies
have defaults disabled in this root; members deliberately select capabilities.
Each library build requires `alloc` or `std`. Commands require `std`.

## Maintainer verification

```sh
python3 scripts/test-ci-policy.py
python3 scripts/test-generation.py --mode all
python3 scripts/test-generation.py --mode all --base ../template-rs
```

The validator retains generated fixtures, commands, diagnostics, and exits. It
checks default and optional layouts, metadata inheritance, root profile ownership,
native command behavior, and library composition with an unchanged root. Optional
`--cli PATH` and `--mcp PATH` compose those templates under `bin/` too. Separate
build/test/clippy/bench modes remain available; bench only compiles its harness.
Maintainer instructions, hooks, workflows, and local environments are excluded
from generated output.
