#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.operator_commands import (
    COMMAND_TAXONOMY,
    command_taxonomy_snapshot as _operator_command_taxonomy_snapshot,
    help_example_commands,
)
from runtime.extension_onboarding import (
    load_extension_onboarding_projection,
    run_extension_onboarding,
)
from runtime.product_state_projection import project_persisted_run_state

PIPELINE_VERSION = "2.0"
WHOLE_SPEC_FIX_SLICE_ID = "SLICE-WHOLE-SPEC-FIX"
SLICE_COMMIT_TEMPLATE = "build(slice:{slice_id}): pass review and spec-check"
FINAL_COMMIT_MESSAGE = "build: whole-spec audit passed"

PLAN_OUTPUTS = (
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
    "plan/slice-manifest.json",
)

TASK_OUTPUTS = (
    "tasks/README.md",
    "tasks/index.md",
    "tasks/task-index.json",
    "tasks/queue-state.json",
)

QUEUE_STATE_KEYS = (
    "ready_tasks",
    "blocked_tasks",
    "in_progress_tasks",
    "completed_tasks",
    "recommended_next_task",
    "last_generated_at",
    "current_slice",
    "slice_status",
    "slice_retry_count",
    "review_status",
    "spec_check_status",
)

SLICE_MANIFEST_REQUIRED_FIELDS = (
    "slice_id",
    "title",
    "goal",
    "source_spec_refs",
    "acceptance_gates",
    "depends_on_slices",
    "status",
)

SPEC_CHECK_RESULT_KEYS = (
    "slice_id",
    "result",
    "summary",
    "missing_requirements",
    "verified_code_paths",
    "verified_commands",
    "verified_outputs",
    "requires_replan",
)


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


@dataclass(frozen=True)
class PhaseSpec:
    key: str
    prompt_path: Path
    required_outputs: tuple[Path, ...]
    log_name: str
    slice_id: str | None = None


@dataclass(frozen=True)
class PhaseResult:
    exit_code: int
    command: list[str]
    log_path: Path


class PhaseExecutionError(RuntimeError):
    def __init__(self, exit_code: int):
        super().__init__(f"phase command failed with exit code {exit_code}")
        self.exit_code = exit_code


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def command_taxonomy_snapshot() -> dict[str, Any]:
    return _operator_command_taxonomy_snapshot()


def _add_pipeline_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--resume", action="store_true", help="Resume from .ohmylawd/run-state.json if present.")
    parser.add_argument(
        "--max-build-iterations",
        type=int,
        default=25,
        help="Maximum number of 04-tasks2build iterations per slice before failing closed.",
    )
    parser.add_argument(
        "--max-slice-retries",
        type=int,
        default=3,
        help="Maximum number of review/spec-check retry loops per slice before failing closed.",
    )
    parser.add_argument("--codex-bin", default="codex", help="Path to the Codex CLI binary.")
    parser.add_argument("--model", help="Optional Codex model override.")
    parser.add_argument("--profile", help="Optional Codex profile name.")
    parser.add_argument("--dry-run", action="store_true", help="Write logs for planned commands without executing Codex.")
    parser.add_argument("--verbose", action="store_true", help="Print runner progress to stderr.")


def build_parser() -> argparse.ArgumentParser:
    example_lines = ["Examples:"]
    example_lines.extend(f"  {command}" for command in help_example_commands())
    parser = argparse.ArgumentParser(
        description="Operate Oh My Lawd through grouped, action-oriented commands.",
        epilog="\n".join(example_lines),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.set_defaults(
        command_group="pipeline",
        pipeline_action="run",
        resume=False,
        max_build_iterations=25,
        max_slice_retries=3,
        codex_bin="codex",
        model=None,
        profile=None,
        dry_run=False,
        verbose=False,
    )

    command_groups = parser.add_subparsers(dest="command_group")

    pipeline_parser = command_groups.add_parser(
        "pipeline",
        help="Execute prompt-pack pipeline actions.",
    )
    pipeline_actions = pipeline_parser.add_subparsers(dest="pipeline_action", required=True)

    pipeline_run_parser = pipeline_actions.add_parser(
        "run",
        help="Run 00, each slice's 01-06 cycle, then 07 until the whole-spec audit passes.",
    )
    _add_pipeline_options(pipeline_run_parser)

    pipeline_resume_parser = pipeline_actions.add_parser(
        "resume",
        help="Resume the slice pipeline from persisted runner state.",
    )
    _add_pipeline_options(pipeline_resume_parser)
    pipeline_resume_parser.set_defaults(resume=True)

    pipeline_preview_parser = pipeline_actions.add_parser(
        "preview",
        help="Show and log planned 00-07 commands without running Codex.",
    )
    _add_pipeline_options(pipeline_preview_parser)
    pipeline_preview_parser.set_defaults(dry_run=True)

    state_parser = command_groups.add_parser(
        "state",
        help="Inspect persisted runtime/orchestration state projections.",
    )
    state_actions = state_parser.add_subparsers(dest="state_action", required=True)

    state_show_parser = state_actions.add_parser(
        "show",
        help="Project persisted run_state into operator-visible product state.",
    )
    state_show_parser.add_argument("--run-state-path", required=True, help="Path to persisted runtime run_state JSON.")
    state_show_parser.add_argument(
        "--freshness-slo-seconds",
        type=int,
        default=30,
        help="Freshness SLO used for projection staleness checks.",
    )
    state_show_parser.add_argument(
        "--now-timestamp",
        help="Optional ISO-8601 UTC timestamp override for deterministic projections.",
    )
    state_show_parser.add_argument("--verbose", action="store_true", help="Print command progress to stderr.")

    extension_parser = command_groups.add_parser(
        "extension",
        help="Run extension onboarding and inspect onboarding state.",
    )
    extension_actions = extension_parser.add_subparsers(dest="extension_action", required=True)

    extension_onboard_parser = extension_actions.add_parser(
        "onboard",
        help="Run discover/select/install/configure/validate/activate onboarding.",
    )
    extension_onboard_parser.add_argument("--extension-id", required=True, help="Extension identifier to onboard.")
    extension_onboard_parser.add_argument("--manifest-path", required=True, help="Path to extension manifest JSON.")
    extension_onboard_parser.add_argument("--config-path", required=True, help="Path to extension configuration JSON.")
    extension_onboard_parser.add_argument(
        "--state-dir",
        default=".ohmylawd/extensions",
        help="Directory used to persist extension onboarding state files.",
    )
    extension_onboard_parser.add_argument(
        "--now-timestamp",
        help="Optional ISO-8601 UTC timestamp override for deterministic onboarding fixtures.",
    )
    extension_onboard_parser.add_argument("--verbose", action="store_true", help="Print command progress to stderr.")

    extension_status_parser = extension_actions.add_parser(
        "status",
        help="Show persisted extension onboarding state.",
    )
    extension_status_parser.add_argument("--extension-id", required=True, help="Extension identifier to inspect.")
    extension_status_parser.add_argument(
        "--state-dir",
        default=".ohmylawd/extensions",
        help="Directory containing persisted extension onboarding state files.",
    )
    extension_status_parser.add_argument("--verbose", action="store_true", help="Print command progress to stderr.")
    return parser


def normalize_command_argv(argv: list[str] | None) -> list[str]:
    command_argv = list(argv or [])
    command_roots = set(COMMAND_TAXONOMY)
    if not command_argv:
        return ["pipeline", "run"]
    if command_argv[0] in ("-h", "--help"):
        return command_argv
    if command_argv[0] not in command_roots:
        return ["pipeline", "run", *command_argv]
    if command_argv[0] == "pipeline" and (len(command_argv) == 1 or command_argv[1].startswith("-")):
        return ["pipeline", "run", *command_argv[1:]]
    return command_argv


def default_repo_root() -> Path:
    return REPO_ROOT


def validate_repo_root(repo_root: Path) -> None:
    missing: list[str] = []
    for required in (
        repo_root / "README.md",
        repo_root / "prompt-pack/00-spec2slices.md",
        repo_root / "prompt-pack/01-slice2metaplan.md",
        repo_root / "prompt-pack/02-metaplan2detailedplan.md",
        repo_root / "prompt-pack/03-detailedplan2tasks.md",
        repo_root / "prompt-pack/04-tasks2build.md",
        repo_root / "prompt-pack/05-review.md",
        repo_root / "prompt-pack/06-spec-check.md",
        repo_root / "prompt-pack/07-whole-spec-audit.md",
        repo_root / "spec",
    ):
        if not required.exists():
            missing.append(str(required))
    if missing:
        raise FileNotFoundError(f"Repository root is missing required files: {', '.join(missing)}")


def ensure_codex_exists(codex_bin: str, *, dry_run: bool = False) -> None:
    if dry_run:
        return
    if shutil.which(codex_bin) is None:
        raise FileNotFoundError(f"Codex binary not found on PATH: {codex_bin}")


def ensure_clean_worktree(repo_root: Path) -> None:
    completed = subprocess.run(
        ["git", "status", "--short"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("pipeline run requires a git repository with a working git status command")
    if completed.stdout.strip():
        raise RuntimeError("pipeline run requires a clean git worktree before automatic commits")


def commit_repo_state(repo_root: Path, message: str) -> str:
    add_result = subprocess.run(
        ["git", "add", "-A"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if add_result.returncode != 0:
        raise RuntimeError(f"git add failed: {add_result.stderr.strip()}")

    commit_result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if commit_result.returncode != 0:
        raise RuntimeError(f"git commit failed: {commit_result.stderr.strip() or commit_result.stdout.strip()}")

    head_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if head_result.returncode != 0:
        raise RuntimeError(f"git rev-parse failed: {head_result.stderr.strip()}")
    return head_result.stdout.strip()


def _phase_slug(value: str) -> str:
    cleaned = [character.lower() if character.isalnum() else "-" for character in value]
    slug = "".join(cleaned).strip("-")
    return slug or "slice"


def bootstrap_phase(repo_root: Path) -> PhaseSpec:
    return PhaseSpec(
        key="00-spec2slices",
        prompt_path=repo_root / "prompt-pack/00-spec2slices.md",
        required_outputs=tuple(repo_root / path for path in PLAN_OUTPUTS),
        log_name="00-spec2slices.log",
    )


def build_slice_phase(repo_root: Path, phase_key: str, slice_id: str, *, iteration: int | None = None) -> PhaseSpec:
    slug = _phase_slug(slice_id)
    if phase_key == "01-slice2metaplan":
        return PhaseSpec(
            key=phase_key,
            prompt_path=repo_root / "prompt-pack/01-slice2metaplan.md",
            required_outputs=(repo_root / f"plan/{slice_id}-metaplan.md",),
            log_name=f"01-slice2metaplan-{slug}.log",
            slice_id=slice_id,
        )
    if phase_key == "02-metaplan2detailedplan":
        return PhaseSpec(
            key=phase_key,
            prompt_path=repo_root / "prompt-pack/02-metaplan2detailedplan.md",
            required_outputs=(repo_root / f"plan/{slice_id}-detailed-plan.md",),
            log_name=f"02-metaplan2detailedplan-{slug}.log",
            slice_id=slice_id,
        )
    if phase_key == "03-detailedplan2tasks":
        return PhaseSpec(
            key=phase_key,
            prompt_path=repo_root / "prompt-pack/03-detailedplan2tasks.md",
            required_outputs=tuple(repo_root / path for path in TASK_OUTPUTS),
            log_name=f"03-detailedplan2tasks-{slug}.log",
            slice_id=slice_id,
        )
    if phase_key == "04-tasks2build":
        if iteration is None:
            raise ValueError("04-tasks2build requires an iteration number")
        return PhaseSpec(
            key=phase_key,
            prompt_path=repo_root / "prompt-pack/04-tasks2build.md",
            required_outputs=(repo_root / "tasks/queue-state.json",),
            log_name=f"04-tasks2build-{slug}-{iteration:03d}.log",
            slice_id=slice_id,
        )
    if phase_key == "05-review":
        return PhaseSpec(
            key=phase_key,
            prompt_path=repo_root / "prompt-pack/05-review.md",
            required_outputs=(repo_root / f"tasks/review-{slice_id}.md",),
            log_name=f"05-review-{slug}.log",
            slice_id=slice_id,
        )
    if phase_key == "06-spec-check":
        return PhaseSpec(
            key=phase_key,
            prompt_path=repo_root / "prompt-pack/06-spec-check.md",
            required_outputs=(repo_root / f"tasks/spec-check-{slice_id}.json",),
            log_name=f"06-spec-check-{slug}.log",
            slice_id=slice_id,
        )
    raise ValueError(f"Unknown slice phase: {phase_key}")


def build_whole_spec_audit_phase(repo_root: Path, *, attempt: int = 1) -> PhaseSpec:
    suffix = f"-{attempt:02d}" if attempt > 1 else ""
    return PhaseSpec(
        key="07-whole-spec-audit",
        prompt_path=repo_root / "prompt-pack/07-whole-spec-audit.md",
        required_outputs=(repo_root / "docs/release-evidence/whole-spec-audit.md",),
        log_name=f"07-whole-spec-audit{suffix}.log",
    )


def validate_required_outputs(phase: PhaseSpec) -> list[Path]:
    return [path for path in phase.required_outputs if not path.exists()]


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_slice_manifest(payload: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["slice manifest must be a JSON object"]

    slices = payload.get("slices")
    if not isinstance(slices, list) or not slices:
        return ["slices must be a non-empty list"]

    seen_ids: set[str] = set()
    for index, slice_entry in enumerate(slices):
        prefix = f"slices[{index}]"
        if not isinstance(slice_entry, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for key in SLICE_MANIFEST_REQUIRED_FIELDS:
            if key not in slice_entry:
                errors.append(f"{prefix} missing field: {key}")
        slice_id = slice_entry.get("slice_id")
        if not isinstance(slice_id, str) or not slice_id:
            errors.append(f"{prefix}.slice_id must be a non-empty string")
        elif slice_id in seen_ids:
            errors.append(f"duplicate slice_id: {slice_id}")
        else:
            seen_ids.add(slice_id)
        for key in ("title", "goal", "status"):
            value = slice_entry.get(key)
            if not isinstance(value, str) or not value:
                errors.append(f"{prefix}.{key} must be a non-empty string")
        for key in ("source_spec_refs", "acceptance_gates", "depends_on_slices"):
            value = slice_entry.get(key)
            if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
                errors.append(f"{prefix}.{key} must be a list of non-empty strings")
    return errors


def read_slice_manifest(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing slice manifest file: {path}")
    payload = load_json(path)
    errors = validate_slice_manifest(payload)
    if errors:
        raise ValueError(f"Invalid slice-manifest.json: {'; '.join(errors)}")
    if not isinstance(payload, dict):
        raise ValueError("Invalid slice-manifest.json: slice manifest must be a JSON object")
    slices = payload["slices"]
    if not isinstance(slices, list):
        raise ValueError("Invalid slice-manifest.json: slices must be a list")
    return [dict(item) for item in slices]


def validate_queue_state(queue_state: object, *, current_slice: str | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(queue_state, dict):
        return ["queue state must be a JSON object"]

    missing_keys = [key for key in QUEUE_STATE_KEYS if key not in queue_state]
    if missing_keys:
        errors.append(f"missing keys: {', '.join(missing_keys)}")

    for key in ("ready_tasks", "blocked_tasks", "in_progress_tasks", "completed_tasks"):
        value = queue_state.get(key)
        if not isinstance(value, list):
            errors.append(f"{key} must be a list")

    recommended_next_task = queue_state.get("recommended_next_task")
    if recommended_next_task is not None and not isinstance(recommended_next_task, str):
        errors.append("recommended_next_task must be a string or null")

    last_generated_at = queue_state.get("last_generated_at")
    if not isinstance(last_generated_at, str):
        errors.append("last_generated_at must be a string")

    queue_slice = queue_state.get("current_slice")
    if not isinstance(queue_slice, str) or not queue_slice:
        errors.append("current_slice must be a non-empty string")
    elif current_slice is not None and queue_slice != current_slice:
        errors.append(f"current_slice must equal {current_slice}")

    for key in ("slice_status", "review_status", "spec_check_status"):
        value = queue_state.get(key)
        if not isinstance(value, str) or not value:
            errors.append(f"{key} must be a non-empty string")

    retry_count = queue_state.get("slice_retry_count")
    if not isinstance(retry_count, int) or retry_count < 0:
        errors.append("slice_retry_count must be a non-negative integer")
    return errors


def read_queue_state(queue_state_path: Path, *, current_slice: str | None = None) -> dict[str, Any]:
    if not queue_state_path.exists():
        raise FileNotFoundError(f"Missing queue state file: {queue_state_path}")
    payload = load_json(queue_state_path)
    errors = validate_queue_state(payload, current_slice=current_slice)
    if errors:
        raise ValueError(f"Invalid queue-state.json: {'; '.join(errors)}")
    if not isinstance(payload, dict):
        raise ValueError("Invalid queue-state.json: queue state must be a JSON object")
    return payload


def validate_spec_check_result(payload: object, *, current_slice: str | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["spec-check result must be a JSON object"]

    missing_keys = [key for key in SPEC_CHECK_RESULT_KEYS if key not in payload]
    if missing_keys:
        errors.append(f"missing keys: {', '.join(missing_keys)}")

    slice_id = payload.get("slice_id")
    if not isinstance(slice_id, str) or not slice_id:
        errors.append("slice_id must be a non-empty string")
    elif current_slice is not None and slice_id != current_slice:
        errors.append(f"slice_id must equal {current_slice}")

    result = payload.get("result")
    if result not in {"pass", "fail"}:
        errors.append("result must be 'pass' or 'fail'")

    summary = payload.get("summary")
    if not isinstance(summary, str) or not summary:
        errors.append("summary must be a non-empty string")

    for key in ("missing_requirements", "verified_code_paths", "verified_commands", "verified_outputs"):
        value = payload.get(key)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            errors.append(f"{key} must be a list of strings")

    requires_replan = payload.get("requires_replan")
    if not isinstance(requires_replan, bool):
        errors.append("requires_replan must be a boolean")
    return errors


def read_spec_check_result(path: Path, *, current_slice: str | None = None) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing spec-check file: {path}")
    payload = load_json(path)
    errors = validate_spec_check_result(payload, current_slice=current_slice)
    if errors:
        raise ValueError(f"Invalid spec-check result: {'; '.join(errors)}")
    if not isinstance(payload, dict):
        raise ValueError("Invalid spec-check result: payload must be a JSON object")
    return payload


def parse_result_marker(path: Path, *, subject: str, allowed: set[str]) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing {subject} file: {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("Result:"):
            result = line.split(":", 1)[1].strip().lower()
            if result not in allowed:
                raise ValueError(f"Invalid {subject} result in {path}: {result}")
            return result
    raise ValueError(f"{subject} file must contain a 'Result:' line: {path}")


def validate_phase_outputs(repo_root: Path, phase: PhaseSpec) -> None:
    missing = validate_required_outputs(phase)
    if missing:
        missing_display = ", ".join(str(path.relative_to(repo_root)) for path in missing)
        raise FileNotFoundError(f"{phase.key} did not produce required outputs: {missing_display}")

    if phase.key == "00-spec2slices":
        read_slice_manifest(repo_root / "plan/slice-manifest.json")
        return

    if phase.key == "03-detailedplan2tasks":
        task_files = sorted((repo_root / "tasks").glob("TASK-*.md"))
        if not task_files:
            raise FileNotFoundError("03-detailedplan2tasks did not produce any tasks/TASK-*.md files")
        read_queue_state(repo_root / "tasks/queue-state.json", current_slice=phase.slice_id)
        return

    if phase.key == "04-tasks2build":
        read_queue_state(repo_root / "tasks/queue-state.json", current_slice=phase.slice_id)
        return

    if phase.key == "05-review":
        parse_result_marker(repo_root / f"tasks/review-{phase.slice_id}.md", subject="review", allowed={"pass", "fail"})
        return

    if phase.key == "06-spec-check":
        read_spec_check_result(repo_root / f"tasks/spec-check-{phase.slice_id}.json", current_slice=phase.slice_id)
        return

    if phase.key == "07-whole-spec-audit":
        parse_result_marker(
            repo_root / "docs/release-evidence/whole-spec-audit.md",
            subject="whole-spec audit",
            allowed={"pass", "fail"},
        )


def phase_outputs_are_valid(repo_root: Path, phase: PhaseSpec) -> bool:
    try:
        validate_phase_outputs(repo_root, phase)
    except (FileNotFoundError, ValueError):
        return False
    return True


def should_continue_build_loop(queue_state: dict[str, Any]) -> bool:
    return bool(
        queue_state.get("recommended_next_task")
        or queue_state.get("ready_tasks")
        or queue_state.get("in_progress_tasks")
    )


def _retry_feedback_lines(phase: PhaseSpec, repo_root: Path) -> list[str]:
    if phase.slice_id is None:
        return []

    lines: list[str] = []
    review_path = repo_root / f"tasks/review-{phase.slice_id}.md"
    if review_path.exists():
        try:
            review_result = parse_result_marker(review_path, subject="review", allowed={"pass", "fail"})
        except ValueError:
            review_result = None
        if review_result == "fail":
            lines.extend(
                [
                    "Retry context: prior review failed.",
                    f"You MUST read {review_path.relative_to(repo_root)} and address its findings before advancing.",
                ]
            )

    spec_check_path = repo_root / f"tasks/spec-check-{phase.slice_id}.json"
    if spec_check_path.exists():
        try:
            spec_check_result = read_spec_check_result(spec_check_path, current_slice=phase.slice_id)
        except (FileNotFoundError, ValueError):
            spec_check_result = None
        if spec_check_result and spec_check_result["result"] == "fail":
            summary = str(spec_check_result.get("summary", "")).strip()
            missing_requirements = spec_check_result.get("missing_requirements", [])
            lines.append("Retry context: prior spec-check failed.")
            lines.append(
                f"You MUST read {spec_check_path.relative_to(repo_root)} and address the missing requirements before advancing."
            )
            if summary:
                lines.append(f"Prior spec-check summary: {summary}")
            if isinstance(missing_requirements, list) and missing_requirements:
                lines.append("Prior missing requirements: " + ", ".join(str(item) for item in missing_requirements))
    return lines


def compose_prompt(phase: PhaseSpec, repo_root: Path) -> str:
    preamble_lines = [
        f"You are running in automated phase {phase.key}.",
        f"Repository root: {repo_root}",
        "Write artifacts directly into this repository.",
        "Treat the prompt-pack content below as authoritative for this phase.",
        "Stay within the documented phase boundary. Do not skip ahead or redesign the pipeline.",
    ]
    if phase.slice_id is not None:
        preamble_lines.append(f"Current slice: {phase.slice_id}")
        preamble_lines.extend(_retry_feedback_lines(phase, repo_root))
    preamble_lines.append("")
    return "\n".join(preamble_lines) + phase.prompt_path.read_text(encoding="utf-8")


def build_codex_command(args: argparse.Namespace, repo_root: Path) -> list[str]:
    command = [
        args.codex_bin,
        "exec",
        "--cd",
        str(repo_root),
        "--full-auto",
    ]
    if args.model:
        command.extend(["--model", args.model])
    if args.profile:
        command.extend(["--profile", args.profile])
    command.append("-")
    return command


def write_phase_log(
    *,
    log_path: Path,
    phase: PhaseSpec,
    command: list[str],
    prompt_text: str,
    exit_code: int,
    stdout: str,
    stderr: str,
    dry_run: bool,
) -> None:
    lines = [
        f"phase={phase.key}",
        f"slice_id={phase.slice_id or ''}",
        f"timestamp={utc_now()}",
        f"dry_run={str(dry_run).lower()}",
        f"exit_code={exit_code}",
        f"command={json.dumps(command)}",
        "",
        "=== PROMPT ===",
        prompt_text,
        "",
        "=== STDOUT ===",
        stdout,
        "",
        "=== STDERR ===",
        stderr,
    ]
    log_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_phase(
    phase: PhaseSpec,
    repo_root: Path,
    paths: RunnerPaths,
    args: argparse.Namespace,
) -> PhaseResult:
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    prompt_text = compose_prompt(phase, repo_root)
    command = build_codex_command(args, repo_root)
    log_path = paths.logs_dir / phase.log_name

    if args.verbose:
        print(f"[runner] phase={phase.key} slice={phase.slice_id or '-'} log={log_path}", file=sys.stderr)

    if args.dry_run:
        write_phase_log(
            log_path=log_path,
            phase=phase,
            command=command,
            prompt_text=prompt_text,
            exit_code=0,
            stdout="DRY RUN: Codex execution skipped.",
            stderr="",
            dry_run=True,
        )
        return PhaseResult(exit_code=0, command=command, log_path=log_path)

    completed = subprocess.run(
        command,
        cwd=repo_root,
        input=prompt_text,
        text=True,
        capture_output=True,
        check=False,
    )
    write_phase_log(
        log_path=log_path,
        phase=phase,
        command=command,
        prompt_text=prompt_text,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        dry_run=False,
    )
    return PhaseResult(exit_code=completed.returncode, command=command, log_path=log_path)


def save_run_state(paths: RunnerPaths, payload: dict[str, Any]) -> None:
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    paths.run_state_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_run_state(paths: RunnerPaths) -> dict[str, Any] | None:
    if not paths.run_state_path.exists():
        return None
    payload = load_json(paths.run_state_path)
    if not isinstance(payload, dict):
        raise ValueError("Invalid run-state.json: payload must be a JSON object")
    return payload


def record_run_state(
    *,
    paths: RunnerPaths,
    status: str,
    current_phase: str,
    current_slice: str | None,
    completed_phases: list[str],
    build_iterations: int,
    last_exit_code: int,
    last_command: list[str],
    last_log_path: Path,
    slice_statuses: dict[str, str],
    review_results: dict[str, str],
    spec_check_results: dict[str, str],
    slice_retry_counts: dict[str, int],
    slice_commits: dict[str, str],
    whole_spec_fix_attempted: bool,
    error_message: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "pipeline_version": PIPELINE_VERSION,
        "status": status,
        "current_phase": current_phase,
        "current_slice": current_slice,
        "completed_phases": completed_phases,
        "build_iterations": build_iterations,
        "last_exit_code": last_exit_code,
        "last_command": last_command,
        "last_log_path": str(last_log_path),
        "slice_statuses": slice_statuses,
        "review_results": review_results,
        "spec_check_results": spec_check_results,
        "slice_retry_counts": slice_retry_counts,
        "slice_commits": slice_commits,
        "whole_spec_fix_attempted": whole_spec_fix_attempted,
        "updated_at": utc_now(),
    }
    if error_message is not None:
        payload["last_error"] = error_message
    save_run_state(paths, payload)


def _state_dict(prior_state: dict[str, Any] | None, key: str, default: dict[str, Any]) -> dict[str, Any]:
    if prior_state is None:
        return dict(default)
    value = prior_state.get(key)
    if not isinstance(value, dict):
        return dict(default)
    return dict(value)


def _revalidate_bootstrap(repo_root: Path, completed_phases: list[str]) -> list[str]:
    phase = bootstrap_phase(repo_root)
    if phase.key not in completed_phases:
        return []
    return [phase.key] if phase_outputs_are_valid(repo_root, phase) else []


def _record_failure(
    *,
    paths: RunnerPaths,
    phase: PhaseSpec,
    result: PhaseResult,
    completed_phases: list[str],
    build_iterations: int,
    current_slice: str | None,
    slice_statuses: dict[str, str],
    review_results: dict[str, str],
    spec_check_results: dict[str, str],
    slice_retry_counts: dict[str, int],
    slice_commits: dict[str, str],
    whole_spec_fix_attempted: bool,
    error_message: str | None = None,
) -> None:
    record_run_state(
        paths=paths,
        status="failed",
        current_phase=phase.key,
        current_slice=current_slice,
        completed_phases=completed_phases,
        build_iterations=build_iterations,
        last_exit_code=result.exit_code,
        last_command=result.command,
        last_log_path=result.log_path,
        slice_statuses=slice_statuses,
        review_results=review_results,
        spec_check_results=spec_check_results,
        slice_retry_counts=slice_retry_counts,
        slice_commits=slice_commits,
        whole_spec_fix_attempted=whole_spec_fix_attempted,
        error_message=error_message,
    )


def execute_phase(
    *,
    phase: PhaseSpec,
    repo_root: Path,
    paths: RunnerPaths,
    args: argparse.Namespace,
    completed_phases: list[str],
    build_iterations: int,
    slice_statuses: dict[str, str],
    review_results: dict[str, str],
    spec_check_results: dict[str, str],
    slice_retry_counts: dict[str, int],
    slice_commits: dict[str, str],
    whole_spec_fix_attempted: bool,
) -> PhaseResult:
    result = run_phase(phase, repo_root, paths, args)
    if result.exit_code != 0:
        _record_failure(
            paths=paths,
            phase=phase,
            result=result,
            completed_phases=completed_phases,
            build_iterations=build_iterations,
            current_slice=phase.slice_id,
            slice_statuses=slice_statuses,
            review_results=review_results,
            spec_check_results=spec_check_results,
            slice_retry_counts=slice_retry_counts,
            slice_commits=slice_commits,
            whole_spec_fix_attempted=whole_spec_fix_attempted,
        )
        raise PhaseExecutionError(result.exit_code)

    try:
        validate_phase_outputs(repo_root, phase)
    except (FileNotFoundError, ValueError) as exc:
        _record_failure(
            paths=paths,
            phase=phase,
            result=PhaseResult(exit_code=1, command=result.command, log_path=result.log_path),
            completed_phases=completed_phases,
            build_iterations=build_iterations,
            current_slice=phase.slice_id,
            slice_statuses=slice_statuses,
            review_results=review_results,
            spec_check_results=spec_check_results,
            slice_retry_counts=slice_retry_counts,
            slice_commits=slice_commits,
            whole_spec_fix_attempted=whole_spec_fix_attempted,
            error_message=str(exc),
        )
        raise

    return result


def _phase_number_for_slice_start(
    repo_root: Path,
    slice_id: str,
    *,
    prior_state: dict[str, Any] | None,
    review_results: dict[str, str],
    spec_check_results: dict[str, str],
) -> tuple[int, int]:
    start_phase = 1
    build_start_iteration = 1

    if prior_state and prior_state.get("current_slice") == slice_id:
        current_phase = prior_state.get("current_phase")
        current_iteration = int(prior_state.get("build_iterations", 0))
        phase_map = {
            "01-slice2metaplan": 1,
            "02-metaplan2detailedplan": 2,
            "03-detailedplan2tasks": 3,
            "04-tasks2build": 4,
            "05-review": 5,
            "06-spec-check": 6,
        }
        if current_phase in phase_map:
            start_phase = phase_map[current_phase]
        if current_phase == "04-tasks2build":
            build_start_iteration = current_iteration + 1

    if review_results.get(slice_id) == "fail":
        start_phase = 4
        build_start_iteration = 1
    if spec_check_results.get(slice_id) == "fail":
        start_phase = 2
        build_start_iteration = 1

    phase_specs = {
        1: build_slice_phase(repo_root, "01-slice2metaplan", slice_id),
        2: build_slice_phase(repo_root, "02-metaplan2detailedplan", slice_id),
        3: build_slice_phase(repo_root, "03-detailedplan2tasks", slice_id),
    }
    if start_phase > 1 and not phase_outputs_are_valid(repo_root, phase_specs[1]):
        return 1, 1
    if start_phase > 2 and not phase_outputs_are_valid(repo_root, phase_specs[2]):
        return 2, 1
    if start_phase > 3 and not phase_outputs_are_valid(repo_root, phase_specs[3]):
        return 3, 1
    return start_phase, build_start_iteration


def run_slice_pipeline(
    *,
    repo_root: Path,
    args: argparse.Namespace,
    paths: RunnerPaths,
    slice_entry: dict[str, Any],
    completed_phases: list[str],
    slice_statuses: dict[str, str],
    review_results: dict[str, str],
    spec_check_results: dict[str, str],
    slice_retry_counts: dict[str, int],
    slice_commits: dict[str, str],
    prior_state: dict[str, Any] | None,
    whole_spec_fix_attempted: bool,
) -> None:
    slice_id = str(slice_entry["slice_id"])
    if slice_statuses.get(slice_id) == "committed" and slice_id in slice_commits:
        return

    start_phase, build_start_iteration = _phase_number_for_slice_start(
        repo_root,
        slice_id,
        prior_state=prior_state,
        review_results=review_results,
        spec_check_results=spec_check_results,
    )

    while True:
        if start_phase <= 1:
            slice_statuses[slice_id] = "metaplanning"
            phase = build_slice_phase(repo_root, "01-slice2metaplan", slice_id)
            result = execute_phase(
                phase=phase,
                repo_root=repo_root,
                paths=paths,
                args=args,
                completed_phases=completed_phases,
                build_iterations=0,
                slice_statuses=slice_statuses,
                review_results=review_results,
                spec_check_results=spec_check_results,
                slice_retry_counts=slice_retry_counts,
                slice_commits=slice_commits,
                whole_spec_fix_attempted=whole_spec_fix_attempted,
            )
            record_run_state(
                paths=paths,
                status="running",
                current_phase=phase.key,
                current_slice=slice_id,
                completed_phases=completed_phases,
                build_iterations=0,
                last_exit_code=0,
                last_command=result.command,
                last_log_path=result.log_path,
                slice_statuses=slice_statuses,
                review_results=review_results,
                spec_check_results=spec_check_results,
                slice_retry_counts=slice_retry_counts,
                slice_commits=slice_commits,
                whole_spec_fix_attempted=whole_spec_fix_attempted,
            )

        if start_phase <= 2:
            slice_statuses[slice_id] = "detailed_planning"
            phase = build_slice_phase(repo_root, "02-metaplan2detailedplan", slice_id)
            result = execute_phase(
                phase=phase,
                repo_root=repo_root,
                paths=paths,
                args=args,
                completed_phases=completed_phases,
                build_iterations=0,
                slice_statuses=slice_statuses,
                review_results=review_results,
                spec_check_results=spec_check_results,
                slice_retry_counts=slice_retry_counts,
                slice_commits=slice_commits,
                whole_spec_fix_attempted=whole_spec_fix_attempted,
            )
            record_run_state(
                paths=paths,
                status="running",
                current_phase=phase.key,
                current_slice=slice_id,
                completed_phases=completed_phases,
                build_iterations=0,
                last_exit_code=0,
                last_command=result.command,
                last_log_path=result.log_path,
                slice_statuses=slice_statuses,
                review_results=review_results,
                spec_check_results=spec_check_results,
                slice_retry_counts=slice_retry_counts,
                slice_commits=slice_commits,
                whole_spec_fix_attempted=whole_spec_fix_attempted,
            )

        if start_phase <= 3:
            slice_statuses[slice_id] = "tasking"
            phase = build_slice_phase(repo_root, "03-detailedplan2tasks", slice_id)
            result = execute_phase(
                phase=phase,
                repo_root=repo_root,
                paths=paths,
                args=args,
                completed_phases=completed_phases,
                build_iterations=0,
                slice_statuses=slice_statuses,
                review_results=review_results,
                spec_check_results=spec_check_results,
                slice_retry_counts=slice_retry_counts,
                slice_commits=slice_commits,
                whole_spec_fix_attempted=whole_spec_fix_attempted,
            )
            record_run_state(
                paths=paths,
                status="running",
                current_phase=phase.key,
                current_slice=slice_id,
                completed_phases=completed_phases,
                build_iterations=0,
                last_exit_code=0,
                last_command=result.command,
                last_log_path=result.log_path,
                slice_statuses=slice_statuses,
                review_results=review_results,
                spec_check_results=spec_check_results,
                slice_retry_counts=slice_retry_counts,
                slice_commits=slice_commits,
                whole_spec_fix_attempted=whole_spec_fix_attempted,
            )

        queue_state: dict[str, Any] | None = None
        if start_phase <= 4:
            slice_statuses[slice_id] = "building"
            for iteration in range(build_start_iteration, args.max_build_iterations + 1):
                phase = build_slice_phase(repo_root, "04-tasks2build", slice_id, iteration=iteration)
                result = execute_phase(
                    phase=phase,
                    repo_root=repo_root,
                    paths=paths,
                    args=args,
                    completed_phases=completed_phases,
                    build_iterations=iteration,
                    slice_statuses=slice_statuses,
                    review_results=review_results,
                    spec_check_results=spec_check_results,
                    slice_retry_counts=slice_retry_counts,
                    slice_commits=slice_commits,
                    whole_spec_fix_attempted=whole_spec_fix_attempted,
                )
                queue_state = read_queue_state(repo_root / "tasks/queue-state.json", current_slice=slice_id)
                record_run_state(
                    paths=paths,
                    status="running",
                    current_phase=phase.key,
                    current_slice=slice_id,
                    completed_phases=completed_phases,
                    build_iterations=iteration,
                    last_exit_code=0,
                    last_command=result.command,
                    last_log_path=result.log_path,
                    slice_statuses=slice_statuses,
                    review_results=review_results,
                    spec_check_results=spec_check_results,
                    slice_retry_counts=slice_retry_counts,
                    slice_commits=slice_commits,
                    whole_spec_fix_attempted=whole_spec_fix_attempted,
                )
                if not should_continue_build_loop(queue_state):
                    break
            else:
                raise RuntimeError(f"slice {slice_id} exceeded --max-build-iterations")

        slice_statuses[slice_id] = "reviewing"
        review_phase = build_slice_phase(repo_root, "05-review", slice_id)
        review_result = execute_phase(
            phase=review_phase,
            repo_root=repo_root,
            paths=paths,
            args=args,
            completed_phases=completed_phases,
            build_iterations=0,
            slice_statuses=slice_statuses,
            review_results=review_results,
            spec_check_results=spec_check_results,
            slice_retry_counts=slice_retry_counts,
            slice_commits=slice_commits,
            whole_spec_fix_attempted=whole_spec_fix_attempted,
        )
        review_results[slice_id] = parse_result_marker(
            repo_root / f"tasks/review-{slice_id}.md",
            subject="review",
            allowed={"pass", "fail"},
        )
        record_run_state(
            paths=paths,
            status="running",
            current_phase=review_phase.key,
            current_slice=slice_id,
            completed_phases=completed_phases,
            build_iterations=0,
            last_exit_code=0,
            last_command=review_result.command,
            last_log_path=review_result.log_path,
            slice_statuses=slice_statuses,
            review_results=review_results,
            spec_check_results=spec_check_results,
            slice_retry_counts=slice_retry_counts,
            slice_commits=slice_commits,
            whole_spec_fix_attempted=whole_spec_fix_attempted,
        )
        if review_results[slice_id] == "fail":
            slice_retry_counts[slice_id] = slice_retry_counts.get(slice_id, 0) + 1
            slice_statuses[slice_id] = "review_failed"
            if slice_retry_counts[slice_id] > args.max_slice_retries:
                raise RuntimeError(f"slice {slice_id} exceeded --max-slice-retries after review failures")
            start_phase = 4
            build_start_iteration = 1
            continue

        slice_statuses[slice_id] = "spec_checking"
        spec_phase = build_slice_phase(repo_root, "06-spec-check", slice_id)
        spec_result = execute_phase(
            phase=spec_phase,
            repo_root=repo_root,
            paths=paths,
            args=args,
            completed_phases=completed_phases,
            build_iterations=0,
            slice_statuses=slice_statuses,
            review_results=review_results,
            spec_check_results=spec_check_results,
            slice_retry_counts=slice_retry_counts,
            slice_commits=slice_commits,
            whole_spec_fix_attempted=whole_spec_fix_attempted,
        )
        spec_check_payload = read_spec_check_result(
            repo_root / f"tasks/spec-check-{slice_id}.json",
            current_slice=slice_id,
        )
        spec_check_results[slice_id] = str(spec_check_payload["result"])
        record_run_state(
            paths=paths,
            status="running",
            current_phase=spec_phase.key,
            current_slice=slice_id,
            completed_phases=completed_phases,
            build_iterations=0,
            last_exit_code=0,
            last_command=spec_result.command,
            last_log_path=spec_result.log_path,
            slice_statuses=slice_statuses,
            review_results=review_results,
            spec_check_results=spec_check_results,
            slice_retry_counts=slice_retry_counts,
            slice_commits=slice_commits,
            whole_spec_fix_attempted=whole_spec_fix_attempted,
        )
        if spec_check_results[slice_id] == "fail":
            slice_retry_counts[slice_id] = slice_retry_counts.get(slice_id, 0) + 1
            slice_statuses[slice_id] = "spec_check_failed"
            if slice_retry_counts[slice_id] > args.max_slice_retries:
                raise RuntimeError(f"slice {slice_id} exceeded --max-slice-retries after spec-check failures")
            start_phase = 2
            build_start_iteration = 1
            continue

        slice_statuses[slice_id] = "committing"
        sha = commit_repo_state(repo_root, SLICE_COMMIT_TEMPLATE.format(slice_id=slice_id))
        slice_commits[slice_id] = sha
        slice_statuses[slice_id] = "committed"
        record_run_state(
            paths=paths,
            status="running",
            current_phase="06-spec-check",
            current_slice=slice_id,
            completed_phases=completed_phases,
            build_iterations=0,
            last_exit_code=0,
            last_command=spec_result.command,
            last_log_path=spec_result.log_path,
            slice_statuses=slice_statuses,
            review_results=review_results,
            spec_check_results=spec_check_results,
            slice_retry_counts=slice_retry_counts,
            slice_commits=slice_commits,
            whole_spec_fix_attempted=whole_spec_fix_attempted,
        )
        return


def _run_dry_run_preview(repo_root: Path, args: argparse.Namespace, paths: RunnerPaths) -> int:
    preview_slice_id = "SLICE-001"
    manifest_path = repo_root / "plan/slice-manifest.json"
    if manifest_path.exists():
        try:
            slices = read_slice_manifest(manifest_path)
        except (FileNotFoundError, ValueError):
            slices = []
        if slices:
            preview_slice_id = str(slices[0]["slice_id"])

    preview_phases = [
        bootstrap_phase(repo_root),
        build_slice_phase(repo_root, "01-slice2metaplan", preview_slice_id),
        build_slice_phase(repo_root, "02-metaplan2detailedplan", preview_slice_id),
        build_slice_phase(repo_root, "03-detailedplan2tasks", preview_slice_id),
        build_slice_phase(repo_root, "04-tasks2build", preview_slice_id, iteration=1),
        build_slice_phase(repo_root, "05-review", preview_slice_id),
        build_slice_phase(repo_root, "06-spec-check", preview_slice_id),
        build_whole_spec_audit_phase(repo_root),
    ]
    last_result: PhaseResult | None = None
    for phase in preview_phases:
        last_result = run_phase(phase, repo_root, paths, args)
    if last_result is None:
        raise RuntimeError("dry run preview produced no phases")
    record_run_state(
        paths=paths,
        status="dry_run",
        current_phase="07-whole-spec-audit",
        current_slice=None,
        completed_phases=[],
        build_iterations=1,
        last_exit_code=last_result.exit_code,
        last_command=last_result.command,
        last_log_path=last_result.log_path,
        slice_statuses={},
        review_results={},
        spec_check_results={},
        slice_retry_counts={},
        slice_commits={},
        whole_spec_fix_attempted=False,
    )
    return last_result.exit_code


def run_pipeline(repo_root: Path, args: argparse.Namespace) -> int:
    validate_repo_root(repo_root)
    if args.max_build_iterations < 1:
        raise ValueError("--max-build-iterations must be at least 1")
    if args.max_slice_retries < 0:
        raise ValueError("--max-slice-retries must be non-negative")

    paths = RunnerPaths(repo_root)
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    ensure_codex_exists(args.codex_bin, dry_run=args.dry_run)

    if args.dry_run:
        return _run_dry_run_preview(repo_root, args, paths)

    prior_state = load_run_state(paths) if args.resume else None
    if prior_state and prior_state.get("status") == "dry_run":
        prior_state = None
    if not prior_state:
        ensure_clean_worktree(repo_root)

    completed_phases = _revalidate_bootstrap(repo_root, list(prior_state.get("completed_phases", [])) if prior_state else [])
    slice_statuses = _state_dict(prior_state, "slice_statuses", {})
    review_results = _state_dict(prior_state, "review_results", {})
    spec_check_results = _state_dict(prior_state, "spec_check_results", {})
    slice_retry_counts = {
        key: int(value)
        for key, value in _state_dict(prior_state, "slice_retry_counts", {}).items()
        if isinstance(value, int)
    }
    slice_commits = {
        key: str(value)
        for key, value in _state_dict(prior_state, "slice_commits", {}).items()
        if isinstance(value, str)
    }
    whole_spec_fix_attempted = bool(prior_state.get("whole_spec_fix_attempted")) if prior_state else False

    if prior_state and prior_state.get("status") == "completed":
        audit_phase = build_whole_spec_audit_phase(repo_root)
        if phase_outputs_are_valid(repo_root, audit_phase):
            return 0

    try:
        if "00-spec2slices" not in completed_phases:
            phase = bootstrap_phase(repo_root)
            result = execute_phase(
                phase=phase,
                repo_root=repo_root,
                paths=paths,
                args=args,
                completed_phases=completed_phases,
                build_iterations=0,
                slice_statuses=slice_statuses,
                review_results=review_results,
                spec_check_results=spec_check_results,
                slice_retry_counts=slice_retry_counts,
                slice_commits=slice_commits,
                whole_spec_fix_attempted=whole_spec_fix_attempted,
            )
            completed_phases = ["00-spec2slices"]
            record_run_state(
                paths=paths,
                status="running",
                current_phase=phase.key,
                current_slice=None,
                completed_phases=completed_phases,
                build_iterations=0,
                last_exit_code=0,
                last_command=result.command,
                last_log_path=result.log_path,
                slice_statuses=slice_statuses,
                review_results=review_results,
                spec_check_results=spec_check_results,
                slice_retry_counts=slice_retry_counts,
                slice_commits=slice_commits,
                whole_spec_fix_attempted=whole_spec_fix_attempted,
            )

        slices = read_slice_manifest(repo_root / "plan/slice-manifest.json")
        for slice_entry in slices:
            run_slice_pipeline(
                repo_root=repo_root,
                args=args,
                paths=paths,
                slice_entry=slice_entry,
                completed_phases=completed_phases,
                slice_statuses=slice_statuses,
                review_results=review_results,
                spec_check_results=spec_check_results,
                slice_retry_counts=slice_retry_counts,
                slice_commits=slice_commits,
                prior_state=prior_state,
                whole_spec_fix_attempted=whole_spec_fix_attempted,
            )
            prior_state = None

        audit_attempt = 1
        while True:
            audit_phase = build_whole_spec_audit_phase(repo_root, attempt=audit_attempt)
            audit_result = execute_phase(
                phase=audit_phase,
                repo_root=repo_root,
                paths=paths,
                args=args,
                completed_phases=completed_phases,
                build_iterations=0,
                slice_statuses=slice_statuses,
                review_results=review_results,
                spec_check_results=spec_check_results,
                slice_retry_counts=slice_retry_counts,
                slice_commits=slice_commits,
                whole_spec_fix_attempted=whole_spec_fix_attempted,
            )
            audit_status = parse_result_marker(
                repo_root / "docs/release-evidence/whole-spec-audit.md",
                subject="whole-spec audit",
                allowed={"pass", "fail"},
            )
            if audit_status == "pass":
                final_commit_sha = commit_repo_state(repo_root, FINAL_COMMIT_MESSAGE)
                slice_commits["FINAL"] = final_commit_sha
                completed_phases = ["00-spec2slices", "07-whole-spec-audit"]
                record_run_state(
                    paths=paths,
                    status="completed",
                    current_phase=audit_phase.key,
                    current_slice=None,
                    completed_phases=completed_phases,
                    build_iterations=0,
                    last_exit_code=0,
                    last_command=audit_result.command,
                    last_log_path=audit_result.log_path,
                    slice_statuses=slice_statuses,
                    review_results=review_results,
                    spec_check_results=spec_check_results,
                    slice_retry_counts=slice_retry_counts,
                    slice_commits=slice_commits,
                    whole_spec_fix_attempted=whole_spec_fix_attempted,
                )
                return 0

            if whole_spec_fix_attempted:
                raise RuntimeError("whole-spec audit failed after the synthetic whole-spec fix slice")

            whole_spec_fix_attempted = True
            synthetic_slice = {
                "slice_id": WHOLE_SPEC_FIX_SLICE_ID,
                "title": "Whole-spec audit fix pass",
                "goal": "Address the whole-spec audit failures before final closure.",
                "source_spec_refs": ["spec/oh-my-lawd.md"],
                "acceptance_gates": ["WHOLE-SPEC-AUDIT"],
                "depends_on_slices": [],
                "status": "synthetic_fix",
            }
            run_slice_pipeline(
                repo_root=repo_root,
                args=args,
                paths=paths,
                slice_entry=synthetic_slice,
                completed_phases=completed_phases,
                slice_statuses=slice_statuses,
                review_results=review_results,
                spec_check_results=spec_check_results,
                slice_retry_counts=slice_retry_counts,
                slice_commits=slice_commits,
                prior_state=None,
                whole_spec_fix_attempted=whole_spec_fix_attempted,
            )
            audit_attempt += 1
    except PhaseExecutionError as exc:
        return exc.exit_code


def run_state_projection(repo_root: Path, args: argparse.Namespace) -> int:
    run_state_path = Path(args.run_state_path)
    if not run_state_path.is_absolute():
        run_state_path = repo_root / run_state_path
    if args.verbose:
        print(f"[runner] state.show path={run_state_path}", file=sys.stderr)
    projection = project_persisted_run_state(
        run_state_path,
        now_timestamp=args.now_timestamp,
        freshness_slo_seconds=args.freshness_slo_seconds,
        operator_run_state_path=str(run_state_path),
    )
    print(json.dumps(asdict(projection), indent=2))
    return 0


def run_extension_onboarding_surface(repo_root: Path, args: argparse.Namespace) -> int:
    if args.verbose:
        print(f"[runner] extension.onboard extension_id={args.extension_id}", file=sys.stderr)
    projection = run_extension_onboarding(
        repo_root=repo_root,
        extension_id=args.extension_id,
        manifest_path=Path(args.manifest_path),
        config_path=Path(args.config_path),
        now_timestamp=args.now_timestamp,
        state_dir=Path(args.state_dir),
    )
    print(json.dumps(asdict(projection), indent=2))
    return 0


def run_extension_status_surface(repo_root: Path, args: argparse.Namespace) -> int:
    if args.verbose:
        print(f"[runner] extension.status extension_id={args.extension_id}", file=sys.stderr)
    projection = load_extension_onboarding_projection(
        repo_root=repo_root,
        extension_id=args.extension_id,
        state_dir=Path(args.state_dir),
    )
    print(json.dumps(projection, indent=2))
    return 0


def dispatch_command(repo_root: Path, args: argparse.Namespace) -> int:
    if args.command_group == "pipeline":
        return run_pipeline(repo_root, args)
    if args.command_group == "state" and getattr(args, "state_action", None) == "show":
        return run_state_projection(repo_root, args)
    if args.command_group == "extension" and getattr(args, "extension_action", None) == "onboard":
        return run_extension_onboarding_surface(repo_root, args)
    if args.command_group == "extension" and getattr(args, "extension_action", None) == "status":
        return run_extension_status_surface(repo_root, args)
    raise ValueError(f"Unknown command selection: group={args.command_group}")


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(normalize_command_argv(raw_argv))
    repo_root = default_repo_root()
    try:
        return dispatch_command(repo_root, args)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
