# 07-whole-spec-audit

You are performing the final repository-wide audit after all planned slices have passed review and spec-check.

## Mission

Audit the entire repository against the active `/spec` set and determine whether repository completion claims are justified.

## Required reads

Read:
- the full `/spec` set
- `/plan`
- `/plan/slice-manifest.json`
- all slice review and spec-check outputs
- release evidence under `docs/release-evidence/`
- the implemented code and operator surface

## Required output

Write `docs/release-evidence/whole-spec-audit.md`.

That file must contain:
- `Result: pass|fail`
- audit scope
- preserved seams checked
- missing or weak coverage, if any
- required fix direction if the audit fails

## Non-negotiable rules

1. Do not treat slice-level success as proof that the whole repo satisfies the full spec.
2. Check preserved, canonical, and release-blocking seams across the whole repository.
3. Fail the audit if completion depends on demo-only or evidence-only substitutes.
