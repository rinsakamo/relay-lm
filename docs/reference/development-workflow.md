# RelayLM 1.0 Development Workflow

This document is the current development-workflow authority for the `v1` product line.

The goal is to keep RelayLM's implementation, executable behavior, and human-readable authority synchronized without rebuilding the heavy governance machinery of RelayLM 0.x.

## Core principle

> **Meaning → Example → Test → Code → Docs → Audit**

For semantic changes:

> **Meaning first. Tests freeze the meaning. Code realizes it. Docs preserve the authority.**

Supporting CI or tooling may help enforce this workflow, but the tooling is not the workflow and must not become a second architecture.

## Universal transaction rules

Every transaction begins from fresh repository authority and remains bounded.

- Work on `v1`; do not mutate frozen 0.x `main` as part of RelayLM 1.0 development.
- Re-read the exact current `v1` head before starting.
- Check open `v1` pull requests and competing work before writing.
- One transaction owns one bounded responsibility.
- Do not expand scope merely because adjacent cleanup is convenient.
- Merge only the exact reviewed head.

## 1. Classify the change

Before writing code, classify the transaction as exactly one of:

### Semantic change

A change to externally or internally meaningful behavior, including authority, persistence semantics, State grammar, Context semantics, provider wire contracts, API behavior, lifecycle rules, or other behavior that affects what RelayLM means or guarantees.

Semantic changes use the test-first workflow below.

### Behavior-preserving change

An internal refactor, rename, extraction, relocation, implementation cleanup, or performance change that is intended to preserve the existing semantic contract.

Behavior-preserving changes do not require artificial RED tests. Existing contract/regression tests are the executable baseline.

### Docs-only change

A correction or clarification that changes no runtime behavior and makes documentation agree with current implementation or already-accepted design authority.

Docs-only changes do not require implementation-first or test-first ceremony that cannot add evidence.

## 2. Semantic-change workflow

### Step A — Meaning and bounded examples

Define the responsibility before implementation.

A semantic transaction should state, in the issue or equivalent bounded specification:

- expected behavior;
- non-goals;
- affected authority boundaries;
- one or more concrete examples.

Prefer examples that can be read directly as behavior:

```text
Given:
  tea = likes

When:
  "Recently I prefer coffee to tea."

Then:
  tea remains a positive preference
  coffee becomes a positive preference
  stronger comparative meaning may be retained
  tea is not removed without explicit revocation
```

The example exists before the implementation so the test is derived from intended meaning rather than from code that already exists.

### Step B — Contract test first

Before implementing the new behavior:

```text
existing relevant suite = GREEN
new contract test       = RED
```

The RED result must be caused by the requested behavior being absent, not by a broken fixture, syntax error, unavailable dependency, or unrelated baseline failure.

Important semantic behavior should be expressed with readable contract tests. Add regression tests when preserving a previously broken edge case, and structural tests when the important guarantee is ownership or authority rather than only output text.

Useful test roles are:

```text
Contract test
  what the system should do

Regression test
  what must not break again

Structural test
  which layer is allowed to own or mutate the behavior
```

### Step C — Minimal implementation

Implement the smallest machinery that satisfies the contract.

```text
new contract test = GREEN
relevant suite     = GREEN
```

Do not add semantics merely because they are nearby or potentially useful. If the contract can be satisfied through an existing Event, State, Context, Validator, provider, or persistence mechanism, prefer that over introducing a new subsystem.

> **Implement the minimum machinery required to satisfy the contract.**

### Step D — Authority documentation sync

After behavior is GREEN and therefore concrete, synchronize the affected current-authority documentation in the same transaction.

Rules:

- describe current implemented behavior in the present tense;
- describe unimplemented behavior explicitly as deferred/future;
- never let a current-authority document present deferred behavior as already implemented;
- keep code, tests, and durable documentation converged before merge.

Documentation is part of completing a semantic implementation, not optional follow-up work.

> **Documentation is part of the implementation.**

### Step E — Final semantic audit

Before merge, answer four questions:

1. Does the test actually express the intended meaning/examples?
2. Did the code implement more semantics or machinery than the test/spec requires?
3. Do the current-authority docs describe the current implementation accurately?
4. Is any deferred scope written as though it were already implemented?

If any answer is wrong or ambiguous, the transaction is not complete.

### Step F — Exact-head merge

Re-read the pull-request head and current `v1` authority, verify the bounded diff, and merge only the exact reviewed head.

A completed semantic transaction is therefore:

```text
fresh authority
  → bounded meaning/examples
  → existing GREEN + new RED
  → minimal code GREEN
  → authority docs sync
  → semantic audit
  → exact-head merge
```

## 3. Behavior-preserving workflow

Behavior-preserving changes use the lighter path:

```text
fresh authority
  → existing relevant tests GREEN
  → bounded change
  → same tests GREEN
  → documentation-impact declaration
  → exact-head audit and merge
```

If the change reveals or introduces a semantic difference, stop treating it as behavior-preserving and restart the affected responsibility as a semantic transaction.

Documentation impact may be `none`, but that conclusion must be intentional. A behavior-preserving refactor must not silently move or duplicate semantic authority.

## 4. Docs-only workflow

Docs-only corrections use:

```text
fresh authority
  → inspect current implementation / accepted authority
  → bounded documentation correction
  → semantic contradiction audit
  → exact-head merge
```

Docs-only work must not invent new runtime semantics. If the correction requires behavior to change, it is a semantic transaction instead.

## 5. Test-first boundary

RelayLM uses test-first development for **semantic behavior changes**, not as ceremony for every edit.

Use test-first when meaning changes.

Do not manufacture a failing test for:

- pure internal refactors already covered by contracts;
- documentation-only synchronization;
- mechanically behavior-preserving moves or renames where existing tests are the relevant proof.

The important baseline is:

> **Existing behavior is GREEN; the new requirement alone is RED.**

## 6. Roles of Issue, Test, Code, and Docs

```text
Issue / bounded spec
  intention and examples

Tests
  executable contract and regression evidence

Code
  minimal implementation

Current-authority docs
  human-readable semantic authority
```

These artifacts should point at the same meaning from different roles. A transaction is not semantically complete when one of them materially disagrees with the others.

## 7. Current vs deferred language

This rule is mandatory for current-authority documentation:

> **Current authority never describes deferred behavior in the present tense.**

Use explicit sections such as:

```text
Current implementation
Deferred / future work
Owner: #issue
```

when both current and future behavior need to appear in the same document.

This prevents design intent from being mistaken for implemented authority.

## 8. Supporting automation

Small automation may be added later to make the workflow harder to forget, for example:

- PR documentation-impact declarations;
- a runtime-owner → tests → authority-doc map;
- lightweight current-boundary checks for mechanically derivable constants or schemas.

These are support mechanisms, not required new architecture concepts. Avoid rebuilding the large 0.x documentation-governance system unless evidence shows that the lightweight workflow is insufficient.

## Fixed principles

1. **Meaning → Example → Test → Code → Docs → Audit.**
2. **Semantic behavior changes are test-first.**
3. **Documentation is part of the implementation.**
4. **Current authority never describes deferred behavior in the present tense.**
5. **One transaction = one bounded responsibility.**
6. **Implement the minimum machinery required to satisfy the contract.**
