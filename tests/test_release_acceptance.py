from __future__ import annotations

import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.oh_my_lawd_build import build_parser, dispatch_command, normalize_command_argv
from runtime.state_store import load_run_state

REPO_ROOT = Path(__file__).resolve().parent.parent


def _dispatch_state_show(run_state_path: Path) -> dict:
    args = build_parser().parse_args(
        normalize_command_argv(
            [
                "state",
                "show",
                "--run-state-path",
                str(run_state_path),
                "--now-timestamp",
                "2026-04-03T20:45:00Z",
            ]
        )
    )
    with mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
        exit_code = dispatch_command(REPO_ROOT, args)
    if exit_code != 0:
        raise AssertionError(f"state show failed for {run_state_path}")
    return json.loads(stdout.getvalue())


class ReleaseAcceptanceTests(unittest.TestCase):
    def test_release_evidence_inputs_are_valid_runtime_state_payloads(self):
        for path in sorted((REPO_ROOT / "docs" / "release-evidence" / "inputs").glob("*.json")):
            with self.subTest(path=path.name):
                run_state = load_run_state(path)
                self.assertEqual(run_state.version, "1.0.0")

    def test_release_evidence_state_show_surfaces_provider_loop_and_recovery_failures(self):
        expectations = {
            "w7-provider-rejection-run-state.json": ("failed_unresolved", "provider_failure"),
            "w8-loop-contained-run-state.json": ("failed_unresolved", "tool_loop_contained"),
            "w9-failed-resume-run-state.json": ("failed_unresolved", "dead_end_prevented"),
        }
        for filename, (expected_state, expected_root_cause) in expectations.items():
            with self.subTest(filename=filename):
                projection = _dispatch_state_show(
                    REPO_ROOT / "docs" / "release-evidence" / "inputs" / filename
                )
                self.assertEqual(projection["projected_state"], expected_state)
                self.assertEqual(
                    projection["explanation"]["root_cause_category"],
                    expected_root_cause,
                )
                self.assertTrue(projection["next_commands"])
                self.assertTrue(projection["explanation"]["remediation_commands"])

    def test_cold_start_commands_on_real_cli_surface_are_executable(self):
        help_result = subprocess.run(
            ["./bin/oh-my-lawd-build", "--help"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("pipeline preview", help_result.stdout)

        with tempfile.TemporaryDirectory() as tmp:
            repo_copy = Path(tmp) / "oh-my-lawd"
            shutil.copytree(REPO_ROOT, repo_copy, dirs_exist_ok=True)
            preview_result = subprocess.run(
                ["./bin/oh-my-lawd-build", "pipeline", "preview", "--max-build-iterations", "5"],
                cwd=repo_copy,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(preview_result.returncode, 0)

    def test_readme_uses_runtime_state_example_instead_of_runner_state(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            "docs/release-evidence/inputs/w7-provider-rejection-run-state.json",
            readme,
        )
        self.assertIn("00-spec2slices.md", readme)
        self.assertIn("07-whole-spec-audit", readme)
        self.assertIn(
            "`state show` expects a persisted runtime `run_state` JSON",
            readme,
        )


if __name__ == "__main__":
    unittest.main()
