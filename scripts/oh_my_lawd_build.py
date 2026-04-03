#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

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


@dataclass(frozen=True)
class PhaseResult:
    exit_code: int
    command: list[str]
    log_path: Path


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Oh My Lawd prompt-pack pipeline through Codex."
    )
    parser.add_argument("--resume", action="store_true", help="Resume from .ohmylawd/run-state.json if present.")
    parser.add_argument(
        "--max-build-iterations",
        type=int,
        default=25,
        help="Maximum number of prompt-pack/03 iterations before failing closed.",
    )
    parser.add_argument("--codex-bin", default="codex", help="Path to the Codex CLI binary.")
    parser.add_argument("--model", help="Optional Codex model override.")
    parser.add_argument("--profile", help="Optional Codex profile name.")
    parser.add_argument("--dry-run", action="store_true", help="Write logs for planned commands without executing Codex.")
    parser.add_argument("--verbose", action="store_true", help="Print runner progress to stderr.")
    return parser


def default_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def validate_repo_root(repo_root: Path) -> None:
    missing = []
    for required in (
        repo_root / "README.md",
        repo_root / "prompt-pack/01-spec2plan.md",
        repo_root / "prompt-pack/02-plan2tasks.md",
        repo_root / "prompt-pack/03-tasks2build.md",
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


def build_phase_specs(repo_root: Path) -> list[PhaseSpec]:
    return [
        PhaseSpec(
            key="01-spec2plan",
            prompt_path=repo_root / "prompt-pack/01-spec2plan.md",
            required_outputs=tuple(repo_root / path for path in PLAN_OUTPUTS),
            log_name="01-spec2plan.log",
        ),
        PhaseSpec(
            key="02-plan2tasks",
            prompt_path=repo_root / "prompt-pack/02-plan2tasks.md",
            required_outputs=tuple(repo_root / path for path in TASK_OUTPUTS),
            log_name="02-plan2tasks.log",
        ),
    ]


def build_loop_phase(repo_root: Path, iteration: int) -> PhaseSpec:
    return PhaseSpec(
        key="03-tasks2build",
        prompt_path=repo_root / "prompt-pack/03-tasks2build.md",
        required_outputs=(repo_root / "tasks/queue-state.json",),
        log_name=f"03-tasks2build-{iteration:03d}.log",
    )


def validate_required_outputs(phase: PhaseSpec) -> list[Path]:
    return [path for path in phase.required_outputs if not path.exists()]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def validate_queue_state(queue_state: dict) -> list[str]:
    errors: list[str] = []
    missing_keys = [key for key in QUEUE_STATE_KEYS if key not in queue_state]
    if missing_keys:
        errors.append(f"missing keys: {', '.join(missing_keys)}")

    for key in ("ready_tasks", "blocked_tasks", "in_progress_tasks", "completed_tasks"):
        value = queue_state.get(key)
        if value is not None and not isinstance(value, list):
            errors.append(f"{key} must be a list")

    recommended_next_task = queue_state.get("recommended_next_task")
    if recommended_next_task is not None and not isinstance(recommended_next_task, str):
        errors.append("recommended_next_task must be a string or null")

    last_generated_at = queue_state.get("last_generated_at")
    if last_generated_at is not None and not isinstance(last_generated_at, str):
        errors.append("last_generated_at must be a string")

    return errors


def validate_phase_outputs(repo_root: Path, phase: PhaseSpec) -> None:
    missing = validate_required_outputs(phase)
    if missing:
        missing_display = ", ".join(str(path.relative_to(repo_root)) for path in missing)
        raise FileNotFoundError(f"{phase.key} did not produce required outputs: {missing_display}")

    if phase.key == "02-plan2tasks":
        task_files = sorted((repo_root / "tasks").glob("TASK-*.md"))
        if not task_files:
            raise FileNotFoundError("02-plan2tasks did not produce any tasks/TASK-*.md files")


def read_queue_state(queue_state_path: Path) -> dict:
    if not queue_state_path.exists():
        raise FileNotFoundError(f"Missing queue state file: {queue_state_path}")
    queue_state = load_json(queue_state_path)
    errors = validate_queue_state(queue_state)
    if errors:
        raise ValueError(f"Invalid queue-state.json: {'; '.join(errors)}")
    return queue_state


def should_continue_build_loop(queue_state: dict) -> bool:
    return bool(
        queue_state.get("recommended_next_task")
        or queue_state.get("ready_tasks")
        or queue_state.get("in_progress_tasks")
    )


def compose_prompt(phase: PhaseSpec, repo_root: Path) -> str:
    preamble = "\n".join(
        [
            f"You are running in automated phase {phase.key}.",
            f"Repository root: {repo_root}",
            "Write artifacts directly into this repository.",
            "Treat the prompt-pack content below as authoritative for this phase.",
            "Stay within the documented phase boundary. Do not skip ahead or redesign the pipeline.",
            "",
        ]
    )
    return preamble + phase.prompt_path.read_text()


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
    log_path.write_text("\n".join(lines).rstrip() + "\n")


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
        print(f"[runner] phase={phase.key} log={log_path}", file=sys.stderr)

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


def save_run_state(paths: RunnerPaths, payload: dict) -> None:
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    paths.run_state_path.write_text(json.dumps(payload, indent=2) + "\n")


def load_run_state(paths: RunnerPaths) -> dict | None:
    if not paths.run_state_path.exists():
        return None
    return load_json(paths.run_state_path)


def record_run_state(
    *,
    paths: RunnerPaths,
    status: str,
    current_phase: str,
    completed_phases: list[str],
    build_iterations: int,
    last_exit_code: int,
    last_command: list[str],
    last_log_path: Path,
) -> None:
    save_run_state(
        paths,
        {
            "status": status,
            "current_phase": current_phase,
            "completed_phases": completed_phases,
            "build_iterations": build_iterations,
            "last_exit_code": last_exit_code,
            "last_command": last_command,
            "last_log_path": str(last_log_path),
            "updated_at": utc_now(),
        },
    )


def run_pipeline(repo_root: Path, args: argparse.Namespace) -> int:
    validate_repo_root(repo_root)
    if args.max_build_iterations < 1:
        raise ValueError("--max-build-iterations must be at least 1")

    paths = RunnerPaths(repo_root)
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    ensure_codex_exists(args.codex_bin, dry_run=args.dry_run)

    prior_state = load_run_state(paths) if args.resume else None
    if prior_state and prior_state.get("status") == "completed":
        if args.verbose:
            print("[runner] prior run already completed", file=sys.stderr)
        return 0

    completed_phases = list(prior_state.get("completed_phases", [])) if prior_state else []

    for phase in build_phase_specs(repo_root):
        if phase.key in completed_phases:
            continue

        result = run_phase(phase, repo_root, paths, args)
        if result.exit_code != 0:
            record_run_state(
                paths=paths,
                status="failed",
                current_phase=phase.key,
                completed_phases=completed_phases,
                build_iterations=0,
                last_exit_code=result.exit_code,
                last_command=result.command,
                last_log_path=result.log_path,
            )
            return result.exit_code

        if not args.dry_run:
            validate_phase_outputs(repo_root, phase)

        completed_phases.append(phase.key)
        record_run_state(
            paths=paths,
            status="running" if not args.dry_run else "dry_run",
            current_phase=phase.key,
            completed_phases=completed_phases,
            build_iterations=0,
            last_exit_code=0,
            last_command=result.command,
            last_log_path=result.log_path,
        )

    if args.dry_run:
        dry_run_phase = build_loop_phase(repo_root, 1)
        result = run_phase(dry_run_phase, repo_root, paths, args)
        record_run_state(
            paths=paths,
            status="dry_run",
            current_phase=dry_run_phase.key,
            completed_phases=completed_phases,
            build_iterations=1,
            last_exit_code=result.exit_code,
            last_command=result.command,
            last_log_path=result.log_path,
        )
        return result.exit_code

    start_iteration = 1
    if prior_state and prior_state.get("current_phase") == "03-tasks2build":
        start_iteration = int(prior_state.get("build_iterations", 0)) + 1

    for iteration in range(start_iteration, args.max_build_iterations + 1):
        phase = build_loop_phase(repo_root, iteration)
        result = run_phase(phase, repo_root, paths, args)
        if result.exit_code != 0:
            record_run_state(
                paths=paths,
                status="failed",
                current_phase=phase.key,
                completed_phases=completed_phases,
                build_iterations=iteration,
                last_exit_code=result.exit_code,
                last_command=result.command,
                last_log_path=result.log_path,
            )
            return result.exit_code

        queue_state = read_queue_state(repo_root / "tasks/queue-state.json")
        status = "running"
        if not should_continue_build_loop(queue_state):
            status = "completed"

        record_run_state(
            paths=paths,
            status=status,
            current_phase=phase.key,
            completed_phases=completed_phases + ([phase.key] if status == "completed" else []),
            build_iterations=iteration,
            last_exit_code=0,
            last_command=result.command,
            last_log_path=result.log_path,
        )

        if status == "completed":
            return 0

    raise RuntimeError(
        f"Exceeded max build iterations ({args.max_build_iterations}) before queue exhaustion"
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = default_repo_root()
    return run_pipeline(repo_root, args)


if __name__ == "__main__":
    raise SystemExit(main())
