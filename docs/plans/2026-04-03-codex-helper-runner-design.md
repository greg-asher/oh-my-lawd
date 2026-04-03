# Codex Helper Runner Design

## Summary

This design adds a repo-local helper CLI that runs the existing prompt-pack pipeline autonomously against the cloned repository. The runner will invoke the local `codex` CLI for `prompt-pack/01-spec2plan.md`, then `prompt-pack/02-plan2tasks.md`, then repeatedly invoke `prompt-pack/03-tasks2build.md` until the task queue reports no recommended ready task.

The first version is optimized for unattended demo execution:
- one command from a fresh clone
- sensible defaults
- durable on-disk run state for resume and debugging
- no prompt-pack format changes

## Goals

- Let a user clone the repo and start the pipeline with one command.
- Preserve the intended workflow already documented in the repository.
- Persist stage outputs and runner state so failures are resumable.
- Stop honestly on `codex` failures, missing artifacts, or invalid queue state.

## Non-Goals

- Redesigning the prompt pack itself.
- Building a generic workflow engine for arbitrary prompt sequences.
- Hiding or rewriting Codex output semantics.
- Adding stack-specific build logic for generated applications.

## Recommended Approach

Use a small Python CLI with only standard-library dependencies and a single executable entry point at the repo root, exposed as `bin/oh-my-lawd-build`.

Why this approach:
- Python is a better fit than shell for JSON parsing, subprocess control, timeout handling, and resumable state files.
- A single executable script remains easy to run from a fresh clone.
- Standard-library-only code avoids introducing package-manager setup just to run the helper.

## Runner Contract

### Entry point

- `bin/oh-my-lawd-build`

### Default behavior

1. Confirm the command is running from the repo root.
2. Confirm `codex` is available on `PATH`.
3. Create runner state and logs under `.ohmylawd/`.
4. Run phase `01-spec2plan`.
5. Validate `/plan` exists with expected required artifacts.
6. Run phase `02-plan2tasks`.
7. Validate `/tasks` exists with expected required artifacts.
8. Run phase `03-tasks2build` in a loop.
9. After each build iteration, reload `/tasks/queue-state.json`.
10. Stop successfully only when there is no recommended next ready task left.

### CLI flags

Initial version should support:
- `--resume`: continue from recorded runner state if present
- `--max-build-iterations N`: hard safety cap for `03` loop
- `--codex-bin PATH`: override `codex` binary path
- `--dry-run`: print planned commands without executing them
- `--verbose`: stream more runner diagnostics

Nice-to-have but not required for v1:
- prompt/model passthrough flags
- release-closure mode toggle

## Prompt Invocation Model

The helper should not reinterpret the prompt-pack logic. For each phase it should:

1. Read the relevant prompt-pack markdown file.
2. Wrap it with a minimal repo-specific preamble that states:
   - current repo root
   - expected writable directories
   - execution mode for the current phase
3. Pass the composed prompt to `codex`.
4. Capture stdout, stderr, exit code, start time, and end time in `.ohmylawd/logs/`.

The sequence is fixed:
- `prompt-pack/01-spec2plan.md`
- `prompt-pack/02-plan2tasks.md`
- `prompt-pack/03-tasks2build.md`

`prompt-pack/00-sample-starter-plan.md` remains documentation only and is not part of the automated runner sequence.

## Persisted Runner State

Store machine-readable runner state in `.ohmylawd/run-state.json`.

Suggested shape:

```json
{
  "status": "running",
  "current_phase": "03-tasks2build",
  "completed_phases": [
    "01-spec2plan",
    "02-plan2tasks"
  ],
  "build_iterations": 4,
  "last_exit_code": 0,
  "last_command": ["codex", "..."],
  "last_log_path": ".ohmylawd/logs/03-tasks2build-004.log",
  "updated_at": "2026-04-03T13:00:00Z"
}
```

This state is runner truth, not task truth. It exists to support:
- resume after interruption
- failure inspection
- deterministic phase restarts

## Phase Validation Rules

### After `01-spec2plan`

Require:
- `/plan` exists
- required plan artifacts exist:
  - `/plan/README.md`
  - `/plan/system-summary.md`
  - `/plan/spec-map.md`
  - `/plan/domain-glossary.md`
  - `/plan/invariants.md`
  - `/plan/acceptance-matrix.md`
  - `/plan/build-order.md`
  - `/plan/task-graph.md`
  - `/plan/open-questions.md`
  - `/plan/forbidden-shortcuts.md`
  - `/plan/walkthroughs.md`
  - `/plan/implementation-brief.json`

### After `02-plan2tasks`

Require:
- `/tasks` exists
- required task artifacts exist:
  - `/tasks/README.md`
  - `/tasks/index.md`
  - `/tasks/task-index.json`
  - `/tasks/queue-state.json`
- at least one `TASK-*.md` file exists

### After each `03-tasks2build` loop

Require:
- `/tasks/queue-state.json` remains valid JSON
- queue snapshot contains expected keys:
  - `ready_tasks`
  - `blocked_tasks`
  - `in_progress_tasks`
  - `completed_tasks`
  - `recommended_next_task`
  - `last_generated_at`

Loop exit condition:
- `recommended_next_task` is empty or null
- and `ready_tasks` is empty
- and `in_progress_tasks` is empty

Loop failure conditions:
- `codex` exits non-zero
- queue-state file missing or invalid
- iteration count exceeds `--max-build-iterations`

## Logging

Create:
- `.ohmylawd/logs/01-spec2plan.log`
- `.ohmylawd/logs/02-plan2tasks.log`
- `.ohmylawd/logs/03-tasks2build-001.log`
- etc.

Logs should contain:
- exact spawned command
- phase name
- timestamps
- combined process output
- runner-side validation summary

## Error Handling

The runner should fail closed:
- do not continue past a failed Codex invocation
- do not continue when required artifacts are missing
- do not silently repair malformed queue state

Expected user-facing failure classes:
- missing `codex` binary
- invalid working directory
- phase validation failure
- build loop safety-cap exhaustion
- malformed JSON in runner-controlled decision files

## File Layout

Expected added files:
- `bin/oh-my-lawd-build`
- `scripts/oh_my_lawd_build.py`
- `tests/test_oh_my_lawd_build.py`
- `.gitignore` update for `.ohmylawd/`
- `README.md` update documenting the helper

## Testing Strategy

The runner should have automated tests for:
- argument parsing
- required artifact validation
- queue-state exit decisions
- resume-state handling
- command construction

The repo should also support a local smoke test using a fake `codex` binary or mocked subprocess calls so the runner can be verified without real autonomous generation during unit tests.

## Risks And Tradeoffs

- The helper depends on `codex` CLI behavior remaining stable enough to accept scripted invocation.
- Prompt-pack output quality is still model-dependent; the runner only improves repeatability of orchestration.
- An unattended `03` loop needs a safety cap to avoid infinite churn on unstable task queues.

## Acceptance For This Feature

The helper is successful when:
- a user can clone the repo and run one command
- the command runs `01`, `02`, and looping `03` in order
- outputs are written into `/plan` and `/tasks`
- `.ohmylawd/run-state.json` and logs support resume/debugging
- the runner stops cleanly when the queue is exhausted or fails honestly when it is not
