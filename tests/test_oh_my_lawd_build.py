from __future__ import annotations

import io
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
    format_runner_event,
    load_run_state,
    run_phase,
    run_pipeline,
    stream_supports_color,
    should_continue_build_loop,
    validate_queue_state,
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


def create_plan_outputs(repo_root: Path) -> None:
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
    ):
        path = repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok\n")


def create_task_outputs(repo_root: Path, queue_state: dict | None = None) -> None:
    defaults = {
        "ready_tasks": [],
        "blocked_tasks": [],
        "in_progress_tasks": [],
        "completed_tasks": ["TASK-001"],
        "recommended_next_task": None,
        "last_generated_at": "2026-04-03T12:00:00Z",
    }
    payload = defaults if queue_state is None else queue_state
    for relative in (
        "tasks/README.md",
        "tasks/index.md",
        "tasks/task-index.json",
    ):
        path = repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok\n")
    (repo_root / "tasks/TASK-001.md").write_text("# Task\n")
    (repo_root / "tasks/queue-state.json").write_text(json.dumps(payload))


class TTYBuffer(io.StringIO):
    def __init__(self, initial_value: str = "", *, tty: bool = False) -> None:
        super().__init__(initial_value)
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


class FakeStdin:
    def __init__(self, *, fail_on_write: bool = False, fail_on_close: bool = False) -> None:
        self.buffer: list[str] = []
        self.closed = False
        self.fail_on_write = fail_on_write
        self.fail_on_close = fail_on_close

    def write(self, text: str) -> int:
        if self.fail_on_write:
            raise BrokenPipeError("stdin closed")
        self.buffer.append(text)
        return len(text)

    def close(self) -> None:
        if self.fail_on_close:
            raise BrokenPipeError("stdin already closed")
        self.closed = True


class FakePopen:
    def __init__(
        self,
        *,
        stdout: str,
        stderr: str,
        returncode: int = 0,
        fail_on_write: bool = False,
        fail_on_close: bool = False,
    ) -> None:
        self.stdin = FakeStdin(fail_on_write=fail_on_write, fail_on_close=fail_on_close)
        self.stdout = TTYBuffer(stdout)
        self.stderr = TTYBuffer(stderr)
        self.returncode = returncode
        self.wait_called = False

    def wait(self) -> int:
        self.wait_called = True
        return self.returncode


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


class TerminalFormattingTests(unittest.TestCase):
    def test_format_runner_event_uses_plain_text_without_tty(self):
        rendered = format_runner_event(
            phase_key="01-spec2plan",
            stream="stdout",
            message="hello",
            use_color=False,
        )
        self.assertEqual(rendered, "[01-spec2plan:stdout] hello")

    def test_stream_supports_color_uses_tty_detection(self):
        self.assertTrue(stream_supports_color(TTYBuffer(tty=True)))
        self.assertFalse(stream_supports_color(TTYBuffer(tty=False)))

    @mock.patch("scripts.oh_my_lawd_build.subprocess.Popen")
    def test_run_phase_formats_each_stream_based_on_its_own_tty(self, popen_mock):
        fake_process = FakePopen(stdout="ok stdout\n", stderr="warn stderr\n", returncode=0)
        popen_mock.return_value = fake_process
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
            stdout_buffer = TTYBuffer(tty=False)
            stderr_buffer = TTYBuffer(tty=True)
            with mock.patch("sys.stdout", stdout_buffer), mock.patch("sys.stderr", stderr_buffer):
                run_phase(phase, repo_root, paths, make_args())
            self.assertNotIn("\033[", stdout_buffer.getvalue())
            self.assertIn("\033[", stderr_buffer.getvalue())


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
    def test_validate_queue_state_rejects_non_object(self):
        self.assertEqual(
            validate_queue_state([]),
            ["queue state must be a JSON object"],
        )

    def test_validate_queue_state_rejects_null_task_lists(self):
        queue_state = {
            "ready_tasks": None,
            "blocked_tasks": None,
            "in_progress_tasks": None,
            "completed_tasks": None,
            "recommended_next_task": None,
            "last_generated_at": "2026-04-03T12:00:00Z",
        }
        self.assertEqual(
            validate_queue_state(queue_state),
            [
                "ready_tasks must be a list",
                "blocked_tasks must be a list",
                "in_progress_tasks must be a list",
                "completed_tasks must be a list",
            ],
        )

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
    @mock.patch("scripts.oh_my_lawd_build.subprocess.Popen")
    def test_run_phase_streams_output_and_writes_log(self, popen_mock):
        fake_process = FakePopen(stdout="ok stdout\n", stderr="warn stderr\n", returncode=0)
        popen_mock.return_value = fake_process
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
            stdout_buffer = TTYBuffer(tty=True)
            stderr_buffer = TTYBuffer(tty=True)
            with mock.patch("sys.stdout", stdout_buffer), mock.patch("sys.stderr", stderr_buffer):
                result = run_phase(phase, repo_root, paths, make_args())
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.command[-1], "-")
            self.assertTrue(result.log_path.exists())
            self.assertIn("ok stdout", stdout_buffer.getvalue())
            self.assertIn("warn stderr", stderr_buffer.getvalue())
            self.assertIn("\033[", stderr_buffer.getvalue())
            self.assertIn("ok stdout", result.log_path.read_text())
            self.assertIn("warn stderr", result.log_path.read_text())
            self.assertTrue(fake_process.wait_called)

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

    @mock.patch("scripts.oh_my_lawd_build.subprocess.Popen")
    def test_run_phase_logs_warning_when_subprocess_closes_stdin_early(self, popen_mock):
        fake_process = FakePopen(
            stdout="",
            stderr="codex exited early\n",
            returncode=1,
            fail_on_write=True,
        )
        popen_mock.return_value = fake_process
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
            self.assertEqual(result.exit_code, 1)
            self.assertIn("runner warning: subprocess closed stdin before prompt delivery", result.log_path.read_text())


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
            state = json.loads((repo_root / ".ohmylawd/run-state.json").read_text())
            self.assertEqual(state["status"], "dry_run")
            self.assertEqual(state["completed_phases"], [])

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
            create_plan_outputs(repo_root)
            create_task_outputs(repo_root)

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
            create_plan_outputs(repo_root)
            create_task_outputs(repo_root)
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

    @mock.patch("scripts.oh_my_lawd_build.ensure_codex_exists")
    @mock.patch("scripts.oh_my_lawd_build.run_phase")
    def test_resume_replays_skipped_phases_when_outputs_are_missing(self, run_phase_mock, _ensure_codex):
        run_phase_mock.side_effect = [
            mock.Mock(exit_code=0, command=["codex"], log_path=Path("/tmp/01.log")),
            mock.Mock(exit_code=0, command=["codex"], log_path=Path("/tmp/02.log")),
            mock.Mock(exit_code=0, command=["codex"], log_path=Path("/tmp/03.log")),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            seed_repo(repo_root)
            create_task_outputs(repo_root)
            paths = RunnerPaths(repo_root)
            paths.state_dir.mkdir(parents=True, exist_ok=True)
            paths.run_state_path.write_text(
                json.dumps(
                    {
                        "status": "running",
                        "current_phase": "03-tasks2build",
                        "completed_phases": ["01-spec2plan", "02-plan2tasks"],
                        "build_iterations": 2,
                        "last_exit_code": 0,
                        "last_command": ["codex"],
                        "last_log_path": "/tmp/old.log",
                        "updated_at": "2026-04-03T12:00:00Z",
                    }
                )
            )

            with self.assertRaises(FileNotFoundError):
                run_pipeline(repo_root, make_args(resume=True))
            self.assertEqual(run_phase_mock.call_args_list[0].args[0].key, "01-spec2plan")

    @mock.patch("scripts.oh_my_lawd_build.ensure_codex_exists")
    @mock.patch("scripts.oh_my_lawd_build.run_phase")
    def test_validation_failure_records_failed_state(self, run_phase_mock, _ensure_codex):
        run_phase_mock.return_value = mock.Mock(
            exit_code=0,
            command=["codex"],
            log_path=Path("/tmp/01.log"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            seed_repo(repo_root)

            with self.assertRaises(FileNotFoundError):
                run_pipeline(repo_root, make_args())

            state = json.loads((repo_root / ".ohmylawd/run-state.json").read_text())
            self.assertEqual(state["status"], "failed")
            self.assertEqual(state["current_phase"], "01-spec2plan")
            self.assertIn("did not produce required outputs", state["last_error"])

    @mock.patch("scripts.oh_my_lawd_build.ensure_codex_exists")
    @mock.patch("scripts.oh_my_lawd_build.run_phase")
    def test_resume_after_dry_run_does_not_skip_phase_generation(self, run_phase_mock, _ensure_codex):
        run_phase_mock.side_effect = [
            mock.Mock(exit_code=0, command=["codex"], log_path=Path("/tmp/01.log")),
            mock.Mock(exit_code=0, command=["codex"], log_path=Path("/tmp/02.log")),
            mock.Mock(exit_code=0, command=["codex"], log_path=Path("/tmp/03.log")),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            seed_repo(repo_root)
            paths = RunnerPaths(repo_root)
            paths.state_dir.mkdir(parents=True, exist_ok=True)
            paths.run_state_path.write_text(
                json.dumps(
                    {
                        "status": "dry_run",
                        "current_phase": "03-tasks2build",
                        "completed_phases": ["01-spec2plan", "02-plan2tasks"],
                        "build_iterations": 1,
                        "last_exit_code": 0,
                        "last_command": ["codex"],
                        "last_log_path": "/tmp/old.log",
                        "updated_at": "2026-04-03T12:00:00Z",
                    }
                )
            )

            with self.assertRaises(FileNotFoundError):
                run_pipeline(repo_root, make_args(resume=True))

            self.assertEqual(run_phase_mock.call_args_list[0].args[0].key, "01-spec2plan")


if __name__ == "__main__":
    unittest.main()
