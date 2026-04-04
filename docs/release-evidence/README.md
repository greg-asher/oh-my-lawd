# Release Evidence

This directory is the repo-tracked evidence surface for slice completion and whole-spec closure.

## Contents
- `inputs/`: persisted runtime `run_state` JSON files generated through `scripts/generate_release_evidence_inputs.py`
- `scripted-checks.md`: scripted acceptance and regression commands
- `walkthroughs/`: live operator walkthrough records on the real CLI surface
- `closure-audit.md`: preserved-seam and release-blocking gate audit for the current release set
- `whole-spec-audit.md`: final 07 whole-spec audit output used to close the slice pipeline

## Existing Live Evidence Reused Here
- Approval scope and invalidation surface: `tasks/TASK-023.md`
- Command parity and next-command guidance: `tasks/TASK-022.md`
- Extension onboarding surface: `tasks/TASK-026.md`
- Policy profile visibility: `tasks/TASK-027.md`

## Generation
Regenerate the persisted runtime-state walkthrough inputs with:

```bash
python3 scripts/generate_release_evidence_inputs.py
```

The generated files are:
- `inputs/w7-provider-rejection-run-state.json`
- `inputs/w8-loop-contained-run-state.json`
- `inputs/w9-failed-resume-run-state.json`

## Slice Pipeline

The slice runner adds one repo-wide closure artifact after slice commits complete:

- `whole-spec-audit.md`: final repository-wide audit proving that passing slice artifacts still add up to direct spec compliance
