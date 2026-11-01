#!/usr/bin/env python3
"""Validate real generated workspaces; retain fixtures and exact command results."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shlex
import tempfile
import tomllib


def read_manifest(path):
    return tomllib.loads(path.read_text())


def cargo_commands(output, mode):
    """Select checks for the dependency-free starter in generated workspace roots."""
    commands = []
    root = output / "workspace-contract" / "Cargo.toml"
    alternate = output / "workspace_contract" / "Cargo.toml"
    if mode in ("all", "build", "test"):
        verb = "build" if mode == "build" else "test"
        commands.append(["cargo", verb, "--manifest-path", root, "--workspace"])
        commands.append(["cargo", "check" if mode == "all" else verb,
                         "--manifest-path", alternate, "--workspace"])
    if mode in ("all", "clippy"):
        commands.append(["cargo", "clippy", "--manifest-path", root,
                         "--workspace", "--all-targets", "--", "-D", "warnings"])
    if mode == "bench":
        # No dedicated benchmarks exist; compile the benchmark harness only.
        commands.append(["cargo", "bench", "--manifest-path", root, "--workspace", "--no-run"])
    return commands


def run_cargo_checks(output, mode, run):
    """Require generated, parseable manifests before starting any compilation."""
    commands = cargo_commands(output, mode)
    for command in commands:
        manifest = Path(command[command.index("--manifest-path") + 1])
        if not manifest.resolve().is_relative_to(output.resolve()):
            raise ValueError(f"Cargo target is outside generated fixtures: {manifest}")
        content = manifest.read_text()
        if "{{" in content.replace("v{{version}}", "") or "{%" in content:
            raise ValueError(f"Cargo target contains unexpanded template syntax: {manifest}")
        tomllib.loads(content)
    for command in commands:
        run(command)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--base", type=Path)
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--mcp", type=Path)
    parser.add_argument("--output", "--workdir", type=Path, help="fresh fixture directory (retained)")
    parser.add_argument("--mode", choices=("all", "build", "test", "clippy", "bench", "generate"),
                        default="generate", help="generated-project check (default: generate)")
    parser.add_argument("--generate-only", action="store_true", help="alias for --mode generate")
    args = parser.parse_args()
    if args.generate_only:
        args.mode = "generate"
    if args.output:
        args.output.mkdir(parents=True, exist_ok=False)
        output = args.output.resolve()
    else:
        output = Path(tempfile.mkdtemp(prefix="workspace-generation-"))
    template = args.template.resolve()
    commands = []
    print(f"Evidence and generated projects: {output}", flush=True)

    def run(command, *, cwd=output, env=None, succeeds=True):
        print(f"$ {shlex.join([str(value) for value in command])}", flush=True)
        result = subprocess.run(
            [str(value) for value in command], cwd=cwd, env=env,
            capture_output=True, text=True, timeout=600,
        )
        commands.append({
            "command": [str(value) for value in command], "cwd": str(cwd),
            "exit": result.returncode, "expected_success": succeeds,
            "stdout": result.stdout, "stderr": result.stderr,
        })
        if (result.returncode == 0) != succeeds:
            raise AssertionError(
                f"Unexpected exit {result.returncode}: {command}\n"
                f"{result.stdout}\n{result.stderr}"
            )
        return result

    def generate(name, *, source=template, destination=output, extra=(), **kwargs):
        return run([
            "cargo", "generate", "--path", source, "--name", name,
            "--destination", destination, "--silent", "--vcs", "none",
            "--no-workspace", *extra,
        ], **kwargs)

    def metadata(path):
        return json.loads(run([
            "cargo", "metadata", "--manifest-path", path / "Cargo.toml",
            "--no-deps", "--offline", "--format-version", "1",
        ]).stdout)

    status = "failed"
    try:
        run(["cargo", "generate", "--version"])
        run(["rustc", "--version"])
        # Names and substitutions are checked against Cargo's actual parser.
        for name, extra in (("workspace-contract", ()), ("workspace_contract", ("--force",)),
                            ("workspace-options", ("-d", "with_clients=true", "-d", "with_packages=true"))):
            generate(name, extra=(*extra, "-d", "description=Contract workspace"))
            project = output / name
            root = read_manifest(project / "Cargo.toml")
            assert "package" not in root
            assert root["workspace"]["members"] == ["bin/*", "cmp/*", "crates/*"] + (
                ["clients/*"] if name == "workspace-options" else [])
            assert root["workspace"]["default-members"] == ["crates/starter", "bin/cli"]
            assert set(root["profile"]) == {"dev", "release", "wasm-dev", "wasm-release"}
            assert root["workspace"]["metadata"]["release"]["tag-name"] == "v{{version}}"
            assert (project / "clients").exists() == (name == "workspace-options")
            assert (project / "packages").exists() == (name == "workspace-options")
            assert root["workspace"]["resolver"] == "3"
            assert root["workspace"]["package"]["rust-version"] == "1.99.1"
            assert root["workspace"]["lints"]["rust"]["unsafe_code"] == "forbid"
            assert root["workspace"]["dependencies"]["thiserror"]["default-features"] is False
            starter = read_manifest(project / "crates/starter/Cargo.toml")
            assert "workspace" not in starter and "profile" not in starter
            assert starter["lints"] == {"workspace": True}
            for field in ("authors", "categories", "description", "documentation", "edition",
                          "homepage", "keywords", "license", "readme", "repository", "rust-version", "version"):
                assert starter["package"][field] == {"workspace": True}, field
            parent_before = hashlib.sha256((project / "Cargo.toml").read_bytes()).hexdigest()
            info = metadata(project)
            inherited = next(package for package in info["packages"]
                             if package["name"] == f"{name}-starter")
            for field in ("authors", "description", "edition", "license", "repository", "version"):
                assert inherited[field] == root["workspace"]["package"][field], field
            assert inherited["rust_version"] == root["workspace"]["package"]["rust-version"]
            expected = {f"{name}-starter", f"{name}-cli", f"{name}-component"}
            if name == "workspace-options":
                expected.add(f"{name}-client")
            assert {package["name"] for package in info["packages"]} == expected
            assert len(info["workspace_members"]) == len(expected)
            assert not inherited["dependencies"]
            assert inherited["publish"] == []
            for package in info["packages"]:
                assert "profile" not in read_manifest(Path(package["manifest_path"]))
                readme = Path(package["manifest_path"]).parent / package["readme"]
                assert readme.resolve() == (project / "README.md").resolve()
                for field in ("authors", "categories", "documentation", "edition", "homepage",
                              "keywords", "license", "repository", "version"):
                    assert package[field] == root["workspace"]["package"][field], field
            assert (project / "LICENSE").read_bytes() == (template / "LICENSE").read_bytes()
            for forbidden in (".github", "AGENTS.md", "scripts", "hooks", "flake.nix", ".git"):
                assert not (project / forbidden).exists(), forbidden
            for path in project.rglob("*"):
                if path.is_file():
                    text = path.read_text()
                    assert "{{" not in text.replace("v{{version}}", "") and "{%" not in text, path
                    assert "axiom" not in text.lower(), path
            run(["cargo", "fmt", "--all", "--", "--check"], cwd=project)
            assert hashlib.sha256((project / "Cargo.toml").read_bytes()).hexdigest() == parent_before

        # These values used to silently generate malformed TOML.
        for index, value in enumerate(('Quoted "description"', "back\\slash", "two\nlines")):
            generate(f"bad-description-{index}", extra=("-d", f"description={value}"), succeeds=False)
        generate("bad-alias", extra=("-d", "alias=invalid/owner"), succeeds=False)
        for index, value in enumerate(('Quoted "author"', "back\\slash", "two\nlines")):
            env = dict(os.environ, CARGO_NAME=value, CARGO_EMAIL="author@example.com")
            result = generate(f"bad-author-{index}", env=env, succeeds=False)
            assert "Cargo author must not contain" in result.stderr

        # --force intentionally bypasses name normalization, not Cargo's validation.
        generate("invalid.name", extra=("--force",))
        result = run([
            "cargo", "metadata", "--no-deps", "--offline", "--format-version", "1",
        ], cwd=output / "invalid.name", succeeds=False)
        assert "invalid character" in result.stderr

        if any((args.base, args.cli, args.mcp)):
            project = output / "workspace-contract"
            manifest = project / "Cargo.toml"
            before = hashlib.sha256(manifest.read_bytes()).hexdigest()
            expected_names = {"workspace-contract-starter", "workspace-contract-cli",
                              "workspace-contract-component"}
            for kind in ("base", "cli", "mcp"):
                if not getattr(args, kind):
                    continue
                source = getattr(args, kind).resolve()
                name = f"member-{kind}"
                generate(name, source=source, destination=project / ("crates" if kind == "base" else "bin"),
                         extra=("-d", "workspace-member=true"))
                expected_names.add(name)
                member = project / ("crates" if kind == "base" else "bin") / name
                data = read_manifest(member / "Cargo.toml")
                assert "workspace" not in data and "profile" not in data
                assert data["lints"] == {"workspace": True}
                for field in ("authors", "edition", "license", "repository", "rust-version", "version"):
                    assert data["package"][field] == {"workspace": True}, (name, field)
                for section in ("dependencies", "dev-dependencies", "build-dependencies"):
                    for dependency in data.get(section, {}).values():
                        assert dependency["workspace"] is True
                        assert "version" not in dependency
                for forbidden in (".git", "Cargo.lock", "target"):
                    assert not (member / forbidden).exists(), (name, forbidden)
                assert hashlib.sha256(manifest.read_bytes()).hexdigest() == before
            info = metadata(project)
            assert {package["name"] for package in info["packages"]} == expected_names
            root_package = read_manifest(manifest)["workspace"]["package"]
            for package in info["packages"]:
                for field in ("authors", "edition", "license", "repository", "version"):
                    assert package[field] == root_package[field], (package["name"], field)
                assert package["rust_version"] == root_package["rust-version"]
            run(["cargo", "fmt", "--all", "--", "--check"], cwd=project)
            orphan_source = next(value for value in (args.base, args.cli, args.mcp) if value)
            generate("orphan-member", source=orphan_source.resolve(), extra=("-d", "workspace-member=true"))
            result = run([
                "cargo", "metadata", "--no-deps", "--offline", "--format-version", "1",
            ], cwd=output / "orphan-member", succeeds=False)
            assert "workspace" in result.stderr

        root_manifest = output / "workspace-contract" / "Cargo.toml"
        parent_before = hashlib.sha256(root_manifest.read_bytes()).hexdigest()
        run_cargo_checks(output, args.mode, run)
        assert hashlib.sha256(root_manifest.read_bytes()).hexdigest() == parent_before

        if args.mode == "all":
            project = output / "workspace-contract"
            run(["cargo", "test", "--workspace", "--all-features"], cwd=output / "workspace-options")
            run(["cargo", "check", "-p", "workspace-options-client", "--lib",
                 "--no-default-features", "--features", "alloc"], cwd=output / "workspace-options")
            run(["cargo", "check", "-p", "workspace-contract-starter", "--lib",
                 "--no-default-features", "--features", "alloc"], cwd=project)
            result = run(["cargo", "check", "-p", "workspace-contract-starter", "--lib",
                          "--no-default-features"], cwd=project, succeeds=False)
            assert "Enable `alloc` or `std`" in result.stderr
            for package in ("workspace-contract-cli", "workspace-contract-component"):
                result = run(["cargo", "run", "--quiet", "-p", package], cwd=project)
                assert result.stdout == "workspace-contract 0.0.0\n"
            run(["cargo", "doc", "--workspace", "--no-deps"], cwd=project)
            for profile in ("release", "wasm-dev", "wasm-release"):
                run(["cargo", "build", "--workspace", "--profile", profile], cwd=project)
            if args.base:
                for features in ("alloc", "alloc,serde", "json", "wasm_bindgen",
                                 "std,json,wasm_bindgen"):
                    run(["cargo", "check", "-p", "member-base", "--lib",
                         "--no-default-features", "--features", features], cwd=project)
                    run(["cargo", "test", "-p", "member-base",
                         "--no-default-features", "--features", features], cwd=project)
                run(["cargo", "clippy", "--workspace", "--all-targets", "--all-features",
                     "--", "-D", "warnings"], cwd=project)
                run(["cargo", "package", "-p", "member-base", "--list", "--allow-dirty"], cwd=project)

        status = "passed"
        print(f"PASS: {len(commands)} commands; generation contract verified", flush=True)
    finally:
        (output / "results.json").write_text(json.dumps({
            "status": status, "template": str(template), "commands": commands,
        }, indent=2) + "\n")


if __name__ == "__main__":
    main()
