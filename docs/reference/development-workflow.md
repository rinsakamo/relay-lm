# RelayLM 1.0 Development Workflow

This is the current development-workflow authority for `v1`.

> **Meaning → Example → Test → Code → Docs → Audit**

For semantic changes:

> **Meaning first. Tests freeze the meaning. Code realizes it. Docs preserve the authority.**

The workflow is intentionally lightweight. It preserves the quality properties worth carrying forward from 0.x without recreating the old governance system:

- fresh authority;
- one bounded responsibility;
- direct canonical convergence;
- fresh-head verification;
- exact-head CI;
- code / test / docs authority convergence.

## Universal rules

Every transaction:

- starts from fresh `v1` authority;
- checks open `v1` PRs / competing work;
- owns one bounded responsibility;
- avoids adjacent scope expansion;
- converges directly on the current canonical owner instead of preserving superseded semantics through compatibility machinery;
- leaves frozen 0.x `main` untouched;
- performs a fresh verification pass over the exact current PR head before merge;
- requires the exact current PR head to pass the required `v1` CI checks;
- merges only the exact reviewed and tested head;
- reconciles its owning Issue after a successful merge when an Issue exists.

If `v1` moves during a transaction, reconstruct authority and classify overlap before merge. Do not silently rebase, merge, or assume the previous review/CI result is still sufficient.

## Canonical convergence rule

`v1` is a greenfield product line. Internal compatibility machinery for superseded RelayLM semantics is prohibited by default.

Do not introduce or retain:

- compatibility patches or shims;
- old-path aliases or forwarding modules;
- temporary bridges intended to be removed later;
- monkey patches that preserve an obsolete contract;
- dual-read or dual-write migration paths;
- simultaneous old/new semantic authorities;
- fallbacks to deprecated RelayLM behavior;
- wrappers whose purpose is to keep a superseded owner alive.

Instead:

```text
change the canonical owner / contract
  → migrate all affected internal consumers in the same bounded transaction
  → remove the superseded path
```

> **One concept = one current owner.**

Intentional permanent adapters remain allowed at genuine architecture boundaries, such as an external protocol/provider/storage boundary, when they translate between the current RelayLM contract and an external contract. Current package exports, facades, and registries are also allowed when they are the canonical public boundary rather than a preservation path for obsolete internal semantics.

If post-release compatibility with an external/public RelayLM contract is ever required, it must be designed explicitly as a versioned compatibility contract. It must not enter the repository as an unnamed temporary bridge.

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

Before implementation, the Issue or bounded spec states:

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

Do not solve a transition by adding a compatibility shim or a second authority path. Change the canonical owner directly and migrate affected internal consumers together.

> **Implement the minimum machinery required to satisfy the contract.**

### D. Authority docs sync

After behavior is GREEN, update affected current-authority docs in the same transaction.

- Current implemented behavior is written in the present tense.
- Unimplemented behavior is explicitly deferred/future.
- Deferred behavior must never appear as current implementation.
- Code, tests, and docs converge before merge.

> **Documentation is part of the implementation.**

### E. Fresh-head semantic review

After implementation and documentation are complete, re-fetch the exact current PR head from GitHub and review the cumulative diff as a fresh verification pass.

This review is independent verification, not necessarily a second human reviewer. It must inspect the actual head/diff/tests/docs rather than trust the implementation summary or earlier local state.

Answer five questions:

1. Does the test express the intended meaning/examples?
2. Did the code add more semantics or machinery than required?
3. Are failure cases, edge cases, or authority-boundary regressions materially under-tested?
4. Do current-authority docs match the implementation and keep deferred behavior explicitly deferred?
5. Does the diff introduce or preserve a compatibility bridge, shim, dual-authority path, old-path forwarder, or deprecated-behavior fallback instead of direct canonical convergence?

Also verify that the cumulative changed-path set still matches the bounded responsibility.

Any wrong or ambiguous answer means the transaction is incomplete.

### F. Exact-head CI gate

The required `v1` CI result must belong to the exact PR head that was just reviewed.

Current baseline:

```text
workflow: .github/workflows/v1-ci.yml
check:    v1 CI / pytest
python:   3.12
command:  python -m pytest -q
```

The workflow explicitly checks out and verifies the PR head SHA before running the full test suite.

Rules:

- the required exact-head CI check must be GREEN before merge;
- a GREEN result from an older PR head is stale and does not count;
- local/manual test output is useful evidence but does not replace the required CI result;
- if CI is unavailable, cancelled, or not attached to the exact reviewed head, do not claim `CI GREEN` and do not merge;
- after any new push, repeat fresh-head review and wait for the new exact-head CI result.

### G. Exact-head merge

Immediately before merge:

1. re-read current `v1`;
2. re-read the PR head;
3. confirm the head is the reviewed SHA;
4. confirm required exact-head CI is GREEN;
5. confirm the bounded diff is unchanged;
6. merge only with expected-head protection.

### H. Issue reconciliation

After the merge succeeds, reconcile the owning Issue against the merged reality. Use exactly one of these outcomes:

```text
implemented completely
  -> close completed

implemented partially
  -> narrow the Issue to true remaining work
     OR move remaining work to a successor Issue and close the original

accepted design promoted to canonical docs
  -> link the canonical authority / successor work and close or supersede the design Issue

not adopted
  -> close not planned

real work remains
  -> keep open, but update Current / Remaining scope so the Issue does not describe stale authority
```

Issue closure happens after merge so the Issue never claims completion before the repository does. Record the merged PR and resulting authority where useful.

A completed semantic transaction is therefore:

```text
fresh authority
  → meaning/examples
  → existing GREEN + new RED
  → minimal code GREEN
  → authority docs
  → fresh-head semantic review
  → exact-head CI GREEN
  → exact-head merge
  → Issue reconciliation
```

## 3. Behavior-preserving change

```text
fresh authority
  → existing relevant tests GREEN
  → bounded change
  → same tests GREEN
  → documentation impact: updated or explicitly none
  → fresh-head cumulative-diff review
  → exact-head CI GREEN
  → exact-head merge
  → Issue reconciliation when an owning Issue exists
```

A behavior-preserving refactor must still converge consumers directly on the canonical owner; it must not leave an old-path compatibility alias or forwarder behind.

If semantics changed, reclassify the work as a semantic transaction.

## 4. Docs-only change

```text
fresh authority
  → inspect current implementation / accepted authority
  → bounded docs correction
  → fresh-head semantic-contradiction review
  → exact-head CI GREEN
  → exact-head merge
  → Issue reconciliation when an owning Issue exists
```

Docs-only work must not invent new runtime semantics.

## 5. Quality model

The workflow protects three distinct layers:

```text
Semantic quality
  Meaning → Example → contract RED/GREEN

Implementation quality
  regression / structural coverage + relevant suite

Repository quality
  fresh authority + direct canonical convergence + fresh-head review + exact-head CI + docs convergence
```

The goal is not to reproduce heavy governance. The goal is to make the wrong semantic change, stale-head merge, compatibility accretion, or documentation drift difficult to ship.

## 6. Artifact roles

```text
Issue / bounded spec   intention + examples + remaining-work ledger
Tests                  executable contract / regression evidence
Code                   minimal implementation
Authority docs         human-readable current semantics
CI                     exact-head executable verification
```

A semantic transaction is not complete while these materially disagree. Issues are planning and traceability artifacts, not current semantic authority; completed or superseded Issues must not remain open in a way that implies stale design is still pending.

## 7. Current vs deferred

Mandatory rule:

> **Current authority never describes deferred behavior in the present tense.**

When both are needed, separate them explicitly:

```text
Current implementation
Deferred / future work
Owner: #issue
```

## 8. Issue reconciliation rule

Issue hygiene is part of transaction completion, not a separate governance project.

> **A completed transaction reconciles its Issue: close it, narrow it to true remaining work, or explicitly supersede it.**

Do not keep an Issue open merely as historical documentation. Git history, merged PRs, and canonical docs preserve history; open Issues should represent real unresolved work.

## 9. Supporting automation

The current mandatory baseline is the exact-head `v1 CI / pytest` workflow.

Additional small automation may be added when useful, such as:

- PR documentation-impact declarations;
- runtime-owner → tests → authority-doc mapping;
- lightweight checks for mechanically derivable constants or schemas;
- structural checks that detect prohibited compatibility paths when they can be identified without false positives;
- post-merge reminders for owning-Issue reconciliation.

These support the workflow; they are not new architecture concepts.

## Fixed principles

1. **Meaning → Example → Test → Code → Docs → Audit.**
2. **Semantic behavior changes are test-first.**
3. **Documentation is part of the implementation.**
4. **Current authority never describes deferred behavior in the present tense.**
5. **One transaction = one bounded responsibility.**
6. **Implement the minimum machinery required to satisfy the contract.**
7. **No bridges, no shims, no dual authority: converge directly on the canonical owner.**
8. **Fresh-head review verifies the repository, not the implementation narrative.**
9. **Only the exact reviewed head may satisfy the required CI gate.**
10. **A completed transaction reconciles its owning Issue.**
