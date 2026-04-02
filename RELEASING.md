# Releasing

## Purpose
This repository is a public specification project. Releases should reflect spec truth and governance discipline, not just file churn.

## Release Cadence
Target cadence:
- weekly releases, once the monitoring workflow is active

Before weekly automation exists, releases may be cut manually.

## What Qualifies For A Release
Typical release-worthy changes:
- normative changes to the spec set
- prompt-pack changes needed to preserve alignment with the spec
- governance changes that materially affect contribution or review flow
- meaningful README or release-process updates that change how the repo should be used

## Suggested Versioning
Use lightweight tag-based releases until a more formal versioning scheme is needed.

Suggested format:
- `v0.1.0`
- `v0.2.0`
- `v0.2.1`

Use:
- minor bumps for meaningful spec or workflow additions
- patch bumps for clarifications, prompt-pack fixes, or governance-only corrections

## Release Checklist
1. confirm the working tree is clean
2. confirm `README.md`, `spec/`, and `prompt-pack/` are aligned
3. confirm no prompt-pack file contradicts the current spec set
4. confirm governance docs still reflect actual repo practice
5. summarize notable changes since the last release
6. create a tag and GitHub release

## Release Notes Guidance
Release notes should call out:
- spec changes
- prompt-pack changes
- governance changes
- any known ambiguities or deferred items that still matter

## Non-Goals
This release process does not imply application binaries, packaged builds, or runtime artifacts. The primary deliverable is the public specification and its supporting workflow materials.
