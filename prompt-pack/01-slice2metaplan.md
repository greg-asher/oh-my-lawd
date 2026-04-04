# 01-slice2metaplan

You are operating on one slice from `plan/slice-manifest.json`.

## Mission

Read the current slice entry, the root planning artifacts, and the referenced source spec sections. Produce the slice metaplan that explains how this slice should be implemented without yet decomposing it into task-level detail.

## Required reads

Read:
- `/spec`
- `/plan/README.md`
- `/plan/spec-map.md`
- `/plan/invariants.md`
- `/plan/preserved-seams.md` when present
- `/plan/slices.md`
- `/plan/slice-manifest.json`

## Required output

Write `/plan/<slice-id>-metaplan.md`.

That file must include:
- slice goal
- source spec references
- preserved seams in scope
- acceptance gates in scope
- code paths or subsystems likely involved
- review focus areas
- spec-check focus areas
- explicit risks and shortcuts to avoid

## Non-negotiable rules

1. Re-read the owning spec sections for this slice directly.
2. Keep the slice aligned with the source spec, not only with root planning summaries.
3. Do not create task files here.
4. Do not implement code here.
