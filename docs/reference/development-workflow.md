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

## Parallel implementation rule

Parallel implementation is allowed across disjoint canonical owners. This relaxes a repository-wide single-writer assumption; it does not relax authority ownership.

> **Single writer per concept, not single writer for the entire repository. Parallel implementation; serial integration.**

Rules:

- one canonical owner or semantic concept has at most one active writer;
- each parallel transaction starts from fresh `v1`, declares its bounded responsibility, and inspects open competing work before writing;
- transactions that share a canonical owner, semantic contract, or unavoidable write surface are serialized instead of being treated as independent;
- when practical, shared aggregate surfaces such as evaluation registries, authority maps, scenario counts, and Issue current-status summaries are reconciled in a short serial integration transaction after the owning component transactions merge rather than becoming parallel-writer hotspots;
- merge and authority reconciliation remain serial: before each merge, re-read current `v1`, the transaction head, and relevant competing work, then perform the normal fresh-head review and exact-head required CI gate;
- when an earlier merge moves `v1`, every still-open parallel transaction reconstructs authority and classifies overlap before merge; semantic or ownership overlap returns the work to a fresh bounded transaction instead of carrying stale assumptions forward;
- parallelism never bypasses test-first semantics, exact-head CI, expected-head protected squash merge, documentation convergence, or Issue reconciliation.

This means independent runtime owners, provider/storage boundaries, isolated evaluation work, or non-overlapping documentation can be developed concurrently. Two transactions must not concurrently redefine the same Context, State, Validator, retrieval, persistence, provider, or other canonical semantic owner.

## Semantic lane execution rule

A body of work that contains multiple disjoint semantic segments may be organized into **semantic lanes**.

A semantic lane is a temporary execution boundary for an ordered sequence of related bounded transactions. It is defined by semantic ownership, not by file, package, Issue, PR, or implementation convenience.

> **One lane = one coherent semantic ownership boundary. Parallel across disjoint lanes; serial within each lane; serial at shared integration surfaces.**

Before a lane starts, declare:

```text
lane:
semantic owner:
canonical surfaces:
non-goals:
cross-lane dependencies:
shared integration surfaces:
ordered transactions:
```

### Lane ownership

The semantic owner is authoritative. File paths are supporting write surfaces only.

Multiple files that implement one semantic rule belong to the same lane when separating them would create competing or divergent semantic authorities. File-level disjointness is not sufficient evidence of semantic independence.

For example, if MEMORY retrieval and Event retrieval must share one lexical relevance contract, their corresponding implementations belong to the same retrieval lane even when they live in different modules.

Conversely, two responsibilities must not be placed in the same lane merely because they happen to touch the same subsystem or Issue.

The existing single-writer rule therefore applies at lane level:

> **One semantic concept has at most one active writer.**

No two active lanes may independently redefine:

- the same canonical semantic owner;
- the same semantic contract;
- derived implementations whose correctness requires one shared rule;
- an unavoidable shared write surface whose concurrent modification would create ambiguous authority.

If ownership cannot be cleanly separated, serialize the work.

### Serial execution inside a lane

Transactions inside one lane execute in declared dependency order:

```text
L1
  → merge
  → fresh authority reconstruction
  → L2
  → merge
  → fresh authority reconstruction
  → L3
```

Completion of one transaction does not by itself require the lane to stop.

After every successful merge, the lane:

1. re-fetches current `v1`;
2. re-checks open PRs and competing semantic writers;
3. reconstructs its authority against the new head;
4. verifies that the next transaction is still owned by the lane;
5. continues with the next bounded transaction.

Each transaction remains independently subject to the full development workflow. A lane never weakens **one transaction = one bounded responsibility**.

### Parallel execution across lanes

Different lanes may execute concurrently only when their semantic ownership is disjoint.

Typical valid separation may include retrieval semantics, Context Compiler semantics, turn/runtime orchestration, isolated evaluation components, or provider/storage boundaries, provided the concrete responsibilities do not share a semantic contract or canonical owner.

A lane must not consume an unmerged assumption from another lane as though it were current authority.

### Cross-lane dependencies

Cross-lane dependencies must be explicit. A dependent transaction may consume another lane's capability only after the required authority exists on current `v1`.

For example:

```text
R3 retrieval diagnostics
  ├─> T2 aggregate runtime diagnostics
  └─> E1 retrieval diagnostics evaluation
```

If the dependency is not yet merged, the dependent transaction waits at that boundary while unrelated lanes may continue.

An unmet dependency never justifies:

- a temporary bridge;
- a compatibility layer;
- speculative duplicate implementation;
- fallback semantics;
- a temporary alternate owner;
- code intended to be replaced immediately after another lane merges.

### Shared integration surfaces

Shared aggregate surfaces are not owned by component lanes unless they are themselves the bounded semantic owner.

Examples include:

- evaluation registries;
- aggregate scenario counts;
- authority maps;
- repository-wide status tables;
- shared navigation indexes;
- aggregate Issue status;
- other cross-component registration surfaces.

Component lanes stop at:

```text
component implemented
component tested
component documented
component merged
integration pending
```

Shared integration is then performed in a short serial integration transaction after the required component authorities exist on current `v1`:

```text
Lane A ─┐
Lane B ─┼─> serial integration
Lane C ─┤
Lane D ─┘
```

There is one writer for a shared integration surface at a time. Serial integration registers or aggregates merged component authority; it must not redefine component semantics.

### Moving `v1`

Every lane is based on live repository authority, not on its initial bootstrap SHA.

When another lane moves `v1`, an active lane must reconstruct authority before its next merge and classify the result:

```text
no relevant overlap
  → continue normal verification

compatible dependency now available
  → consume only after it exists on current v1

semantic or ownership overlap
  → stop the stale transaction
  → reconstruct a fresh bounded transaction

canonical owner conflict
  → stop lane execution until ownership is resolved
```

Do not silently rebase, merge, rewrite history, or carry stale semantic assumptions forward.

### Lane stop conditions

A lane continues through its declared ordered transactions unless one of these conditions occurs:

- canonical-owner conflict;
- semantic ownership ambiguity;
- newly discovered cross-lane overlap;
- required dependency not yet merged;
- architecture or authority ambiguity;
- required permission is unavailable;
- irreversible scope expansion would be required;
- fresh-head semantic review fails;
- exact-head required CI fails or is unavailable;
- the next declared transaction is no longer necessary against current `v1`.

Routine successful transaction completion is not a stop condition.

### Lane and work-package completion

A lane is complete when all currently valid lane-owned transactions are merged, their owning Issues are reconciled, no lane-owned semantic work remains, and any remaining shared integration work is explicitly identified.

Lane completion does not imply shared integration completion.

A multi-lane work package is complete only after:

```text
all required component lanes complete
  → shared serial integration complete
  → aggregate authority/docs converge
  → remaining Issues represent only real unresolved work
```

### Prohibited decomposition

Do not use lanes to create artificial concurrency.

Invalid decomposition includes separating files that encode one semantic contract, for example:

```text
Lane A = memory_retrieval.py
Lane B = event_retrieval.py
```

when both implement one retrieval relevance rule.

Likewise, do not split one semantic change into separate implementation, test, and documentation lanes. Tests, code, and authority documentation remain part of the same bounded transaction.

Semantic lanes are an execution optimization, not a new authority layer. Issues remain planning and remaining-work ledgers; tests remain executable contracts; code remains implementation; authority documents remain current semantic authority; `v1` remains repository authority.

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

All required `v1` CI results must belong to the exact PR head that was just reviewed.

Current required baseline:

```text
workflow: .github/workflows/v1-ci.yml
python:   3.12

required checks:
  v1 CI / pytest
    python -m pytest -q

  v1 CI / minimum-supported
    install declared direct dependency floors
    python -m pip check
    python -m pytest -q

  v1 CI / package-smoke
    build RelayLM wheel
    install into a clean virtual environment
    python -m pip check
    verify package import, version, and console entry points

  v1 CI / lint
    ruff check .
```

Each job explicitly checks out and verifies the PR head SHA before running its verification.

Rules:

- all required exact-head CI checks must be GREEN before merge;
- a GREEN result from an older PR head is stale and does not count;
- local/manual test output is useful evidence but does not replace the required CI results;
- if any required CI check is unavailable, cancelled, or not attached to the exact reviewed head, do not claim `CI GREEN` and do not merge;
- after any new push, repeat fresh-head review and wait for the new exact-head required CI results.

### G. Exact-head merge

Immediately before merge:

1. re-read current `v1`;
2. re-read the PR head;
3. confirm the head is the reviewed SHA;
4. confirm all required exact-head CI checks are GREEN;
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
  → exact-head required CI GREEN
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
  → exact-head required CI GREEN
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
  → exact-head required CI GREEN
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

The current mandatory baseline is the four exact-head `v1 CI` checks: `pytest`, `minimum-supported`, `package-smoke`, and `lint`.

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
11. **Parallel implementation is allowed only across disjoint canonical owners; integration and authority reconciliation remain serial.**
12. **Semantic lanes follow ownership boundaries: lane-internal transactions are serial, disjoint lanes may run in parallel, and shared integration remains serial.**
