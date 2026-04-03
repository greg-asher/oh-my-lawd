from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

from scripts.oh_my_lawd_build import (
    PhaseSpec,
    RunnerPaths,
    build_parser,
    load_run_state,
    run_phase,
    run_pipeline,
    should_continue_build_loop,
    validate_required_outputs,
)


def make_args(**overrides: object) -> Namespace:
    defaults = {
        "resume": False,
        "max_build_iterations": 25,
        "codex_bin": "codex",
        "model": None,
        "profile": None,
        "dry_run": False,
        "verbose": False,
    }
    defaults.update(overrides)
    return Namespace(**defaults)


def seed_repo(repo_root: Path) -> None:
    (repo_root / "spec").mkdir(parents=True, exist_ok=True)
    (repo_root / "README.md").write_text("# demo\n")
    for name in ("01-spec2plan.md", "02-plan2tasks.md", "03-tasks2build.md"):
        prompt_path = repo_root / "prompt-pack" / name
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(f"# {name}\n")


class ParserTests(unittest.TestCase):
    def test_parser_defaults(self):
        args = build_parser().parse_args([])
        self.assertFalse(args.resume)
        self.assertEqual(args.max_build_iterations, 25)
        self.assertEqual(args.codex_bin, "codex")
        self.assertIsNone(args.model)
        self.assertIsNone(args.profile)
        self.assertFalse(args.dry_run)
        self.assertFalse(args.verbose)


class RunnerPathsTests(unittest.TestCase):
    def test_runner_paths_are_repo_relative(self):
        paths = RunnerPaths(Path("/tmp/demo"))
        self.assertEqual(paths.state_dir, Path("/tmp/demo/.ohmylawd"))
        self.assertEqual(paths.logs_dir, Path("/tmp/demo/.ohmylawd/logs"))
        self.assertEqual(paths.run_state_path, Path("/tmp/demo/.ohmylawd/run-state.json"))


class ValidationTests(unittest.TestCase):
    def test_validate_required_outputs_reports_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            phase = PhaseSpec(
                key="01-spec2plan",
                prompt_path=repo_root / "prompt-pack/01-spec2plan.md",
                required_outputs=(
                    repo_root / "plan/README.md",
                    repo_root / "plan/system-summary.md",
                ),
                log_name="01-spec2plan.log",
            )
            missing = validate_required_outputs(phase)
            self.assertEqual(
                missing,
                [
                    repo_root / "plan/README.md",
                    repo_root / "plan/system-summary.md",
                ],
            )


class QueueStateTests(unittest.TestCase):
    def test_loop_stops_when_queue_is_exhausted(self):
        queue_state = {
            "ready_tasks": [],
            "blocked_tasks": [],
            "in_progress_tasks": [],
            "completed_tasks": ["TASK-001"],
            "recommended_next_task": None,
            "last_generated_at": "2026-04-03T12:00:00Z",
        }
        self.assertFalse(should_continue_build_loop(queue_state))

    def test_loop_continues_when_ready_task_exists(self):
        queue_state = {
            "ready_tasks": ["TASK-002"],
            "blocked_tasks": [],
            "in_progress_tasks": [],
            "completed_tasks": [],
            "recommended_next_task": "TASK-002",
            "last_generated_at": "2026-04-03T12:00:00Z",
        }
        self.assertTrue(should_continue_build_loop(queue_state))


class RunStateTests(unittest.TestCase):
    def test_load_run_state_returns_none_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = RunnerPaths(Path(tmp))
            self.assertIsNone(load_run_state(paths))


class RunPhaseTests(unittest.TestCase):
    @mock.patch("scripts.oh_my_lawd_build.subprocess.run")
    def test_run_phase_writes_log_and_returns_exit_code(self, run_mock):
        run_mock.return_value = mock.Mock(returncode=0, stdout="ok", stderr="")
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            seed_repo(repo_root)
            phase = PhaseSpec(
                key="01-spec2plan",
                prompt_path=repo_root / "prompt-pack/01-spec2plan.md",
                required_outputs=(),
                log_name="01-spec2plan.log",
            )
            paths = RunnerPaths(repo_root)
            result = run_phase(phase, repo_root, paths, make_args())
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.command[-1], "-")
            self.assertTrue(result.log_path.exists())
            self.assertIn("=== PROMPT ===", result.log_path.read_text())
            run_mock.assert_called_once()

    def test_run_phase_dry_run_writes_command_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            seed_repo(repo_root)
            phase = PhaseSpec(
                key="01-spec2plan",
                prompt_path=repo_root / "prompt-pack/01-spec2plan.md",
                required_outputs=(),
                log_name="01-spec2plan.log",
            )
            paths = RunnerPaths(repo_root)
            result = run_phase(phase, repo_root, paths, make_args(dry_run=True))
            self.assertEqual(result.exit_code, 0)
            self.assertIn("DRY RUN", result.log_path.read_text())


class PipelineTests(unittest.TestCase):
    @mock.patch("scripts.oh_my_lawd_build.ensure_codex_exists")
    def test_run_pipeline_dry_run_writes_three_logs(self, _ensure_codex):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            seed_repo(repo_root)
            exit_code = run_pipeline(repo_root, make_args(dry_run=True))
            self.assertEqual(exit_code, 0)
            logs_dir = repo_root / ".ohmylawd/logs"
            self.assertTrue((logs_dir / "01-spec2plan.log").exists())
            self.assertTrue((logs_dir / "02-plan2tasks.log").exists())
            self.assertTrue((logs_dir / "03-tasks2build-001.log").exists())

    @mock.patch("scripts.oh_my_lawd_build.ensure_codex_exists")
    @mock.patch("scripts.oh_my_lawd_build.run_phase")
    def test_run_pipeline_completes_when_queue_is_exhausted(self, run_phase_mock, _ensure_codex):
        run_phase_mock.side_effect = [
            mock.Mock(exit_code=0, command=["codex"], log_path=Path("/tmp/01.log")),
            mock.Mock(exit_code=0, command=["codex"], log_path=Path("/tmp/02.log")),
            mock.Mock(exit_code=0, command=["codex"], log_path=Path("/tmp/03.log")),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            seed_repo(repo_root)
            for relative in (
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
            ):
                path = repo_root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("ok\n")
            (repo_root / "tasks/TASK-001.md").write_text("# Task\n")
            (repo_root / "tasks/queue-state.json").write_text(
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

            exit_code = run_pipeline(repo_root, make_args())

            self.assertEqual(exit_code, 0)
            state = json.loads((repo_root / ".ohmylawd/run-state.json").read_text())
            self.assertEqual(state["status"], "completed")
            self.assertEqual(state["build_iterations"], 1)

    @mock.patch("scripts.oh_my_lawd_build.ensure_codex_exists")
    @mock.patch("scripts.oh_my_lawd_build.run_phase")
    def test_run_pipeline_resumes_from_build_loop_iteration_plus_one(self, run_phase_mock, _ensure_codex):
        run_phase_mock.return_value = mock.Mock(
            exit_code=0,
            command=["codex"],
            log_path=Path("/tmp/03.log"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            seed_repo(repo_root)
            (repo_root / "tasks").mkdir(parents=True, exist_ok=True)
            (repo_root / "tasks/queue-state.json").write_text(
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
            state = {
                "status": "running",
                "current_phase": "03-tasks2build",
                "completed_phases": ["01-spec2plan", "02-plan2tasks"],
                "build_iterations": 2,
                "last_exit_code": 0,
                "last_command": ["codex"],
                "last_log_path": "/tmp/old.log",
                "updated_at": "2026-04-03T12:00:00Z",
            }
            paths = RunnerPaths(repo_root)
            paths.state_dir.mkdir(parents=True, exist_ok=True)
            paths.run_state_path.write_text(json.dumps(state))

            exit_code = run_pipeline(repo_root, make_args(resume=True))

            self.assertEqual(exit_code, 0)
            first_phase = run_phase_mock.call_args_list[0].args[0]
            self.assertEqual(first_phase.log_name, "03-tasks2build-003.log")


if __name__ == "__main__":
    unittest.main()
