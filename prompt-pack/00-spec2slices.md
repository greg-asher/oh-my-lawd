# 00-spec2slices

You are operating inside a repository that contains a `spec/` folder. Your job is to read the active spec set, preserve it as the governing contract, and write the root planning package plus a slice manifest for implementation.

## Mission

Produce the durable `/plan` workspace that anchors implementation and the slice index that drives the runner's outer loop.

The spec remains authoritative. `/plan` is a traceable planning layer. `/tasks` does not exist yet.

## Required outputs

Create or update the full root planning package:
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
- `/plan/slices.md`
- `/plan/slice-manifest.json`

## Slice requirements

`/plan/slices.md` must explain:
- the slicing strategy
- why each slice is a meaningful capability
- which spec sections each slice owns
- the slice execution order

`/plan/slice-manifest.json` must be a JSON object with a `slices` array. Each slice entry must include:
- `slice_id`
- `title`
- `goal`
- `source_spec_refs`
- `acceptance_gates`
- `depends_on_slices`
- `status`

## Non-negotiable rules

1. Read the governing spec documents first.
2. Preserve runtime, orchestration, and product ownership boundaries.
3. Do not invent requirements outside `/spec`.
4. Do not let planning artifacts replace preserved or canonical seams.
5. Slice by testable capability or journey, not by arbitrary subsystem bulk.
6. If the spec is ambiguous, record the ambiguity instead of guessing.

## Slice sizing guidance

Good slices:
- primary operator surface
- approval flow
- recovery and resume
- extension onboarding

Bad slices:
- all runtime
- all product
- finish the repo

## Required final behavior

The root plan must be strong enough that later phases can:
- plan one slice without rereading the whole spec every turn
- trace each slice back to the source spec
- enforce that review and spec-check happen before slice completion
