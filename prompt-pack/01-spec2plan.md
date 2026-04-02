# spec2plan.md

You are operating inside a repository that contains a spec folder. Your job is to ingest the spec set, normalize it into a buildable plan, and write that plan into a new `/plan` folder at the repo root.

Your task is planning only. Do not implement app code. Do not modify the spec files. Do not create runtime, product, or orchestration code. Your output is the `/plan` folder and its contents.

## Mission

Read the spec folder as the active source of truth and produce a durable, implementation-oriented planning package that a coding agent can execute step by step.

The plan must preserve the spec’s boundaries and contracts. It must not invent architecture that conflicts with the spec. If the spec is ambiguous, surface the ambiguity explicitly in the plan instead of silently guessing.

## Non-negotiable rules

1. The spec folder is authoritative.
2. Do not redefine requirements outside the spec.
3. Do not merge runtime, orchestration, and product concerns.
4. Do not introduce stack-specific assumptions unless the spec already requires them.
5. Do not create implementation code.
6. Do not create fake certainty. If something is unclear, record it as an open question or implementation note.
7. Optimize for execution safety, clarity, resumability, and traceability to the spec.
8. The plan must be buildable by another agent without rereading the raw specs every turn.

## What to read first

Find and read the full spec set in the spec folder. Identify:
- the index or governing doc
- runtime contract
- orchestration contract
- product or UX contract
- coherence, review, or invariants doc if present

Then derive a normalized model of:
- system purpose
- product constraints
- design constraints that are normative
- runtime truths
- orchestration truths
- product UX truths
- invariants
- acceptance gates
- forbidden shortcuts or anti-patterns
- open ambiguities

## Required outcome

Create a `/plan` folder at the repo root with a planning package that includes at minimum:

### 1. `/plan/README.md`
A concise overview of:
- what was read
- what the system is
- what the plan folder contains
- how another agent should use it

### 2. `/plan/system-summary.md`
A normalized summary of the system:
- purpose
- major layers
- core concepts
- key invariants
- what must be true for the build to be honest

Keep this tight and structured. This is not a paraphrase dump.

### 3. `/plan/spec-map.md`
A traceable map of the spec set:
- each spec document
- its ownership boundary
- what it normatively defines
- what it explicitly must not define
- key cross-references

This file should make it hard for later agents to mix layers.

### 4. `/plan/domain-glossary.md`
Canonical terms only. For each important term, record:
- name
- meaning
- owning layer
- related persisted or runtime objects if relevant

Use one concept, one name. Call out any naming seams or ambiguities.

### 5. `/plan/invariants.md`
List the system invariants that must hold during implementation.
For each invariant include:
- invariant statement
- why it matters
- what parts of the system it touches
- what kind of implementation shortcut would violate it

### 6. `/plan/acceptance-matrix.md`
Turn the acceptance gates from the spec into a planning matrix.
For each gate include:
- gate id
- owning layer
- what behavior must exist
- likely implementation area(s)
- likely test shape
- prerequisite dependencies

Do not invent test results. This is a planning artifact.

### 7. `/plan/build-order.md`
A dependency-aware implementation sequence.
This must answer:
- what foundation objects and modules should exist first
- what should be built before UI
- what should be built before orchestration
- what should be verified before expansion

The order should prefer:
- canonical types
- persisted truth
- execution core
- blocking/approval semantics
- orchestration semantics
- product projection
- walkthrough-level testing

### 8. `/plan/task-graph.md`
A concrete work decomposition for building the system.
Tasks must be:
- scoped
- dependency-aware
- small enough to execute incrementally
- traceable back to the spec

For each task include:
- task id
- title
- objective
- owning layer
- prerequisites
- files or modules likely involved
- acceptance gates advanced
- expected artifacts/evidence
- honest completion criteria

Do not produce vague tasks like “build runtime.” Break them into concrete units.

### 9. `/plan/open-questions.md`
Capture only real ambiguities that matter for implementation.
For each one include:
- question
- why it matters
- likely safe default if forced to proceed
- what spec file or section caused the ambiguity

Do not inflate this with trivialities.

### 10. `/plan/forbidden-shortcuts.md`
List implementation shortcuts that would violate the spec.
Examples of the kind of thing to catch:
- reconstructing execution truth from transcript
- inventing UI state not backed by persisted truth
- collapsing action identity into model identity
- treating delegation as runtime action execution if the spec forbids it
- bypassing approval digest enforcement
- ignoring write-scope conflict semantics

This should be one of the most useful files in the folder.

### 11. `/plan/walkthroughs.md`
Extract the canonical end-to-end scenarios from the spec, or derive them from the acceptance model if needed.
For each walkthrough include:
- scenario name
- why it matters
- layers involved
- minimum implementation prerequisites
- what successful execution would prove

These are planning targets, not test output.

### 12. `/plan/implementation-brief.json`
Produce a machine-usable JSON brief that captures the normalized planning truth. Include at minimum:
- system_name
- source_specs
- layers
- canonical_terms
- invariants
- acceptance_gates
- build_order
- task_index
- open_questions
- forbidden_shortcuts

Make this stable and structured so another agent can load it without reparsing markdown.

## Planning standards

When producing the plan:
- compress repeated ideas
- do not restate the entire spec
- preserve normative meaning
- do not invent hidden requirements
- separate “must build” from “later extension”
- prefer deterministic, dependency-aware sequencing
- surface release burden when relevant
- keep the planning artifacts useful for execution, not just documentation

## Implementation-shaping guidance

Your plan should naturally enforce these principles when they are present in the spec:
- persisted truth before projection
- execution identity before UX explanation
- approval enforcement before approval polish
- task-state and write-scope truth before scheduler sophistication
- orchestration truth before delegation UX
- product-visible state must derive from persisted execution truth
- no hidden mutation
- no resumability via inference
- no layer leakage

## Required final behavior

At the end:
1. create the full `/plan` folder
2. write all required files
3. ensure internal consistency across the plan artifacts
4. include a short final summary in `/plan/README.md` of what is ready, what is ambiguous, and how a follow-on coding agent should start

## Quality bar

The `/plan` folder should be good enough that a second agent could begin implementation from it with minimal rereading of the raw spec documents.

Do not be verbose for its own sake. Be precise, structured, and execution-oriented.
