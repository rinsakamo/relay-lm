# RelayLM 1.0 Development Workflow

This is the current development-workflow authority for `v1`.

> **Meaning → Example → Test → Code → Docs → Audit**

For semantic changes:

> **Meaning first. Tests freeze the meaning. Code realizes it. Docs preserve the authority.**

The workflow is intentionally lightweight. CI or tooling may enforce parts of it later, but tooling must not become a second architecture or recreate the heavy 0.x governance system.

## Universal rules

Every transaction:

- starts from fresh `v1` authority;
- checks open `v1` PRs / competing work;
- owns one bounded responsibility;
- avoids adjacent scope expansion;
- leaves frozen 0.x `main` untouched;
- merges only the exact reviewed head.

## 1. Classify the change

Choose one path before writing.

### Semantic change

Behavior or meaning changes: authority, persistence, State grammar, Context semantics, provider wire, API behavior, lifecycle, or another RelayLM guarantee.

Use the test-first workflow below.

### Behavior-preserving change

Refactor, rename, extraction, relocation, cleanup, or performance work intended to preserve existing semantics.

Do not manufacture a RED test. Existing contract/regression tests are the baseline.

### Docs-only change

Documentation correction or clarification with no runtime behavior change.

Do not add test-first ceremony that provides no evidence.

## 2. Semantic change

### A. Meaning + examples

Before implementation, the issue or bounded spec states:

- expected behavior;
- non-goals;
- affected authority boundaries;
- concrete Given / When / Then examples.

Example:

```text
Given: tea = likes
When:  "Recently I prefer coffee to tea."
Then:
  tea remains positive
  coffee becomes positive
  comparative strength may be retained
  tea is not removed without explicit revocation
```

### B. Contract test first

Before implementing:

```text
existing relevant suite = GREEN
new contract test       = RED
```

RED must mean "the requested behavior is not implemented", not a broken fixture, syntax error, missing dependency, or unrelated failure.

Use readable tests according to the guarantee:

```text
contract    expected behavior
regression  a previously broken edge case
structural  ownership / authority boundary
```

### C. Minimal implementation

Implement only what the contract requires:

```text
new contract test = GREEN
relevant suite     = GREEN
```

Prefer existing Event / State / Context / Validator / provider / persistence machinery over creating a new subsystem.

> **Implement the minimum machinery required to satisfy the contract.**

### D. Authority docs sync

After behavior is GREEN, update affected current-authority docs in the same transaction.

- Current implemented behavior is written in the present tense.
- Unimplemented behavior is explicitly deferred/future.
- Deferred behavior must never appear as current implementation.
- Code, tests, and docs converge before merge.

> **Documentation is part of the implementation.**

### E. Semantic audit

Before merge, answer four questions:

1. Does the test express the intended meaning/examples?
2. Did the code add more semantics or machinery than required?
3. Do current-authority docs match the implementation?
4. Is any deferred behavior written as already implemented?

Any wrong or ambiguous answer means the transaction is incomplete.

### F. Exact-head merge

Re-read the PR head and current `v1`, verify the bounded diff, and merge only the exact reviewed head.

```text
fresh authority
  → meaning/examples
  → existing GREEN + new RED
  → minimal code GREEN
  → authority docs
  → semantic audit
  → exact-head merge
```

## 3. Behavior-preserving change

```text
fresh authority
  → existing relevant tests GREEN
  → bounded change
  → same tests GREEN
  → documentation impact: updated or explicitly none
  → exact-head audit / merge
```

If semantics changed, reclassify the work as a semantic transaction.

## 4. Docs-only change

```text
fresh authority
  → inspect current implementation / accepted authority
  → bounded docs correction
  → semantic contradiction audit
  → exact-head merge
```

Docs-only work must not invent new runtime semantics.

## 5. Artifact roles

```text
Issue / bounded spec   intention + examples
Tests                  executable contract / regression evidence
Code                   minimal implementation
Authority docs         human-readable current semantics
```

A semantic transaction is not complete while these materially disagree.

## 6. Current vs deferred

Mandatory rule:

> **Current authority never describes deferred behavior in the present tense.**

When both are needed, separate them explicitly:

```text
Current implementation
Deferred / future work
Owner: #issue
```

## 7. Supporting automation

Small supporting automation may be added when useful, such as:

- PR documentation-impact declarations;
- runtime-owner → tests → authority-doc mapping;
- lightweight checks for mechanically derivable constants or schemas.

These support the workflow; they are not new architecture concepts.

## Fixed principles

1. **Meaning → Example → Test → Code → Docs → Audit.**
2. **Semantic behavior changes are test-first.**
3. **Documentation is part of the implementation.**
4. **Current authority never describes deferred behavior in the present tense.**
5. **One transaction = one bounded responsibility.**
6. **Implement the minimum machinery required to satisfy the contract.**
