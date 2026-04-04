from __future__ import annotations

import io
import json
import shlex
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

from runtime.operator_commands import help_example_commands
from runtime.product_state_projection import project_persisted_run_state
from scripts.oh_my_lawd_build import (
    QUEUE_STATE_KEYS,
    SPEC_CHECK_RESULT_KEYS,
    WHOLE_SPEC_FIX_SLICE_ID,
    PhaseSpec,
    RunnerPaths,
    build_parser,
    command_taxonomy_snapshot,
    commit_repo_state,
    compose_prompt,
    dispatch_command,
    ensure_clean_worktree,
    load_run_state,
    main,
    normalize_command_argv,
    run_phase,
    run_pipeline,
    should_continue_build_loop,
    validate_queue_state,
    validate_slice_manifest,
    validate_spec_check_result,
    validate_required_outputs,
)


def make_args(**overrides: object) -> Namespace:
    defaults = {
        "resume": False,
        "max_build_iterations": 25,
        "max_slice_retries": 3,
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
    (repo_root / "README.md").write_text("# demo\n", encoding="utf-8")
    for name in (
        "00-spec2slices.md",
        "01-slice2metaplan.md",
        "02-metaplan2detailedplan.md",
        "03-detailedplan2tasks.md",
        "04-tasks2build.md",
        "05-review.md",
        "06-spec-check.md",
        "07-whole-spec-audit.md",
    ):
        prompt_path = repo_root / "prompt-pack" / name
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(f"# {name}\n", encoding="utf-8")


def create_bootstrap_outputs(repo_root: Path, slices: list[dict] | None = None) -> None:
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
        "plan/slices.md",
    ):
        path = repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok\n", encoding="utf-8")

    manifest = {
        "slices": slices
        if slices is not None
        else [
            {
                "slice_id": "SLICE-001",
                "title": "Primary operator surface",
                "goal": "Validate one spec slice.",
                "source_spec_refs": ["spec/product-contract.md#5"],
                "acceptance_gates": ["PX-07"],
                "depends_on_slices": [],
                "status": "ready",
            }
        ]
    }
    (repo_root / "plan/slice-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def create_slice_plan_outputs(repo_root: Path, slice_id: str) -> None:
    (repo_root / f"plan/{slice_id}-metaplan.md").write_text("# Meta Plan\n", encoding="utf-8")
    (repo_root / f"plan/{slice_id}-detailed-plan.md").write_text("# Detailed Plan\n", encoding="utf-8")


def create_task_outputs(
    repo_root: Path,
    *,
    current_slice: str = "SLICE-001",
    queue_state: dict | None = None,
) -> None:
    defaults = {
        "ready_tasks": [],
        "blocked_tasks": [],
        "in_progress_tasks": [],
        "completed_tasks": ["TASK-001"],
        "recommended_next_task": None,
        "last_generated_at": "2026-04-03T12:00:00Z",
        "current_slice": current_slice,
        "slice_status": "building",
        "slice_retry_count": 0,
        "review_status": "not_run",
        "spec_check_status": "not_run",
    }
    payload = defaults if queue_state is None else queue_state
    for relative in (
        "tasks/README.md",
        "tasks/index.md",
    ):
        path = repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok\n", encoding="utf-8")
    (repo_root / "tasks/TASK-001.md").write_text(
        "# Task\n\n## ID\nTASK-001\n\n## Slice ID\n"
        f"{current_slice}\n\n## Relevant Spec References\n- spec/product-contract.md#5\n",
        encoding="utf-8",
    )
    (repo_root / "tasks/task-index.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "id": "TASK-001",
                        "slice_id": current_slice,
                        "source_spec_refs": ["spec/product-contract.md#5"],
                        "status": "completed",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (repo_root / "tasks/queue-state.json").write_text(json.dumps(payload), encoding="utf-8")


def create_review_output(repo_root: Path, slice_id: str, result: str = "pass") -> None:
    path = repo_root / f"tasks/review-{slice_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# Review\n\nResult: {result}\n",
        encoding="utf-8",
    )


def create_spec_check_output(repo_root: Path, slice_id: str, result: str = "pass") -> None:
    payload = {
        "slice_id": slice_id,
        "result": result,
        "summary": "slice check complete",
        "missing_requirements": [] if result == "pass" else ["spec/product-contract.md#5"],
        "verified_code_paths": ["scripts/oh_my_lawd_build.py"],
        "verified_commands": ["./bin/oh-my-lawd-build pipeline run"],
        "verified_outputs": ["tasks/spec-check.json"],
        "requires_replan": result == "fail",
    }
    path = repo_root / f"tasks/spec-check-{slice_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def create_whole_spec_audit(repo_root: Path, result: str = "pass") -> None:
    path = repo_root / "docs/release-evidence/whole-spec-audit.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# Whole Spec Audit\n\nResult: {result}\n", encoding="utf-8")


def _seed_run_state_payload(path: Path, *, state: str = "running") -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "run_state_envelopes.json"
    payload = json.loads(fixture_path.read_text())[0]["payload"]
    payload["execution_status"] = state
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _seed_approval_pending_run_state_payload(path: Path) -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "product_state_projection_cases.json"
    payload = json.loads(fixture_path.read_text())[1]["payload"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _seed_extension_onboarding_inputs(
    repo_root: Path,
    *,
    extension_id: str = "demo-extension",
) -> tuple[Path, Path]:
    manifest_path = repo_root / "extensions" / extension_id / "manifest.json"
    config_path = repo_root / "extensions" / extension_id / "config.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "extension_id": extension_id,
                "display_name": "Demo Extension",
                "entrypoint": "mcp://demo",
            }
        ),
        encoding="utf-8",
    )
    config_path.write_text(json.dumps({"settings": {"enabled": True}}), encoding="utf-8")
    return manifest_path, config_path


def _load_extension_operator_surface_fixture() -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / "extension_onboarding_operator_surface.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


class ParserTests(unittest.TestCase):
    def test_parser_defaults(self):
        args = build_parser().parse_args(normalize_command_argv([]))
        self.assertEqual(args.command_group, "pipeline")
        self.assertEqual(args.pipeline_action, "run")
        self.assertEqual(args.max_slice_retries, 3)
        self.assertFalse(args.resume)
        self.assertEqual(args.max_build_iterations, 25)
        self.assertEqual(args.codex_bin, "codex")
        self.assertFalse(args.dry_run)

    def test_parser_help_lists_grouped_operator_commands(self):
        help_text = build_parser().format_help()
        pipeline_help = io.StringIO()
        with self.assertRaises(SystemExit):
            with mock.patch("sys.stdout", pipeline_help):
                build_parser().parse_args(["pipeline", "run", "--help"])
        self.assertIn("pipeline run", help_text)
        self.assertIn("pipeline preview", help_text)
        self.assertIn("--max-slice-retries", pipeline_help.getvalue())
        self.assertIn("state show", help_text)
        self.assertIn("extension onboard", help_text)

    def test_command_taxonomy_snapshot_matches_expected_fixture(self):
        fixture_path = Path(__file__).parent / "fixtures" / "operator_command_taxonomy.json"
        expected = json.loads(fixture_path.read_text())
        self.assertEqual(command_taxonomy_snapshot(), expected)

    def test_help_example_commands_snapshot_matches_expected_fixture(self):
        fixture_path = Path(__file__).parent / "fixtures" / "operator_help_commands.json"
        expected = json.loads(fixture_path.read_text())
        self.assertEqual(list(help_example_commands()), expected)


class CommandRoutingTests(unittest.TestCase):
    def test_normalize_command_argv_defaults_to_pipeline_run(self):
        self.assertEqual(normalize_command_argv(None), ["pipeline", "run"])
        self.assertEqual(normalize_command_argv([]), ["pipeline", "run"])

    def test_normalize_command_argv_maps_legacy_root_flags_to_pipeline_run(self):
        self.assertEqual(
            normalize_command_argv(["--dry-run", "--verbose"]),
            ["pipeline", "run", "--dry-run", "--verbose"],
        )

    @mock.patch("scripts.oh_my_lawd_build.dispatch_command")
    @mock.patch("scripts.oh_my_lawd_build.default_repo_root")
    def test_main_routes_legacy_invocation_to_real_pipeline_command(self, default_repo_root_mock, dispatch_mock):
        default_repo_root_mock.return_value = Path("/tmp/demo")
        dispatch_mock.return_value = 0

        exit_code = main(["--dry-run"])

        self.assertEqual(exit_code, 0)
        _, args = dispatch_mock.call_args.args
        self.assertEqual(args.command_group, "pipeline")
        self.assertEqual(args.pipeline_action, "run")
        self.assertTrue(args.dry_run)

    def test_dispatch_state_show_projects_persisted_run_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_state_path = Path(tmp) / "runtime-run-state.json"
            fixture_path = Path(__file__).parent / "fixtures" / "run_state_envelopes.json"
            payload = json.loads(fixture_path.read_text())[0]["payload"]
            runtime_state_path.write_text(json.dumps(payload), encoding="utf-8")

            args = Namespace(
                command_group="state",
                state_action="show",
                run_state_path=str(runtime_state_path),
                now_timestamp="2026-04-03T16:15:05Z",
                freshness_slo_seconds=30,
                verbose=False,
            )
            with mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
                exit_code = dispatch_command(Path("/tmp/unused"), args)

            self.assertEqual(exit_code, 0)
            projection = json.loads(stdout.getvalue())
            self.assertEqual(projection["run_id"], "run-runtime-only")
            self.assertEqual(projection["projected_state"], "running")
            self.assertIn("latest_assistant_response", projection)

    def test_dispatch_state_show_exposes_runtime_defined_approval_scope_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_state_path = Path(tmp) / "approval-pending-run-state.json"
            _seed_approval_pending_run_state_payload(runtime_state_path)

            args = Namespace(
                command_group="state",
                state_action="show",
                run_state_path=str(runtime_state_path),
                now_timestamp="2026-04-03T18:10:15Z",
                freshness_slo_seconds=30,
                verbose=False,
            )
            with mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
                exit_code = dispatch_command(Path("/tmp/unused"), args)

            self.assertEqual(exit_code, 0)
            projection = json.loads(stdout.getvalue())
            self.assertEqual(projection["projected_state"], "approval_pending")
            self.assertTrue(projection["approval_scope_actions"])

    def test_dispatch_extension_onboard_exposes_staged_projection_and_check_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            manifest_path, config_path = _seed_extension_onboarding_inputs(repo_root)
            expected = _load_extension_operator_surface_fixture()
            args = Namespace(
                command_group="extension",
                extension_action="onboard",
                extension_id="demo-extension",
                manifest_path=str(manifest_path),
                config_path=str(config_path),
                state_dir=".ohmylawd/extensions",
                now_timestamp="2026-04-03T19:10:00Z",
                verbose=False,
            )
            with mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
                exit_code = dispatch_command(repo_root, args)

            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["onboarding_status"], "activated")
            self.assertEqual([stage["stage"] for stage in payload["stages"]], expected["stage_order"])


class CommandParitySmokeTests(unittest.TestCase):
    def _dispatch_rendered_command(self, repo_root: Path, command: str) -> int:
        argv = shlex.split(command)
        self.assertEqual(argv[0], "./bin/oh-my-lawd-build")
        args = build_parser().parse_args(normalize_command_argv(argv[1:]))
        if args.command_group == "pipeline":
            with mock.patch("scripts.oh_my_lawd_build.run_pipeline", return_value=0) as run_pipeline_mock:
                exit_code = dispatch_command(repo_root, args)
            run_pipeline_mock.assert_called_once()
            return exit_code

        with mock.patch("sys.stdout", new_callable=io.StringIO):
            return dispatch_command(repo_root, args)

    def test_help_commands_are_executable_as_rendered(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            seed_repo(repo_root)
            create_bootstrap_outputs(repo_root)
            create_task_outputs(repo_root)
            _seed_run_state_payload(repo_root / ".ohmylawd/runtime-run-state.json")
            _seed_extension_onboarding_inputs(repo_root)

            for command in help_example_commands():
                with self.subTest(command=command):
                    self.assertEqual(self._dispatch_rendered_command(repo_root, command), 0)

    def test_projected_next_and_remediation_commands_are_executable_as_rendered(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_state_path = repo_root / ".ohmylawd/runtime-run-state.json"
            _seed_run_state_payload(run_state_path, state="blocked")

            projection = project_persisted_run_state(
                run_state_path,
                now_timestamp="2026-04-03T16:15:05Z",
                operator_run_state_path=str(run_state_path),
            )
            commands = list(projection.next_commands) + list(projection.explanation.remediation_commands)
            for command in commands:
                with self.subTest(command=command):
                    self.assertEqual(self._dispatch_rendered_command(repo_root, command), 0)


class ValidationTests(unittest.TestCase):
    def test_validate_required_outputs_reports_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            phase = PhaseSpec(
                key="00-spec2slices",
                prompt_path=repo_root / "prompt-pack/00-spec2slices.md",
                required_outputs=(repo_root / "plan/README.md", repo_root / "plan/slice-manifest.json"),
                log_name="00-spec2slices.log",
            )
            missing = validate_required_outputs(phase)
            self.assertEqual(missing, [repo_root / "plan/README.md", repo_root / "plan/slice-manifest.json"])

    def test_validate_slice_manifest_rejects_missing_fields(self):
        errors = validate_slice_manifest({"slices": [{"slice_id": "SLICE-001"}]})
        self.assertTrue(errors)

    def test_validate_spec_check_result_rejects_invalid_result(self):
        payload = {
            "slice_id": "SLICE-001",
            "result": "maybe",
            "summary": "bad",
            "missing_requirements": [],
            "verified_code_paths": [],
            "verified_commands": [],
            "verified_outputs": [],
            "requires_replan": False,
        }
        self.assertIn("result must be 'pass' or 'fail'", validate_spec_check_result(payload))


class QueueStateTests(unittest.TestCase):
    def test_validate_queue_state_rejects_non_object(self):
        self.assertEqual(validate_queue_state([]), ["queue state must be a JSON object"])

    def test_validate_queue_state_requires_slice_metadata(self):
        queue_state = {
            "ready_tasks": [],
            "blocked_tasks": [],
            "in_progress_tasks": [],
            "completed_tasks": [],
            "recommended_next_task": None,
            "last_generated_at": "2026-04-03T12:00:00Z",
        }
        errors = validate_queue_state(queue_state)
        for key in QUEUE_STATE_KEYS[6:]:
            self.assertTrue(any(key in error for error in errors))

    def test_loop_stops_when_queue_is_exhausted(self):
        queue_state = {
            "ready_tasks": [],
            "blocked_tasks": [],
            "in_progress_tasks": [],
            "completed_tasks": ["TASK-001"],
            "recommended_next_task": None,
            "last_generated_at": "2026-04-03T12:00:00Z",
            "current_slice": "SLICE-001",
            "slice_status": "building",
            "slice_retry_count": 0,
            "review_status": "not_run",
            "spec_check_status": "not_run",
        }
        self.assertFalse(should_continue_build_loop(queue_state))


class RunnerPathsTests(unittest.TestCase):
    def test_runner_paths_are_repo_relative(self):
        paths = RunnerPaths(Path("/tmp/demo"))
        self.assertEqual(paths.state_dir, Path("/tmp/demo/.ohmylawd"))
        self.assertEqual(paths.logs_dir, Path("/tmp/demo/.ohmylawd/logs"))
        self.assertEqual(paths.run_state_path, Path("/tmp/demo/.ohmylawd/run-state.json"))


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
                key="00-spec2slices",
                prompt_path=repo_root / "prompt-pack/00-spec2slices.md",
                required_outputs=(),
                log_name="00-spec2slices.log",
            )
            paths = RunnerPaths(repo_root)
            result = run_phase(phase, repo_root, paths, make_args())
            self.assertEqual(result.exit_code, 0)
            self.assertTrue(result.log_path.exists())
            self.assertIn("=== PROMPT ===", result.log_path.read_text(encoding="utf-8"))


class PipelineTests(unittest.TestCase):
    def _make_phase_driver(
        self,
        repo_root: Path,
        *,
        slices: list[dict] | None = None,
        spec_fail_once_for: str | None = None,
        first_audit_result: str = "pass",
        final_audit_result: str = "pass",
    ):
        spec_counts: dict[str, int] = {}
        audit_count = {"value": 0}

        def _driver(phase: PhaseSpec, *_args, **_kwargs):
            if phase.key == "00-spec2slices":
                create_bootstrap_outputs(repo_root, slices=slices)
            elif phase.key in {"01-slice2metaplan", "02-metaplan2detailedplan"} and phase.slice_id:
                create_slice_plan_outputs(repo_root, phase.slice_id)
            elif phase.key == "03-detailedplan2tasks" and phase.slice_id:
                create_task_outputs(repo_root, current_slice=phase.slice_id)
            elif phase.key == "04-tasks2build" and phase.slice_id:
                create_task_outputs(repo_root, current_slice=phase.slice_id)
            elif phase.key == "05-review" and phase.slice_id:
                create_review_output(repo_root, phase.slice_id, result="pass")
            elif phase.key == "06-spec-check" and phase.slice_id:
                spec_counts[phase.slice_id] = spec_counts.get(phase.slice_id, 0) + 1
                result = "pass"
                if phase.slice_id == spec_fail_once_for and spec_counts[phase.slice_id] == 1:
                    result = "fail"
                create_spec_check_output(repo_root, phase.slice_id, result=result)
            elif phase.key == "07-whole-spec-audit":
                audit_count["value"] += 1
                result = first_audit_result if audit_count["value"] == 1 else final_audit_result
                create_whole_spec_audit(repo_root, result=result)
            return mock.Mock(exit_code=0, command=["codex"], log_path=Path(f"/tmp/{phase.log_name}"))

        return _driver

    @mock.patch("scripts.oh_my_lawd_build.ensure_codex_exists")
    def test_run_pipeline_dry_run_writes_preview_logs(self, _ensure_codex):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            seed_repo(repo_root)
            exit_code = run_pipeline(repo_root, make_args(dry_run=True))
            self.assertEqual(exit_code, 0)
            logs_dir = repo_root / ".ohmylawd/logs"
            for name in (
                "00-spec2slices.log",
                "01-slice2metaplan-slice-001.log",
                "02-metaplan2detailedplan-slice-001.log",
                "03-detailedplan2tasks-slice-001.log",
                "04-tasks2build-slice-001-001.log",
                "05-review-slice-001.log",
                "06-spec-check-slice-001.log",
                "07-whole-spec-audit.log",
            ):
                self.assertTrue((logs_dir / name).exists())
            state = json.loads((repo_root / ".ohmylawd/run-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "dry_run")

    @mock.patch("scripts.oh_my_lawd_build.ensure_codex_exists")
    @mock.patch("scripts.oh_my_lawd_build.run_phase")
    def test_dry_run_preview_uses_first_manifest_slice_when_present(self, run_phase_mock, _ensure_codex):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            seed_repo(repo_root)
            create_bootstrap_outputs(
                repo_root,
                slices=[
                    {
                        "slice_id": "SLICE-ALPHA",
                        "title": "Alpha",
                        "goal": "alpha",
                        "source_spec_refs": ["spec/product-contract.md#5"],
                        "acceptance_gates": ["PX-07"],
                        "depends_on_slices": [],
                        "status": "ready",
                    }
                ],
            )
            run_phase_mock.return_value = mock.Mock(exit_code=0, command=["codex"], log_path=Path("/tmp/preview.log"))

            exit_code = run_pipeline(repo_root, make_args(dry_run=True))

            self.assertEqual(exit_code, 0)
            slice_ids = [call.args[0].slice_id for call in run_phase_mock.call_args_list if call.args[0].slice_id]
            self.assertTrue(slice_ids)
            self.assertEqual(slice_ids[0], "SLICE-ALPHA")

    @mock.patch("scripts.oh_my_lawd_build.commit_repo_state", side_effect=["sha-slice", "sha-final"])
    @mock.patch("scripts.oh_my_lawd_build.ensure_clean_worktree")
    @mock.patch("scripts.oh_my_lawd_build.ensure_codex_exists")
    @mock.patch("scripts.oh_my_lawd_build.run_phase")
    def test_run_pipeline_completes_single_slice(
        self,
        run_phase_mock,
        _ensure_codex,
        _ensure_clean_worktree,
        _commit_repo_state,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            seed_repo(repo_root)
            run_phase_mock.side_effect = self._make_phase_driver(repo_root)

            exit_code = run_pipeline(repo_root, make_args())

            self.assertEqual(exit_code, 0)
            state = json.loads((repo_root / ".ohmylawd/run-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "completed")
            self.assertEqual(state["slice_statuses"]["SLICE-001"], "committed")
            self.assertEqual(state["slice_commits"]["FINAL"], "sha-final")

    @mock.patch("scripts.oh_my_lawd_build.commit_repo_state", side_effect=["sha-1", "sha-2", "sha-final"])
    @mock.patch("scripts.oh_my_lawd_build.ensure_clean_worktree")
    @mock.patch("scripts.oh_my_lawd_build.ensure_codex_exists")
    @mock.patch("scripts.oh_my_lawd_build.run_phase")
    def test_run_pipeline_completes_multiple_slices(
        self,
        run_phase_mock,
        _ensure_codex,
        _ensure_clean_worktree,
        _commit_repo_state,
    ):
        slices = [
            {
                "slice_id": "SLICE-001",
                "title": "Primary operator surface",
                "goal": "slice one",
                "source_spec_refs": ["spec/product-contract.md#5"],
                "acceptance_gates": ["PX-07"],
                "depends_on_slices": [],
                "status": "ready",
            },
            {
                "slice_id": "SLICE-002",
                "title": "Recovery and resume",
                "goal": "slice two",
                "source_spec_refs": ["spec/product-contract.md#8"],
                "acceptance_gates": ["PX-12"],
                "depends_on_slices": ["SLICE-001"],
                "status": "ready",
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            seed_repo(repo_root)
            run_phase_mock.side_effect = self._make_phase_driver(repo_root, slices=slices)

            exit_code = run_pipeline(repo_root, make_args())

            self.assertEqual(exit_code, 0)
            called_slices = [call.args[0].slice_id for call in run_phase_mock.call_args_list if call.args[0].slice_id]
            self.assertIn("SLICE-001", called_slices)
            self.assertIn("SLICE-002", called_slices)

    @mock.patch("scripts.oh_my_lawd_build.commit_repo_state", side_effect=["sha-slice", "sha-final"])
    @mock.patch("scripts.oh_my_lawd_build.ensure_clean_worktree")
    @mock.patch("scripts.oh_my_lawd_build.ensure_codex_exists")
    @mock.patch("scripts.oh_my_lawd_build.run_phase")
    def test_spec_check_failure_routes_back_to_detailed_planning(
        self,
        run_phase_mock,
        _ensure_codex,
        _ensure_clean_worktree,
        _commit_repo_state,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            seed_repo(repo_root)
            run_phase_mock.side_effect = self._make_phase_driver(repo_root, spec_fail_once_for="SLICE-001")

            exit_code = run_pipeline(repo_root, make_args())

            self.assertEqual(exit_code, 0)
            phase_keys = [call.args[0].key for call in run_phase_mock.call_args_list]
            self.assertGreaterEqual(phase_keys.count("02-metaplan2detailedplan"), 2)
            state = json.loads((repo_root / ".ohmylawd/run-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["slice_retry_counts"]["SLICE-001"], 1)

    @mock.patch("scripts.oh_my_lawd_build.commit_repo_state", side_effect=["sha-slice", "sha-fix", "sha-final"])
    @mock.patch("scripts.oh_my_lawd_build.ensure_clean_worktree")
    @mock.patch("scripts.oh_my_lawd_build.ensure_codex_exists")
    @mock.patch("scripts.oh_my_lawd_build.run_phase")
    def test_whole_spec_audit_failure_runs_synthetic_fix_slice(
        self,
        run_phase_mock,
        _ensure_codex,
        _ensure_clean_worktree,
        _commit_repo_state,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            seed_repo(repo_root)
            run_phase_mock.side_effect = self._make_phase_driver(
                repo_root,
                first_audit_result="fail",
                final_audit_result="pass",
            )

            exit_code = run_pipeline(repo_root, make_args())

            self.assertEqual(exit_code, 0)
            called_slices = [call.args[0].slice_id for call in run_phase_mock.call_args_list if call.args[0].slice_id]
            self.assertIn(WHOLE_SPEC_FIX_SLICE_ID, called_slices)

    @mock.patch("scripts.oh_my_lawd_build.commit_repo_state", side_effect=["sha-slice", "sha-fix"])
    @mock.patch("scripts.oh_my_lawd_build.ensure_clean_worktree")
    @mock.patch("scripts.oh_my_lawd_build.ensure_codex_exists")
    @mock.patch("scripts.oh_my_lawd_build.run_phase")
    def test_second_whole_spec_audit_failure_raises(
        self,
        run_phase_mock,
        _ensure_codex,
        _ensure_clean_worktree,
        _commit_repo_state,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            seed_repo(repo_root)
            run_phase_mock.side_effect = self._make_phase_driver(
                repo_root,
                first_audit_result="fail",
                final_audit_result="fail",
            )

            with self.assertRaises(RuntimeError):
                run_pipeline(repo_root, make_args())

    @mock.patch("scripts.oh_my_lawd_build.commit_repo_state", side_effect=["sha-slice", "sha-final"])
    @mock.patch("scripts.oh_my_lawd_build.ensure_clean_worktree")
    @mock.patch("scripts.oh_my_lawd_build.ensure_codex_exists")
    @mock.patch("scripts.oh_my_lawd_build.run_phase")
    def test_run_pipeline_resumes_build_loop_iteration_plus_one(
        self,
        run_phase_mock,
        _ensure_codex,
        _ensure_clean_worktree,
        _commit_repo_state,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            seed_repo(repo_root)
            create_bootstrap_outputs(repo_root)
            create_slice_plan_outputs(repo_root, "SLICE-001")
            create_task_outputs(repo_root, current_slice="SLICE-001")
            paths = RunnerPaths(repo_root)
            paths.state_dir.mkdir(parents=True, exist_ok=True)
            paths.run_state_path.write_text(
                json.dumps(
                    {
                        "pipeline_version": "2.0",
                        "status": "running",
                        "current_phase": "04-tasks2build",
                        "current_slice": "SLICE-001",
                        "completed_phases": ["00-spec2slices"],
                        "build_iterations": 2,
                        "last_exit_code": 0,
                        "last_command": ["codex"],
                        "last_log_path": "/tmp/old.log",
                        "slice_statuses": {"SLICE-001": "building"},
                        "review_results": {},
                        "spec_check_results": {},
                        "slice_retry_counts": {"SLICE-001": 0},
                        "slice_commits": {},
                        "whole_spec_fix_attempted": False,
                    }
                ),
                encoding="utf-8",
            )
            run_phase_mock.side_effect = self._make_phase_driver(repo_root)

            exit_code = run_pipeline(repo_root, make_args(resume=True))

            self.assertEqual(exit_code, 0)
            first_phase = run_phase_mock.call_args_list[0].args[0]
            self.assertEqual(first_phase.log_name, "04-tasks2build-slice-001-003.log")

    @mock.patch("scripts.oh_my_lawd_build.commit_repo_state", side_effect=["sha-slice", "sha-final"])
    @mock.patch("scripts.oh_my_lawd_build.ensure_clean_worktree")
    @mock.patch("scripts.oh_my_lawd_build.ensure_codex_exists")
    @mock.patch("scripts.oh_my_lawd_build.run_phase")
    def test_resume_skips_clean_worktree_gate_when_prior_state_exists(
        self,
        run_phase_mock,
        _ensure_codex,
        ensure_clean_worktree_mock,
        _commit_repo_state,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            seed_repo(repo_root)
            create_bootstrap_outputs(repo_root)
            create_slice_plan_outputs(repo_root, "SLICE-001")
            create_task_outputs(repo_root, current_slice="SLICE-001")
            paths = RunnerPaths(repo_root)
            paths.state_dir.mkdir(parents=True, exist_ok=True)
            paths.run_state_path.write_text(
                json.dumps(
                    {
                        "pipeline_version": "2.0",
                        "status": "running",
                        "current_phase": "04-tasks2build",
                        "current_slice": "SLICE-001",
                        "completed_phases": ["00-spec2slices"],
                        "build_iterations": 1,
                        "last_exit_code": 0,
                        "last_command": ["codex"],
                        "last_log_path": "/tmp/old.log",
                        "slice_statuses": {"SLICE-001": "building"},
                        "review_results": {},
                        "spec_check_results": {},
                        "slice_retry_counts": {"SLICE-001": 0},
                        "slice_commits": {},
                        "whole_spec_fix_attempted": False,
                    }
                ),
                encoding="utf-8",
            )
            run_phase_mock.side_effect = self._make_phase_driver(repo_root)

            exit_code = run_pipeline(repo_root, make_args(resume=True))

            self.assertEqual(exit_code, 0)
            ensure_clean_worktree_mock.assert_not_called()


class GitGuardTests(unittest.TestCase):
    @mock.patch("scripts.oh_my_lawd_build.subprocess.run")
    def test_ensure_clean_worktree_rejects_dirty_status(self, run_mock):
        run_mock.return_value = mock.Mock(returncode=0, stdout=" M README.md\n", stderr="")
        with self.assertRaises(RuntimeError):
            ensure_clean_worktree(Path("/tmp/demo"))

    @mock.patch("scripts.oh_my_lawd_build.subprocess.run")
    def test_commit_repo_state_returns_head_sha(self, run_mock):
        run_mock.side_effect = [
            mock.Mock(returncode=0, stdout="", stderr=""),
            mock.Mock(returncode=0, stdout="[main] commit\n", stderr=""),
            mock.Mock(returncode=0, stdout="abc123\n", stderr=""),
        ]
        self.assertEqual(commit_repo_state(Path("/tmp/demo"), "msg"), "abc123")


class PromptPackRegressionTests(unittest.TestCase):
    def test_detailed_plan_prompt_requires_retry_feedback_artifacts(self):
        prompt = (
            Path(__file__).resolve().parent.parent / "prompt-pack" / "02-metaplan2detailedplan.md"
        ).read_text(encoding="utf-8")
        self.assertIn("/tasks/review-<slice-id>.md", prompt)
        self.assertIn("/tasks/spec-check-<slice-id>.json", prompt)

    def test_build_prompt_requires_retry_feedback_artifacts(self):
        prompt = (
            Path(__file__).resolve().parent.parent / "prompt-pack" / "04-tasks2build.md"
        ).read_text(encoding="utf-8")
        self.assertIn("/tasks/review-<slice-id>.md", prompt)
        self.assertIn("/tasks/spec-check-<slice-id>.json", prompt)

    def test_review_prompt_requires_separate_quality_check(self):
        prompt = (Path(__file__).resolve().parent.parent / "prompt-pack" / "05-review.md").read_text(encoding="utf-8")
        self.assertIn("/spec", prompt)
        self.assertIn("Result: pass|fail", prompt)

    def test_spec_check_prompt_requires_direct_spec_comparison(self):
        prompt = (Path(__file__).resolve().parent.parent / "prompt-pack" / "06-spec-check.md").read_text(encoding="utf-8")
        self.assertIn("Read `/spec` directly", prompt)
        self.assertIn("must not stand in for missing functionality", prompt)

    def test_compose_prompt_includes_retry_feedback_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            seed_repo(repo_root)
            create_review_output(repo_root, "SLICE-001", result="fail")
            create_spec_check_output(repo_root, "SLICE-001", result="fail")
            phase = PhaseSpec(
                key="02-metaplan2detailedplan",
                prompt_path=repo_root / "prompt-pack/02-metaplan2detailedplan.md",
                required_outputs=(),
                log_name="02-metaplan2detailedplan-slice-001.log",
                slice_id="SLICE-001",
            )

            prompt_text = compose_prompt(phase, repo_root)

            self.assertIn("Retry context: prior review failed.", prompt_text)
            self.assertIn("Retry context: prior spec-check failed.", prompt_text)
            self.assertIn("missing requirements", prompt_text.lower())


if __name__ == "__main__":
    unittest.main()
