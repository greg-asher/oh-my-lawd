# Oh My Lawd Scope and Simplicity Guide

Status: Active
Layer: Non-normative scope guide

## 1. Purpose
This document is a plain-language guide to keep the spec set lean and clear.

It does not define runtime, orchestration, or product behavior.
Normative requirements belong only in their owning spec documents.

## 2. Focus
When deciding whether something belongs in the active spec set, prefer work that directly improves:
1. product clarity
2. user experience
3. execution safety
4. recovery and resumability

If a requirement does not materially help one of these, it is usually optional or out of scope.

## 3. Keep It Lean
1. Use plain names and plain language.
2. Avoid adding process-heavy requirements to core behavior.
3. Avoid adding concepts that only serve one edge case.
4. Prefer extending existing models over adding new control paths.
5. Keep operator-facing behavior concrete and actionable.

## 4. Manual Walkthrough Policy
Walkthroughs are a manual team practice.

They are not a built-in system requirement, runtime contract, or required structured artifact unless an owning spec explicitly adds that requirement later.

## 5. Practical Check
Before adding a new requirement, ask:
1. Does this make the product or UX clearer for real users?
2. Does this reduce real operational risk?
3. Is this necessary now, or can it stay out of scope?

If the answer is unclear, keep the requirement out of the core spec.
