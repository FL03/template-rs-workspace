# Rust workspace template

A virtual Cargo workspace for composing the single-package
[library](https://github.com/FL03/template-rs),
[CLI](https://github.com/FL03/template-rs-cli), and
[MCP server](https://github.com/FL03/template-rs-mcp) templates. The root owns
package versions, metadata, dependency versions, and lints. Each member chooses
its dependencies and features.

Use Rust 1.96.0 or newer and cargo-generate 0.23.8 or newer. This workspace's
Rust floor accommodates the MCP template; standalone libraries and CLIs can
retain their own lower floors.

## Generate a workspace

```sh
cargo generate --git https://github.com/FL03/template-rs-workspace \
  --name my-workspace --silent --no-workspace \
  -d alias=FL03 -d description="My Rust workspace"
cd my-workspace
cargo metadata --no-deps --format-version 1
```

The initial `crates/starter` library has no dependencies and is not publishable.
Put your first API there, or remove it after adding another member. Cargo requires
a member for a usable virtual workspace. There is no fixed SDK/core split.

## Add packages

Run these commands from the generated workspace root:

```sh
cargo generate --git https://github.com/FL03/template-rs \
  --name domain-lib --destination crates --silent --vcs none --no-workspace \
  -d workspace-member=true
cargo generate --git https://github.com/FL03/template-rs-cli \
  --name tools-cli --destination crates --silent --vcs none --no-workspace \
  -d workspace-member=true
cargo generate --git https://github.com/FL03/template-rs-mcp \
  --name tools-mcp --destination crates --silent --vcs none --no-workspace \
  -d workspace-member=true
```

`members = ["crates/*"]` discovers each package. `--no-workspace` prevents
cargo-generate from rewriting the parent manifest; `--vcs none` prevents nested
Git repositories. Always use both flags for member generation. A member inherits
authors, edition, license, repository, Rust version, package version, and lints.
Descriptions and readmes stay local to the package. Generating member mode
outside a compatible workspace deliberately fails Cargo metadata validation.

Root dependencies cover only the delivered template family: `anyhow`, `clap`,
`rmcp`, `serde`, `serde_json`, `thiserror`, `tokio`, and `tracing-subscriber`.
Declaring a dependency here does not compile it; a member must consume it.
Remove entries you do not use. Add future dependency versions here and reference
them from members with `workspace = true`. Members request capability features;
optional dependencies remain optional on the member. Defaults are disabled where
needed to preserve the library's `no_std` feature boundary.

```sh
cargo fmt --all -- --check
cargo check --workspace --all-features
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace --all-features
cargo run -p tools-cli -- --help
```

Use `cargo run -p tools-mcp` through an MCP client using stdio. The process serves
JSON-RPC on stdout until input closes; diagnostics belong on stderr. Follow that
member's README for tool requests and protocol smoke tests.

## Generation inputs

| Input | Default | Meaning |
| --- | --- | --- |
| `--name` | Required | Workspace directory and starter package prefix |
| `alias` | `FL03` | GitHub repository owner |
| `description` | `A composable Rust workspace` | Shared initial description |
| Built-in `authors` | Cargo's configured author | Root package authors |

Edition 2024 and Apache-2.0 match the checked-in license. There is no license
menu that would disagree with the supplied license file. Descriptions must be
single-line text without double quotes, backslashes, or control characters;
invalid values fail generation. A small local pre-hook applies the same TOML
safety rule to the built-in author. It runs no commands and writes no files.
Names with underscores can be preserved using `--force`; Cargo still validates
the final package name.

Template-authoring workflows, instruction files, Nix/container scaffolding,
validation scripts, and the hook itself are omitted from generated projects.
The output contains one workspace root and no package-local build profiles.
Use Cargo's default profiles or define a needed profile once at the root.

## Validate template changes

From a checkout of this template, Python 3.11+ runs the local generation contract:

```sh
python3 scripts/test-generation.py
python3 scripts/test-generation.py \
  --base ../template-rs --cli ../template-rs-cli --mcp ../template-rs-mcp
```

The optional second command checks real member inheritance, an unchanged root
manifest, and absence of nested workspaces. This script runs generation, format,
and metadata checks without compilation; run the Cargo commands above against
the generated output for compile, lint, and runtime validation. No hosted
workflows are dispatched.

See [QUICKSTART.md](QUICKSTART.md) for a local checkout workflow. The contract
follows the official [Cargo workspace reference](https://doc.rust-lang.org/cargo/reference/workspaces.html),
[cargo-generate placeholders](https://cargo-generate.github.io/cargo-generate/templates/template_defined_placeholders.html),
and [ignore rules](https://cargo-generate.github.io/cargo-generate/templates/ignoring.html).
