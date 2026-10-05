#!/usr/bin/env python3
"""Exercise real cargo-generate outputs without running a Rust compilation."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib


def read_manifest(path):
    return tomllib.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--base", type=Path)
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--mcp", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if any((args.base, args.cli, args.mcp)) and not all((args.base, args.cli, args.mcp)):
        parser.error("--base, --cli, and --mcp must be provided together")
    if args.output:
        args.output.mkdir(parents=True, exist_ok=False)
        output = args.output.resolve()
    else:
        output = Path(tempfile.mkdtemp(prefix="workspace-generation-"))
    template = args.template.resolve()
    commands = []
    print(f"Evidence and generated projects: {output}", flush=True)

    def run(command, *, cwd=output, env=None, succeeds=True):
        result = subprocess.run(
            [str(value) for value in command], cwd=cwd, env=env,
            capture_output=True, text=True, timeout=60,
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
        for name, extra in (("workspace-contract", ()), ("workspace_contract", ("--force",))):
            generate(name, extra=(*extra, "-d", "description=Contract workspace"))
            project = output / name
            root = read_manifest(project / "Cargo.toml")
            assert "package" not in root
            assert root["workspace"]["members"] == ["crates/*"]
            assert root["workspace"]["resolver"] == "3"
            assert root["workspace"]["package"]["rust-version"] == "1.96.0"
            assert root["workspace"]["lints"]["rust"]["unsafe_code"] == "forbid"
            assert root["workspace"]["dependencies"]["thiserror"]["default-features"] is False
            info = metadata(project)
            assert [package["name"] for package in info["packages"]] == [f"{name}-starter"]
            assert len(info["workspace_members"]) == 1
            assert not info["packages"][0]["dependencies"]
            assert info["packages"][0]["publish"] == []
            assert (project / "LICENSE").read_bytes() == (template / "LICENSE").read_bytes()
            for forbidden in (".github", "AGENTS.md", "scripts", "hooks", "flake.nix", ".git"):
                assert not (project / forbidden).exists(), forbidden
            for path in project.rglob("*"):
                if path.is_file():
                    text = path.read_text()
                    assert "{{" not in text and "{%" not in text, path
                    assert "axiom" not in text.lower(), path
            run(["cargo", "fmt", "--all", "--", "--check"], cwd=project)

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

        if args.base:
            project = output / "workspace-contract"
            manifest = project / "Cargo.toml"
            before = hashlib.sha256(manifest.read_bytes()).hexdigest()
            expected_names = {"workspace-contract-starter"}
            for kind in ("base", "cli", "mcp"):
                source = getattr(args, kind).resolve()
                name = f"member-{kind}"
                generate(name, source=source, destination=project / "crates",
                         extra=("-d", "workspace-member=true"))
                expected_names.add(name)
                member = project / "crates" / name
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
            generate("orphan-member", source=args.base.resolve(), extra=("-d", "workspace-member=true"))
            result = run([
                "cargo", "metadata", "--no-deps", "--offline", "--format-version", "1",
            ], cwd=output / "orphan-member", succeeds=False)
            assert "workspace" in result.stderr

        status = "passed"
        print(f"PASS: {len(commands)} commands; generation contract verified", flush=True)
    finally:
        (output / "results.json").write_text(json.dumps({
            "status": status, "template": str(template), "commands": commands,
        }, indent=2) + "\n")


if __name__ == "__main__":
    main()
