#!/usr/bin/env python3
"""Fast regression checks for maintainer CI events and generated Cargo targets."""

import importlib.util
from pathlib import Path
import re
import tempfile
import sys

sys.dont_write_bytecode = True
import unittest

VALIDATOR = 'test-generation.py'
ROOT = Path(__file__).resolve().parents[1]


def section(text, name):
    match = re.search(rf"^{name}:\n((?:[ \t].*\n|\n)*)", text, re.MULTILINE)
    if not match:
        raise AssertionError(f"Missing YAML section: {name}")
    return match.group(1)


class CiPolicy(unittest.TestCase):
    def test_one_canonical_pr_check(self):
        workflow = (ROOT / ".github/workflows/template-check.yml").read_text()
        events = section(workflow, "on")
        self.assertIn("  pull_request:\n", events)
        self.assertIn("branches: [main, master, 'v[0-9]*.[0-9]*.[0-9]*']", events)
        self.assertIn("types: [opened, reopened, synchronize]", events)
        self.assertEqual(re.findall(r"^  ([a-z_]+):", events, re.MULTILINE), ["pull_request"])
        self.assertNotIn("paths:", events)
        self.assertIn("  contents: read\n", section(workflow, "permissions"))
        self.assertIn("runs-on: ubuntu-latest", workflow)
        self.assertRegex(workflow, r"timeout-minutes: [1-9][0-9]?\b")
        self.assertIn("cache: false", workflow)
        self.assertNotIn("sccache", workflow)
        self.assertIn("toolchain: stable", workflow)
        self.assertIn("components: rustfmt, clippy", workflow)
        self.assertIn("cargo-generate --version 0.23.8 --locked", workflow)
        self.assertIn("--mode all", workflow)
        self.assertNotIn("secrets.", workflow)

    def test_legacy_events_are_preserved_without_pr_or_branch_push(self):
        for mode in ("build", "test", "clippy", "bench"):
            with self.subTest(mode=mode):
                workflow = (ROOT / f".github/workflows/cargo-{mode}.yml").read_text()
                events = section(workflow, "on")
                self.assertEqual(set(re.findall(r"^  ([a-z_]+):", events, re.MULTILINE)),
                                 {"push", "repository_dispatch", "workflow_dispatch"})
                self.assertNotIn("branches:", events)
                for tag in ("latest", "v[0-9]*", "v[0-9]*.[0-9]*.[0-9]*"):
                    self.assertIn(f"      - {tag}\n", events)
                expected = "[clippy, cargo-clippy]" if mode == "clippy" else f"[cargo-{mode}]"
                self.assertIn(f"types: {expected}", events)
                self.assertIn(f"--mode {mode}", workflow)
                self.assertIn("cache: false", workflow)
                self.assertIn("runs-on: ${{ inputs.runner || 'ubuntu-latest' }}", workflow)
                if mode != "clippy":
                    self.assertIn("toolchain: ${{ inputs.toolchain || 'stable' }}", workflow)
                    self.assertIn("CARGO_BUILD_TARGET: ${{ inputs.target || 'x86_64-unknown-linux-gnu' }}", workflow)
                self.assertNotIn("--features full", workflow)
                self.assertNotIn("axiom", workflow.lower())

    def test_selected_toolchain_reaches_temporary_fixture_commands(self):
        for mode in ("all", "build", "test", "clippy", "bench"):
            with self.subTest(mode=mode):
                name = "template-check" if mode == "all" else f"cargo-{mode}"
                workflow = (ROOT / f".github/workflows/{name}.yml").read_text()
                expected = ("stable" if mode in ("all", "clippy")
                            else "${{ inputs.toolchain || 'stable' }}")
                setup = re.search(r"^      - name: Setup Rust\n((?:        .*\n|\n)*)",
                                  workflow, re.MULTILINE).group(1)
                validation = re.search(
                    r"^      - name: Validate generated projects\n((?:        .*\n|\n)*)",
                    workflow, re.MULTILINE).group(1)
                self.assertIn(f"          toolchain: {expected}\n", setup)
                self.assertIn(f"        env:\n          RUSTUP_TOOLCHAIN: {expected}\n", validation)
                self.assertIn('--output "$RUNNER_TEMP/template-check"', validation)

    def test_all_cargo_targets_are_generated_and_bench_is_compile_only(self):
        validator = ROOT / "scripts" / VALIDATOR
        spec = importlib.util.spec_from_file_location("validator", validator)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            # A missing or unexpanded fixture must stop before native Cargo runs.
            calls = []
            with self.assertRaises(FileNotFoundError):
                module.run_cargo_checks(output, "clippy", calls.append)
            self.assertEqual(calls, [])
            command = module.cargo_commands(output, "clippy")[0]
            manifest = Path(command[command.index("--manifest-path") + 1])
            manifest.parent.mkdir(parents=True)
            manifest.write_text('[package]\nname = "{{ project-name }}"\n{% if workspace-member %}\n')
            with self.assertRaises(ValueError):
                module.run_cargo_checks(output, "clippy", calls.append)
            self.assertEqual(calls, [])
            for mode in ("all", "build", "test", "clippy", "bench"):
                commands = module.cargo_commands(output, mode)
                self.assertTrue(commands, mode)
                for command in commands:
                    self.assertEqual(command[0], "cargo")
                    self.assertIn("--manifest-path", command)
                    manifest = Path(command[command.index("--manifest-path") + 1])
                    self.assertTrue(manifest.is_relative_to(output), command)
                    self.assertNotEqual(manifest, ROOT / "Cargo.toml")
                    self.assertNotIn("full", command)
                    if command[1] == "bench":
                        self.assertIn("--no-run", command)
                if mode == "all":
                    self.assertIn("test", {command[1] for command in commands})
                    self.assertIn("clippy", {command[1] for command in commands})
                if mode == "bench":
                    self.assertTrue(all(command[1] == "bench" for command in commands))


if __name__ == "__main__":
    unittest.main()
