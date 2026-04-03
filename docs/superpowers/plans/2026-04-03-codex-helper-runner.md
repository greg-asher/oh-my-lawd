# Codex Helper Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repo-local CLI that invokes the existing `01 -> 02 -> 03` prompt-pack pipeline through the `codex` CLI, persists runner state under `.ohmylawd/`, and loops `03` until the task queue is exhausted.

**Architecture:** Use an executable shell shim at `bin/oh-my-lawd-build` that delegates to a standard-library-only Python runner in `scripts/oh_my_lawd_build.py`. The Python module owns CLI parsing, subprocess execution, artifact validation, queue-loop control, and persisted runner state, while unit tests use `unittest` and mocks to verify decisions without invoking the real `codex` binary.

**Tech Stack:** POSIX shell, Python 3 standard library (`argparse`, `json`, `pathlib`, `subprocess`, `datetime`, `unittest`, `unittest.mock`)

---

### Task 1: Scaffold the runner entry point and state model

**Files:**
- Create: `bin/oh-my-lawd-build`
- Create: `scripts/oh_my_lawd_build.py`
- Modify: `.gitignore`
- Test: `tests/test_oh_my_lawd_build.py`

- [ ] **Step 1: Write the failing tests for CLI defaults and state-path helpers**

```python
import unittest
from pathlib import Path

from scripts.oh_my_lawd_build import build_parser, RunnerPaths


class ParserTests(unittest.TestCase):
    def test_parser_defaults(self):
        args = build_parser().parse_args([])
        self.assertFalse(args.resume)
        self.assertEqual(args.max_build_iterations, 25)
        self.assertEqual(args.codex_bin, "codex")
        self.assertFalse(args.dry_run)
        self.assertFalse(args.verbose)


class RunnerPathsTests(unittest.TestCase):
    def test_runner_paths_are_repo_relative(self):
        paths = RunnerPaths(Path("/tmp/demo"))
        self.assertEqual(paths.state_dir, Path("/tmp/demo/.ohmylawd"))
        self.assertEqual(paths.logs_dir, Path("/tmp/demo/.ohmylawd/logs"))
        self.assertEqual(paths.run_state_path, Path("/tmp/demo/.ohmylawd/run-state.json"))
```

- [ ] **Step 2: Run the tests to verify the feature is not implemented yet**

Run: `python3 -m unittest tests.test_oh_my_lawd_build -v`
Expected: FAIL with `ModuleNotFoundError` or import errors for `scripts.oh_my_lawd_build`

- [ ] **Step 3: Add the executable wrapper and Python module skeleton**

`bin/oh-my-lawd-build`

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$ROOT_DIR/scripts/oh_my_lawd_build.py" "$@"
```

`scripts/oh_my_lawd_build.py`

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunnerPaths:
    repo_root: Path

    @property
    def state_dir(self) -> Path:
        return self.repo_root / ".ohmylawd"

    @property
    def logs_dir(self) -> Path:
        return self.state_dir / "logs"

    @property
    def run_state_path(self) -> Path:
        return self.state_dir / "run-state.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Oh My Lawd prompt-pack pipeline through Codex."
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-build-iterations", type=int, default=25)
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser


def main() -> int:
    build_parser().parse_args()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`.gitignore`

```gitignore
.ohmylawd/
```

- [ ] **Step 4: Run the targeted tests again**

Run: `python3 -m unittest tests.test_oh_my_lawd_build -v`
Expected: PASS for parser defaults and repo-relative runner paths

- [ ] **Step 5: Commit the scaffold**

```bash
git add .gitignore bin/oh-my-lawd-build scripts/oh_my_lawd_build.py tests/test_oh_my_lawd_build.py
git commit -m "feat: scaffold codex helper runner"
```

### Task 2: Implement phase execution, prompt loading, and artifact validation

**Files:**
- Modify: `scripts/oh_my_lawd_build.py`
- Modify: `tests/test_oh_my_lawd_build.py`
- Test: `tests/test_oh_my_lawd_build.py`

- [ ] **Step 1: Write failing tests for phase metadata and required artifact validation**

```python
import tempfile
import unittest
from pathlib import Path

from scripts.oh_my_lawd_build import PhaseSpec, validate_required_outputs


class ValidationTests(unittest.TestCase):
    def test_validate_required_outputs_reports_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            spec = PhaseSpec(
                key="01-spec2plan",
                prompt_path=repo_root / "prompt-pack/01-spec2plan.md",
                required_outputs=[
                    repo_root / "plan/README.md",
                    repo_root / "plan/system-summary.md",
                ],
                log_name="01-spec2plan.log",
            )
            missing = validate_required_outputs(spec)
            self.assertEqual(
                missing,
                [
                    repo_root / "plan/README.md",
                    repo_root / "plan/system-summary.md",
                ],
            )
```

- [ ] **Step 2: Run the tests to confirm validation helpers do not exist yet**

Run: `python3 -m unittest tests.test_oh_my_lawd_build -v`
Expected: FAIL with import errors for `PhaseSpec` or `validate_required_outputs`

- [ ] **Step 3: Implement phase specs, prompt composition, and validation helpers**

Add to `scripts/oh_my_lawd_build.py`:

```python
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class PhaseSpec:
    key: str
    prompt_path: Path
    required_outputs: list[Path]
    log_name: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_phase_specs(repo_root: Path) -> list[PhaseSpec]:
    return [
        PhaseSpec(
            key="01-spec2plan",
            prompt_path=repo_root / "prompt-pack/01-spec2plan.md",
            required_outputs=[
                repo_root / "plan/README.md",
                repo_root / "plan/system-summary.md",
                repo_root / "plan/spec-map.md",
                repo_root / "plan/domain-glossary.md",
                repo_root / "plan/invariants.md",
                repo_root / "plan/acceptance-matrix.md",
                repo_root / "plan/build-order.md",
                repo_root / "plan/task-graph.md",
                repo_root / "plan/open-questions.md",
                repo_root / "plan/forbidden-shortcuts.md",
                repo_root / "plan/walkthroughs.md",
                repo_root / "plan/implementation-brief.json",
            ],
            log_name="01-spec2plan.log",
        ),
        PhaseSpec(
            key="02-plan2tasks",
            prompt_path=repo_root / "prompt-pack/02-plan2tasks.md",
            required_outputs=[
                repo_root / "tasks/README.md",
                repo_root / "tasks/index.md",
                repo_root / "tasks/task-index.json",
                repo_root / "tasks/queue-state.json",
            ],
            log_name="02-plan2tasks.log",
        ),
    ]


def validate_required_outputs(phase: PhaseSpec) -> list[Path]:
    return [path for path in phase.required_outputs if not path.exists()]


def load_prompt_text(prompt_path: Path, repo_root: Path) -> str:
    body = prompt_path.read_text()
    preamble = "\n".join(
        [
            "You are running inside the Oh My Lawd repository.",
            f"Repository root: {repo_root}",
            "Write artifacts in place in this repository.",
            "Do not prompt for confirmation unless the prompt-pack requires it.",
            "",
        ]
    )
    return f"{preamble}{body}"


def ensure_codex_exists(codex_bin: str) -> None:
    if shutil.which(codex_bin) is None:
        raise FileNotFoundError(f"Codex binary not found on PATH: {codex_bin}")
```

- [ ] **Step 4: Add a subprocess execution wrapper and test it with mocks**

Add to `tests/test_oh_my_lawd_build.py`:

```python
from unittest import mock

from scripts.oh_my_lawd_build import run_phase


class RunPhaseTests(unittest.TestCase):
    @mock.patch("scripts.oh_my_lawd_build.subprocess.run")
    def test_run_phase_writes_log_and_returns_exit_code(self, run_mock):
        run_mock.return_value = mock.Mock(
            returncode=0,
            stdout="ok",
            stderr="",
        )
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            prompt_path = repo_root / "prompt-pack/01-spec2plan.md"
            prompt_path.parent.mkdir(parents=True)
            prompt_path.write_text("phase body")
            phase = PhaseSpec(
                key="01-spec2plan",
                prompt_path=prompt_path,
                required_outputs=[],
                log_name="01-spec2plan.log",
            )
            paths = RunnerPaths(repo_root)
            paths.logs_dir.mkdir(parents=True)
            exit_code = run_phase(phase, repo_root, paths, "codex", dry_run=False)
            self.assertEqual(exit_code, 0)
            self.assertTrue((paths.logs_dir / "01-spec2plan.log").exists())
```

Add to `scripts/oh_my_lawd_build.py`:

```python
def run_phase(
    phase: PhaseSpec,
    repo_root: Path,
    paths: RunnerPaths,
    codex_bin: str,
    dry_run: bool,
) -> int:
    prompt_text = load_prompt_text(phase.prompt_path, repo_root)
    command = [codex_bin, "exec", prompt_text]
    log_path = paths.logs_dir / phase.log_name
    if dry_run:
        log_path.write_text("DRY RUN\n" + " ".join(command) + "\n")
        return 0
    completed = subprocess.run(
        command,
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    log_path.write_text(
        "\n".join(
            [
                f"phase={phase.key}",
                f"started_at={utc_now()}",
                f"command={command}",
                "",
                completed.stdout,
                completed.stderr,
            ]
        )
    )
    return completed.returncode
```

- [ ] **Step 5: Run the full test module**

Run: `python3 -m unittest tests.test_oh_my_lawd_build -v`
Expected: PASS for validation helpers and mocked phase execution

- [ ] **Step 6: Commit phase execution support**

```bash
git add scripts/oh_my_lawd_build.py tests/test_oh_my_lawd_build.py
git commit -m "feat: add prompt-pack phase execution"
```

### Task 3: Implement run-state persistence, resume logic, and the looping `03` build phase

**Files:**
- Modify: `scripts/oh_my_lawd_build.py`
- Modify: `tests/test_oh_my_lawd_build.py`
- Test: `tests/test_oh_my_lawd_build.py`

- [ ] **Step 1: Write failing tests for queue-state stop conditions and resume behavior**

```python
from scripts.oh_my_lawd_build import load_run_state, should_continue_build_loop


class QueueStateTests(unittest.TestCase):
    def test_loop_stops_when_no_ready_or_in_progress_work_remains(self):
        queue_state = {
            "ready_tasks": [],
            "blocked_tasks": [],
            "in_progress_tasks": [],
            "completed_tasks": ["TASK-001"],
            "recommended_next_task": None,
            "last_generated_at": "2026-04-03T12:00:00Z",
        }
        self.assertFalse(should_continue_build_loop(queue_state))


class RunStateTests(unittest.TestCase):
    def test_load_run_state_returns_none_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            paths = RunnerPaths(repo_root)
            self.assertIsNone(load_run_state(paths))
```

- [ ] **Step 2: Run tests to confirm loop-state helpers are still missing**

Run: `python3 -m unittest tests.test_oh_my_lawd_build -v`
Expected: FAIL with import errors for `load_run_state` or `should_continue_build_loop`

- [ ] **Step 3: Implement persisted run state and queue-state decisions**

Add to `scripts/oh_my_lawd_build.py`:

```python
def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_run_state(paths: RunnerPaths, payload: dict) -> None:
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    paths.run_state_path.write_text(json.dumps(payload, indent=2) + "\n")


def load_run_state(paths: RunnerPaths) -> dict | None:
    if not paths.run_state_path.exists():
        return None
    return load_json(paths.run_state_path)


def should_continue_build_loop(queue_state: dict) -> bool:
    return bool(
        queue_state.get("recommended_next_task")
        or queue_state.get("ready_tasks")
        or queue_state.get("in_progress_tasks")
    )
```

- [ ] **Step 4: Implement `03` looping and `main()` orchestration**

Extend `scripts/oh_my_lawd_build.py` with:

```python
def build_loop_phase(repo_root: Path) -> PhaseSpec:
    return PhaseSpec(
        key="03-tasks2build",
        prompt_path=repo_root / "prompt-pack/03-tasks2build.md",
        required_outputs=[repo_root / "tasks/queue-state.json"],
        log_name="03-tasks2build.log",
    )


def next_log_name(iteration: int) -> str:
    return f"03-tasks2build-{iteration:03d}.log"


def run_build_loop(repo_root: Path, paths: RunnerPaths, args: argparse.Namespace) -> int:
    phase = build_loop_phase(repo_root)
    for iteration in range(1, args.max_build_iterations + 1):
        phase = PhaseSpec(
            key=phase.key,
            prompt_path=phase.prompt_path,
            required_outputs=phase.required_outputs,
            log_name=next_log_name(iteration),
        )
        exit_code = run_phase(phase, repo_root, paths, args.codex_bin, args.dry_run)
        save_run_state(
            paths,
            {
                "status": "running" if exit_code == 0 else "failed",
                "current_phase": phase.key,
                "completed_phases": ["01-spec2plan", "02-plan2tasks"],
                "build_iterations": iteration,
                "last_exit_code": exit_code,
                "last_log_path": str(paths.logs_dir / phase.log_name),
                "updated_at": utc_now(),
            },
        )
        if exit_code != 0:
            return exit_code
        queue_state = load_json(repo_root / "tasks/queue-state.json")
        if not should_continue_build_loop(queue_state):
            save_run_state(
                paths,
                {
                    "status": "completed",
                    "current_phase": phase.key,
                    "completed_phases": ["01-spec2plan", "02-plan2tasks", "03-tasks2build"],
                    "build_iterations": iteration,
                    "last_exit_code": 0,
                    "last_log_path": str(paths.logs_dir / phase.log_name),
                    "updated_at": utc_now(),
                },
            )
            return 0
    raise RuntimeError("Exceeded max build iterations without exhausting the task queue")


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    paths = RunnerPaths(repo_root)
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    ensure_codex_exists(args.codex_bin)

    for phase in build_phase_specs(repo_root):
        exit_code = run_phase(phase, repo_root, paths, args.codex_bin, args.dry_run)
        save_run_state(
            paths,
            {
                "status": "running" if exit_code == 0 else "failed",
                "current_phase": phase.key,
                "completed_phases": [],
                "build_iterations": 0,
                "last_exit_code": exit_code,
                "last_log_path": str(paths.logs_dir / phase.log_name),
                "updated_at": utc_now(),
            },
        )
        if exit_code != 0:
            return exit_code
        missing = validate_required_outputs(phase)
        if missing:
            raise FileNotFoundError(f"Missing required outputs for {phase.key}: {missing}")

    return run_build_loop(repo_root, paths, args)
```

- [ ] **Step 5: Add a mocked end-to-end runner test**

Add to `tests/test_oh_my_lawd_build.py`:

```python
class MainFlowTests(unittest.TestCase):
    @mock.patch("scripts.oh_my_lawd_build.ensure_codex_exists")
    @mock.patch("scripts.oh_my_lawd_build.run_phase")
    def test_main_runs_until_queue_exhausted(self, run_phase_mock, _ensure_codex):
        run_phase_mock.side_effect = [0, 0, 0]
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            for relative in [
                "prompt-pack/01-spec2plan.md",
                "prompt-pack/02-plan2tasks.md",
                "prompt-pack/03-tasks2build.md",
                "plan/README.md",
                "plan/system-summary.md",
                "plan/spec-map.md",
                "plan/domain-glossary.md",
                "plan/invariants.md",
                "plan/acceptance-matrix.md",
                "plan/build-order.md",
                "plan/task-graph.md",
                "plan/open-questions.md",
                "plan/forbidden-shortcuts.md",
                "plan/walkthroughs.md",
                "plan/implementation-brief.json",
                "tasks/README.md",
                "tasks/index.md",
                "tasks/task-index.json",
                "tasks/queue-state.json",
            ]:
                path = repo_root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.name == "queue-state.json":
                    path.write_text(
                        json.dumps(
                            {
                                "ready_tasks": [],
                                "blocked_tasks": [],
                                "in_progress_tasks": [],
                                "completed_tasks": ["TASK-001"],
                                "recommended_next_task": None,
                                "last_generated_at": "2026-04-03T12:00:00Z",
                            }
                        )
                    )
                else:
                    path.write_text("ok")
```

- [ ] **Step 6: Run the test suite**

Run: `python3 -m unittest tests.test_oh_my_lawd_build -v`
Expected: PASS for queue exit behavior, run-state persistence, and mocked main flow

- [ ] **Step 7: Commit the autonomous loop**

```bash
git add scripts/oh_my_lawd_build.py tests/test_oh_my_lawd_build.py
git commit -m "feat: add autonomous codex build loop"
```

### Task 4: Document usage and add a dry-run smoke path

**Files:**
- Modify: `README.md`
- Modify: `tests/test_oh_my_lawd_build.py`
- Test: `tests/test_oh_my_lawd_build.py`

- [ ] **Step 1: Write a failing test for dry-run log generation**

```python
class DryRunTests(unittest.TestCase):
    def test_run_phase_dry_run_writes_command_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            prompt_path = repo_root / "prompt-pack/01-spec2plan.md"
            prompt_path.parent.mkdir(parents=True)
            prompt_path.write_text("phase body")
            phase = PhaseSpec(
                key="01-spec2plan",
                prompt_path=prompt_path,
                required_outputs=[],
                log_name="01-spec2plan.log",
            )
            paths = RunnerPaths(repo_root)
            paths.logs_dir.mkdir(parents=True)
            exit_code = run_phase(phase, repo_root, paths, "codex", dry_run=True)
            self.assertEqual(exit_code, 0)
            self.assertIn("DRY RUN", (paths.logs_dir / phase.log_name).read_text())
```

- [ ] **Step 2: Run the suite to verify the dry-run assertion fails before README work**

Run: `python3 -m unittest tests.test_oh_my_lawd_build -v`
Expected: FAIL if dry-run logging is missing or incomplete

- [ ] **Step 3: Update README usage and smoke-test guidance**

Add a new section to `README.md`:

```markdown
## Autonomous Runner

This repository includes a repo-local helper for running the prompt-pack pipeline through the `codex` CLI.

Requirements:
- `codex` installed and available on `PATH`
- Python 3 available locally

Usage:

```bash
./bin/oh-my-lawd-build
```

Useful flags:
- `./bin/oh-my-lawd-build --dry-run`
- `./bin/oh-my-lawd-build --resume`
- `./bin/oh-my-lawd-build --max-build-iterations 10`

Runner state and logs are written to `.ohmylawd/`.
```

- [ ] **Step 4: Run the full test suite**

Run: `python3 -m unittest tests.test_oh_my_lawd_build -v`
Expected: PASS for dry-run logging and all earlier runner tests

- [ ] **Step 5: Run a repo-level smoke check**

Run: `./bin/oh-my-lawd-build --dry-run`
Expected: exit code `0` and creation of `.ohmylawd/logs/` plus dry-run command logs without invoking the real `codex` binary

- [ ] **Step 6: Commit docs and smoke-path updates**

```bash
git add README.md tests/test_oh_my_lawd_build.py
git commit -m "docs: add codex helper runner usage"
```

## Self-Review

Spec coverage for this feature:
- The design requirement is covered by Tasks 1 through 4.
- Repo-local CLI surface is covered by Task 1 and Task 4.
- Autonomous `01 -> 02 -> 03` sequencing is covered by Task 2 and Task 3.
- Resume/debug state under `.ohmylawd/` is covered by Task 1 and Task 3.
- Honest stop conditions and safety-cap behavior are covered by Task 3.

Placeholder scan:
- No `TODO`, `TBD`, or deferred “write tests later” placeholders remain.

Type consistency:
- `RunnerPaths`, `PhaseSpec`, `run_phase`, `load_run_state`, and `should_continue_build_loop` use the same names across tasks.

Plan complete and saved to `docs/superpowers/plans/2026-04-03-codex-helper-runner.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration

2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
