#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

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
    "plan/implementation-brief.json",
    "plan/preserved-seams.md",
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


class PhaseExecutionTimeoutError(RuntimeError):
    def __init__(self, message: str, result: PhaseResult) -> None:
        super().__init__(message)
        self.result = result


class PhaseExecutionInterruptedError(RuntimeError):
    def __init__(self, message: str, result: PhaseResult) -> None:
        super().__init__(message)
        self.result = result


class _StreamCapture:
    def __init__(self, phase_key: str, stream_name: str, target: TextIO, use_color: bool) -> None:
        self.phase_key = phase_key
        self.stream_name = stream_name
        self.target = target
        self.use_color = use_color
        self.buffer: list[str] = []
        self.lock = threading.Lock()

    def write(self, message: str) -> None:
        if not message:
            return
        self.buffer.append(message)
        rendered = format_runner_event(
            phase_key=self.phase_key,
            stream=self.stream_name,
            message=message.rstrip("\n"),
            use_color=self.use_color,
        )
        if message.endswith("\n"):
            rendered += "\n"
        with self.lock:
            self.target.write(rendered)
            self.target.flush()

    def getvalue(self) -> str:
        return "".join(self.buffer)


def stream_supports_color(stream: TextIO) -> bool:
    return hasattr(stream, "isatty") and stream.isatty()


def format_runner_event(*, phase_key: str, stream: str, message: str, use_color: bool) -> str:
    prefix = f"[{phase_key}:{stream}]"
    if not use_color:
        return f"{prefix} {message}"

    dim = "\033[2m"
    reset = "\033[0m"
    stdout_color = "\033[36m"
    stderr_color = "\033[33m"
    color = stdout_color if stream == "stdout" else stderr_color
    return f"{dim}{prefix}{reset} {color}{message}{reset}"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Oh My Lawd prompt-pack pipeline through Codex."
    )
    parser.add_argument("--resume", action="store_true", help="Resume from .ohmylawd/run-state.json if present.")
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print the current runner state without invoking Codex.",
    )
    parser.add_argument(
        "--max-build-iterations",
        type=int,
        default=25,
        help="Maximum number of prompt-pack/03 iterations before failing closed.",
    )
    parser.add_argument(
        "--phase-timeout-seconds",
        type=int,
        default=None,
        help="Optional per-phase timeout in seconds before the runner aborts the current Codex invocation.",
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


def load_json(path: Path) -> object:
    return json.loads(path.read_text())


def validate_queue_state(queue_state: object) -> list[str]:
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


def phase_outputs_are_valid(repo_root: Path, phase: PhaseSpec) -> bool:
    try:
        validate_phase_outputs(repo_root, phase)
    except (FileNotFoundError, ValueError):
        return False
    return True


def read_queue_state(queue_state_path: Path) -> dict:
    if not queue_state_path.exists():
        raise FileNotFoundError(f"Missing queue state file: {queue_state_path}")
    queue_state = load_json(queue_state_path)
    errors = validate_queue_state(queue_state)
    if errors:
        raise ValueError(f"Invalid queue-state.json: {'; '.join(errors)}")
    if not isinstance(queue_state, dict):
        raise ValueError("Invalid queue-state.json: queue state must be a JSON object")
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


def print_phase_banner(phase: PhaseSpec, log_path: Path, *, use_color: bool) -> None:
    message = f"starting {phase.key} -> {log_path}"
    if use_color:
        message = f"\033[1m{message}\033[0m"
    print(message, file=sys.stderr)


def print_phase_summary(phase: PhaseSpec, summary_status: str, log_path: Path, *, use_color: bool) -> None:
    message = f"finished {phase.key} [{summary_status}] -> {log_path}"
    if use_color:
        message = f"\033[1m{message}\033[0m"
    print(message, file=sys.stderr)


def terminate_process(process: subprocess.Popen[str], *, grace_period_seconds: float = 2.0) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=grace_period_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def stream_process_output(
    process: subprocess.Popen[str],
    phase_key: str,
    *,
    stdout_use_color: bool,
    stderr_use_color: bool,
    phase_timeout_seconds: int | None,
) -> tuple[str, str, int, bool]:
    stdout_target = _StreamCapture(phase_key, "stdout", sys.stdout, stdout_use_color)
    stderr_target = _StreamCapture(phase_key, "stderr", sys.stderr, stderr_use_color)

    def pump(source: TextIO | None, target: _StreamCapture) -> None:
        if source is None:
            return
        for chunk in iter(source.readline, ""):
            target.write(chunk)
        source.close()

    threads = [
        threading.Thread(target=pump, args=(process.stdout, stdout_target), daemon=True),
        threading.Thread(target=pump, args=(process.stderr, stderr_target), daemon=True),
    ]
    for thread in threads:
        thread.start()

    timed_out = False
    try:
        process.wait(timeout=phase_timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        terminate_process(process)
    except KeyboardInterrupt:
        terminate_process(process)
        raise

    for thread in threads:
        thread.join()

    exit_code = process.returncode if process.returncode is not None else process.wait()
    return stdout_target.getvalue(), stderr_target.getvalue(), exit_code, timed_out


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

    stdout_use_color = stream_supports_color(sys.stdout)
    stderr_use_color = stream_supports_color(sys.stderr)
    print_phase_banner(phase, log_path, use_color=stderr_use_color)

    process = subprocess.Popen(
        command,
        cwd=repo_root,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    assert process.stdin is not None
    stdin_write_error = False
    try:
        process.stdin.write(prompt_text)
    except BrokenPipeError:
        stdin_write_error = True
    finally:
        try:
            process.stdin.close()
        except BrokenPipeError:
            stdin_write_error = True
    try:
        stdout, stderr, exit_code, timed_out = stream_process_output(
            process,
            phase.key,
            stdout_use_color=stdout_use_color,
            stderr_use_color=stderr_use_color,
            phase_timeout_seconds=args.phase_timeout_seconds,
        )
    except KeyboardInterrupt as exc:
        stderr = "runner interrupted: execution stopped by operator\n"
        write_phase_log(
            log_path=log_path,
            phase=phase,
            command=command,
            prompt_text=prompt_text,
            exit_code=130,
            stdout="",
            stderr=stderr,
            dry_run=False,
        )
        print_phase_summary(phase, "interrupted", log_path, use_color=stderr_use_color)
        raise PhaseExecutionInterruptedError(
            "execution interrupted by operator",
            PhaseResult(exit_code=130, command=command, log_path=log_path),
        ) from exc

    if stdin_write_error:
        stderr = f"{stderr}runner warning: subprocess closed stdin before prompt delivery\n"

    if timed_out:
        timeout_message = (
            f"runner timeout: phase exceeded {args.phase_timeout_seconds} seconds and was terminated\n"
        )
        stderr = f"{stderr}{timeout_message}"
        write_phase_log(
            log_path=log_path,
            phase=phase,
            command=command,
            prompt_text=prompt_text,
            exit_code=124,
            stdout=stdout,
            stderr=stderr,
            dry_run=False,
        )
        print_phase_summary(phase, "failed (timeout)", log_path, use_color=stderr_use_color)
        raise PhaseExecutionTimeoutError(
            timeout_message.rstrip(),
            PhaseResult(exit_code=124, command=command, log_path=log_path),
        )

    write_phase_log(
        log_path=log_path,
        phase=phase,
        command=command,
        prompt_text=prompt_text,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        dry_run=False,
    )
    summary_status = "ok" if exit_code == 0 else f"failed ({exit_code})"
    print_phase_summary(phase, summary_status, log_path, use_color=stderr_use_color)
    return PhaseResult(exit_code=exit_code, command=command, log_path=log_path)


def save_run_state(paths: RunnerPaths, payload: dict) -> None:
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    paths.run_state_path.write_text(json.dumps(payload, indent=2) + "\n")


def load_run_state(paths: RunnerPaths) -> dict | None:
    if not paths.run_state_path.exists():
        return None
    payload = load_json(paths.run_state_path)
    if not isinstance(payload, dict):
        raise ValueError("run-state.json must be a JSON object")
    return payload


def build_run_state_payload(
    *,
    status: str,
    current_phase: str,
    completed_phases: list[str],
    build_iterations: int,
    last_exit_code: int,
    last_command: list[str],
    last_log_path: Path,
    error_message: str | None = None,
) -> dict:
    payload = {
        "status": status,
        "current_phase": current_phase,
        "completed_phases": completed_phases,
        "build_iterations": build_iterations,
        "last_exit_code": last_exit_code,
        "last_command": last_command,
        "last_log_path": str(last_log_path),
        "updated_at": utc_now(),
    }
    if error_message is not None:
        payload["last_error"] = error_message
    return payload


def format_run_state_summary(state: dict) -> str:
    completed_phases = state.get("completed_phases")
    completed_display = "(none)"
    if isinstance(completed_phases, list) and completed_phases:
        completed_display = ", ".join(str(phase) for phase in completed_phases)

    lines = [
        f"Runner status: {state.get('status', 'unknown')}",
        f"Current phase: {state.get('current_phase', 'unknown')}",
        f"Completed phases: {completed_display}",
        f"Build iterations: {state.get('build_iterations', 'unknown')}",
        f"Last exit code: {state.get('last_exit_code', 'unknown')}",
        f"Last log path: {state.get('last_log_path', 'unknown')}",
        f"Updated at: {state.get('updated_at', 'unknown')}",
    ]
    if "last_error" in state:
        lines.append(f"Last error: {state['last_error']}")
    return "\n".join(lines)


def print_run_status(
    paths: RunnerPaths,
    *,
    output: TextIO | None = None,
    error_output: TextIO | None = None,
) -> int:
    output = sys.stdout if output is None else output
    error_output = sys.stderr if error_output is None else error_output
    try:
        state = load_run_state(paths)
    except ValueError as exc:
        print(f"invalid runner state: {exc}", file=error_output)
        return 1

    if state is None:
        print(f"no runner state found at {paths.run_state_path}", file=error_output)
        return 1

    print(format_run_state_summary(state), file=output)
    return 0


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
    error_message: str | None = None,
) -> None:
    save_run_state(
        paths,
        build_run_state_payload(
            status=status,
            current_phase=current_phase,
            completed_phases=completed_phases,
            build_iterations=build_iterations,
            last_exit_code=last_exit_code,
            last_command=last_command,
            last_log_path=last_log_path,
            error_message=error_message,
        ),
    )


def record_phase_state(
    *,
    paths: RunnerPaths,
    status: str,
    phase_key: str,
    completed_phases: list[str],
    build_iterations: int,
    result: PhaseResult,
    error_message: str | None = None,
) -> None:
    record_run_state(
        paths=paths,
        status=status,
        current_phase=phase_key,
        completed_phases=completed_phases,
        build_iterations=build_iterations,
        last_exit_code=result.exit_code,
        last_command=result.command,
        last_log_path=result.log_path,
        error_message=error_message,
    )


def revalidate_completed_phases(
    repo_root: Path,
    phase_specs: list[PhaseSpec],
    prior_completed_phases: list[str],
) -> list[str]:
    validated: list[str] = []
    for phase in phase_specs:
        if phase.key not in prior_completed_phases:
            break
        if not phase_outputs_are_valid(repo_root, phase):
            break
        validated.append(phase.key)
    return validated


def run_pipeline(repo_root: Path, args: argparse.Namespace) -> int:
    validate_repo_root(repo_root)
    if args.max_build_iterations < 1:
        raise ValueError("--max-build-iterations must be at least 1")
    if args.phase_timeout_seconds is not None and args.phase_timeout_seconds < 1:
        raise ValueError("--phase-timeout-seconds must be at least 1")

    paths = RunnerPaths(repo_root)
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    ensure_codex_exists(args.codex_bin, dry_run=args.dry_run)

    phase_specs = build_phase_specs(repo_root)
    prior_state = load_run_state(paths) if args.resume and not args.dry_run else None
    if prior_state and prior_state.get("status") == "dry_run":
        prior_state = None

    completed_phases = (
        revalidate_completed_phases(
            repo_root,
            phase_specs,
            list(prior_state.get("completed_phases", [])),
        )
        if prior_state
        else []
    )

    if prior_state and prior_state.get("status") == "completed":
        try:
            queue_state = read_queue_state(repo_root / "tasks/queue-state.json")
        except (FileNotFoundError, ValueError):
            queue_state = None
        if (
            completed_phases == [phase.key for phase in phase_specs]
            and queue_state is not None
            and not should_continue_build_loop(queue_state)
        ):
            if args.verbose:
                print("[runner] prior run already completed", file=sys.stderr)
            return 0

    for phase in phase_specs:
        if phase.key in completed_phases:
            continue

        try:
            result = run_phase(phase, repo_root, paths, args)
        except PhaseExecutionTimeoutError as exc:
            record_phase_state(
                paths=paths,
                status="failed",
                phase_key=phase.key,
                completed_phases=completed_phases,
                build_iterations=0,
                result=exc.result,
                error_message=str(exc),
            )
            return exc.result.exit_code
        except PhaseExecutionInterruptedError as exc:
            record_phase_state(
                paths=paths,
                status="interrupted",
                phase_key=phase.key,
                completed_phases=completed_phases,
                build_iterations=0,
                result=exc.result,
                error_message=str(exc),
            )
            return exc.result.exit_code
        if result.exit_code != 0:
            record_phase_state(
                paths=paths,
                status="failed",
                phase_key=phase.key,
                completed_phases=completed_phases,
                build_iterations=0,
                result=result,
            )
            return result.exit_code

        if not args.dry_run:
            try:
                validate_phase_outputs(repo_root, phase)
            except (FileNotFoundError, ValueError) as exc:
                record_phase_state(
                    paths=paths,
                    status="failed",
                    phase_key=phase.key,
                    completed_phases=completed_phases,
                    build_iterations=0,
                    result=PhaseResult(exit_code=1, command=result.command, log_path=result.log_path),
                    error_message=str(exc),
                )
                raise

        completed_phases.append(phase.key)
        record_phase_state(
            paths=paths,
            status="running" if not args.dry_run else "dry_run",
            phase_key=phase.key,
            completed_phases=completed_phases if not args.dry_run else [],
            build_iterations=0,
            result=PhaseResult(exit_code=0, command=result.command, log_path=result.log_path),
        )

    if args.dry_run:
        dry_run_phase = build_loop_phase(repo_root, 1)
        result = run_phase(dry_run_phase, repo_root, paths, args)
        record_run_state(
            paths=paths,
            status="dry_run",
            current_phase=dry_run_phase.key,
            completed_phases=[],
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
        try:
            result = run_phase(phase, repo_root, paths, args)
        except PhaseExecutionTimeoutError as exc:
            record_phase_state(
                paths=paths,
                status="failed",
                phase_key=phase.key,
                completed_phases=completed_phases,
                build_iterations=iteration,
                result=exc.result,
                error_message=str(exc),
            )
            return exc.result.exit_code
        except PhaseExecutionInterruptedError as exc:
            record_phase_state(
                paths=paths,
                status="interrupted",
                phase_key=phase.key,
                completed_phases=completed_phases,
                build_iterations=iteration,
                result=exc.result,
                error_message=str(exc),
            )
            return exc.result.exit_code
        if result.exit_code != 0:
            record_phase_state(
                paths=paths,
                status="failed",
                phase_key=phase.key,
                completed_phases=completed_phases,
                build_iterations=iteration,
                result=result,
            )
            return result.exit_code

        try:
            queue_state = read_queue_state(repo_root / "tasks/queue-state.json")
        except (FileNotFoundError, ValueError) as exc:
            record_phase_state(
                paths=paths,
                status="failed",
                phase_key=phase.key,
                completed_phases=completed_phases,
                build_iterations=iteration,
                result=PhaseResult(exit_code=1, command=result.command, log_path=result.log_path),
                error_message=str(exc),
            )
            raise
        status = "running"
        if not should_continue_build_loop(queue_state):
            status = "completed"

        record_phase_state(
            paths=paths,
            status=status,
            phase_key=phase.key,
            completed_phases=completed_phases + ([phase.key] if status == "completed" else []),
            build_iterations=iteration,
            result=PhaseResult(exit_code=0, command=result.command, log_path=result.log_path),
        )

        if status == "completed":
            return 0

    record_run_state(
        paths=paths,
        status="failed",
        current_phase="03-tasks2build",
        completed_phases=completed_phases,
        build_iterations=args.max_build_iterations,
        last_exit_code=1,
        last_command=[],
        last_log_path=paths.logs_dir / f"03-tasks2build-{args.max_build_iterations:03d}.log",
        error_message=f"Exceeded max build iterations ({args.max_build_iterations}) before queue exhaustion",
    )
    raise RuntimeError(
        f"Exceeded max build iterations ({args.max_build_iterations}) before queue exhaustion"
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = default_repo_root()
    if args.status:
        return print_run_status(RunnerPaths(repo_root))
    return run_pipeline(repo_root, args)


if __name__ == "__main__":
    raise SystemExit(main())
