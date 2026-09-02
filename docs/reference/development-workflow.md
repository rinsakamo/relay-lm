# RelayLM 1.0 Development Workflow

This is the current development-workflow authority for `v1`.

> **Meaning → Example → Test → Code → Docs/Authority → Audit**

For semantic changes:

> **Meaning first. Tests freeze the meaning. Code realizes it. Owner-local authority preserves it.**

The workflow is intentionally small. It protects fresh repository authority, bounded semantic ownership, direct canonical convergence, exact-head verification, and honest completion claims without turning implementation history into permanent ceremony.

## 1. Universal transaction rules

Every repository transaction:

1. re-fetches current `v1` and open PRs targeting `v1`;
2. resolves the semantic owner and reads its current canonical authority;
3. owns one bounded responsibility and names material non-goals;
4. uses the verification discipline appropriate to the change class;
5. converges code, tests, and owner-local authority directly on the current contract;
6. re-fetches and reviews the exact final PR head;
7. requires the required `v1` CI results for that exact reviewed head;
8. re-checks current `v1`, competing work, and the unchanged PR head immediately before merge;
9. merges only the exact reviewed/tested head with expected-head protection;
10. before declaring completion, reconciles material physical/external execution learning when applicable and reconciles the owning Issue after merge, or after terminal completion of a no-repository-mutation transaction, when an Issue exists.

A bounded physical/external execution-only transaction that performs no repository mutation still consumes fresh repository/owner authority and the owning execution/evidence contract, but it does not create a no-op PR merely to satisfy repository mutation gates. Fresh-head review, exact-head CI, and merge requirements apply when there is a repository mutation/PR; execution-only completion uses the applicable owner-specific physical/evidence gates plus section 10 reconciliation.

Handoffs, old comments, previously recorded SHAs, earlier CI results, Issues, and projections are historical evidence. They do not replace fresh repository facts.

If `v1` moves during a transaction, reconstruct relevant authority before continuing. Do not silently carry assumptions, reviews, or CI evidence across a moved base.

Frozen 0.x `main` is outside the `v1` workflow and must not be modified by `v1` transactions.

## 2. Classify the change before writing

### Semantic change

Use this class when behavior or meaning changes: authority, State, Context, Continuity, persistence, provider wire, public API, lifecycle, validation, or another RelayLM guarantee.

Before implementation, establish:

- the intended meaning;
- concrete examples or Given / When / Then cases;
- affected authority boundaries;
- explicit non-goals.

Then establish a meaningful RED contract or regression test.

```text
existing relevant suite = GREEN
new contract test       = RED
```

RED must mean that the requested behavior is missing. A syntax error, broken fixture, unavailable dependency, or unrelated failure is not semantic evidence.

Implement only enough machinery to make the intended contract GREEN while keeping the relevant suite GREEN.

### Behavior-preserving change

Use this class for refactors, extractions, renames, relocation, simplification, and performance work intended to preserve current semantics.

Do **not** manufacture a RED test.

Use existing regressions or a bounded characterization surface to establish the before/after contract. For risky simplification, overlap old and new representations until equivalence is demonstrated before deleting the old one.

If the work reveals an intentional semantic change, reclassify it as a semantic transaction.

### Docs-only change

Use this class for correcting or simplifying documentation without changing runtime behavior.

Do not add fake test-first ceremony. Ground the edit in current implementation and authority, then rely on repository structural tests plus exact-head CI.

Docs-only work must not introduce new product semantics or hand-edit generated persistent projections.

## 3. One concept, one current owner

Semantic ownership is the primary decomposition rule.

> **One semantic concept has one current canonical writer.**

File boundaries, Issue boundaries, PR boundaries, and implementation convenience do not create independent semantic owners.

Before writing:

- locate the responsible `.ai/authority/<id>.yaml` declaration;
- read its canonical surfaces;
- load only dependencies or evidence that can materially change the decision;
- check whether another open transaction is writing the same semantic owner or unavoidable shared semantic boundary.

If ownership is ambiguous, resolve that ambiguity before semantic mutation. Do not invent a temporary owner, bridge, fallback, or duplicate implementation.

## 4. Direct canonical convergence

`v1` is a greenfield product line. Internal compatibility machinery for superseded RelayLM semantics is prohibited by default.

Do not retain:

- old-path aliases or forwarding modules whose only purpose is compatibility;
- temporary bridges intended for later removal;
- dual-read or dual-write paths for superseded internal semantics;
- fallbacks to deprecated RelayLM behavior;
- monkey patches or shims preserving an obsolete owner;
- simultaneous old/new semantic authorities.

Instead:

```text
change the canonical owner / contract
  → migrate affected internal consumers
  → remove the superseded path
```

Permanent adapters remain valid at genuine external protocol, provider, storage, package, or public-contract boundaries when they translate the current RelayLM contract rather than preserve obsolete internal semantics.

## 5. Owner-local authority convergence

Authority is part of the implementation.

After behavior is correct:

- update the affected current-authority documents owned by the same semantic owner;
- update `.ai/authority/<id>.yaml` when its current surfaces, dependencies, or evidence change;
- describe implemented behavior in the present tense;
- mark deferred behavior explicitly as deferred/future;
- do not change another owner's authority merely to restate a local fact.

Repository-wide maps, reverse dependencies, navigation views, and status tables are derived projections, not routine transaction write surfaces.

```text
component implementation
  → owner-local authority
  → validation
  → merge

derived developer view
  → reconstruct from projection recipe when needed

human-facing aggregate documentation
  → materialize at the owned version/release boundary
```

> **Own facts locally. Do not hand-maintain aggregates.**

## 6. Parallel work

Parallel implementation is allowed only when semantic ownership is genuinely disjoint.

> **Single writer per concept, not single writer for the repository.**

Two transactions may proceed concurrently when they do not redefine the same semantic owner, shared contract, or unavoidable integration decision.

When another transaction moves `v1`:

```text
no relevant overlap
  → reconstruct authority and continue

new compatible dependency is now merged
  → consume it only from current v1

semantic / ownership overlap
  → stop the stale mutation and reconstruct a bounded transaction
```

A cross-owner integration transaction is justified only when a real shared semantic decision remains after component work merges. Merely registering already-known facts in a derived view is not integration work.

No special `lane`, `work package`, or serial-integration lifecycle is required to express these rules. Temporary plans may organize work, but they are working state rather than an additional authority layer.

## 7. Fresh-head review

After the cumulative implementation, tests, and authority edits are complete, re-fetch the exact current PR head and review that actual diff.

Do not review from an earlier checkout, implementation summary, or remembered patch.

Fresh-head review challenges the transaction's **completion claim**, not only the changed lines. When a claimed invariant can be realized through materially equivalent supported paths, inspect those sibling paths far enough to search for material counterexamples. Discovery scope may exceed the transaction's mutation scope; discovering a sibling violation does not authorize unrelated or cross-owner mutation.

Ask:

1. Does the change express the intended contract or preservation goal?
2. Did it add more semantics or machinery than required? Before completion, can necessary additions be integrated into existing principles, deduplicated, or expressed more generally without weakening the intended behavior or authority boundaries?
3. Does the claimed invariant hold across materially equivalent supported realization paths, and are material counterexamples, failure modes, or authority boundaries under-tested?
4. Do current-authority docs match the code and distinguish current from deferred behavior?
5. Does the diff preserve an obsolete bridge, wrapper, dual authority, or implementation-history artifact instead of converging directly?
6. Does the cumulative changed-path set still fit the bounded responsibility?

Any material mismatch means the transaction is incomplete. A material sibling finding outside the current mutation boundary is routed to its current owner rather than ignored or absorbed opportunistically. The current transaction must narrow an over-broad completion claim when the finding is not actually part of its responsibility; if the finding remains a counterexample to the claim being made, completion waits for the responsible boundary to be resolved.

High-risk changes may additionally use an isolated adversarial review under `docs/reference/ai-development.md`; that does not replace this fresh-head review.

## 8. Exact-head CI

All required merge CI must belong to the exact PR head just reviewed.

The source-controlled merge baseline is implemented by `.github/workflows/v1-ci.yml`. The meaning of each green job is owned by `docs/reference/ci-verification.md`; do not duplicate or reinterpret those guarantees here.

Current required jobs are:

- `v1 CI / pytest`;
- `v1 CI / minimum-supported`;
- `v1 CI / package-smoke`;
- `v1 CI / lint`.

Rules:

- all required jobs must be GREEN for the exact reviewed head;
- an older-head result is stale;
- local/manual output is useful evidence but does not replace required CI;
- cancelled, unavailable, or detached checks are not GREEN evidence;
- any new push invalidates the previous fresh-head review and exact-head CI claim.

`v1 release identity` and release-candidate verification have separate guarantees owned by release engineering and `docs/reference/ci-verification.md` / release contracts. Their existence does not change the normal four-job source merge baseline unless current authority explicitly says so.

## 9. Merge gate

Immediately before merge:

1. re-fetch current `v1`;
2. re-fetch open competing PRs relevant to the owner;
3. re-fetch the PR head;
4. confirm the head is exactly the reviewed SHA;
5. confirm its required exact-head CI is GREEN;
6. confirm the bounded cumulative diff is unchanged;
7. merge with expected-head protection.

If the base moved, classify overlap before merge. A moved base is not automatically a reason to rebase, and it is never permission to reuse stale semantic assumptions.

## 10. Completion reconciliation

### Physical / external execution learning

This rule is conditional and orthogonal to change classification. It applies when a transaction performs material execution that depends on host, GPU/runtime, external service/tooling, or manual operations whose outcome cannot be reconstructed from current repository authority and required CI alone. Ordinary repository-only semantic, preservation, docs, and CI transactions do not add this ceremony merely because they executed tests or deterministic repository tooling.

Before claiming completion for an applicable execution, publish a concise repository-visible execution handoff on the shared transaction surface, normally the owning Issue discussion; when no owning Issue exists and a PR is the durable transaction surface, use the PR discussion. The handoff is historical working evidence. It is not current authority, an execution prompt, or authorization to reuse historical host state.

Retain only the material execution path:

- enough stable execution identity and conditions to disambiguate the run;
- materially distinct attempt deltas and their observable outcomes;
- the final successful path, or the terminal failure if no path succeeded;
- citable artifact or evidence references;
- candidate reusable lessons; and
- volatile observations explicitly labeled historical.

Do not turn the handoff into a raw log archive. Secrets, credentials, unbounded logs, prompt/request payloads, and transient process/GPU state remain outside it unless an existing evidence owner explicitly requires a bounded form. Prefer citable references to existing immutable evidence over copying its payload into the handoff.

Then classify each material lesson without widening mutation authority:

```text
reusable procedure or enforceable invariant
  → if already inside this transaction's mutation responsibility,
     converge it through the responsible owner / deterministic guard / regression
  → otherwise route it to the current owner or successor work;
     an execution-only transaction does not gain repository mutation authority

immutable execution result
  → preserve under the existing producer-owned evidence boundary

volatile / superseded observation
  → leave historical; do not copy into current authority
```

The shared handoff never replaces fresh repository authority, current upstream verification, live host/admission/capacity checks, or exact-head evidence required by the owning execution contract.

> **Do not preserve trial history as authority; preserve what the trial taught us.**

### Owning Issue reconciliation

After a successful merge, or after terminal completion of a bounded no-repository-mutation transaction, reconcile the owning Issue against current reality.

Use one of these outcomes:

```text
implemented completely
  → close completed

implemented partially
  → narrow the Issue to true remaining work
     or move that work to a successor and close the original

accepted design promoted
  → point to current authority / successor work and close or supersede

not adopted
  → close not planned

real work remains
  → keep open with current scope rewritten to describe only that work
```

Open Issues are planning and remaining-work ledgers, not current semantic authority or historical archives.

## 11. Stop conditions

Stop the current mutation and report/reconstruct the boundary when:

- semantic ownership is ambiguous or contested;
- competing work writes the same semantic contract;
- a required dependency is not yet merged;
- fresh repository facts cannot be obtained;
- the bounded transaction would require material unrelated scope expansion;
- fresh-head review finds a semantic or authority mismatch;
- required exact-head CI fails or is unavailable;
- current `v1` makes the planned change no longer necessary.

A stop condition does not authorize temporary compatibility machinery or duplicate ownership. Unrelated disjoint work may continue independently.

## 12. Completion shapes

Semantic change:

```text
fresh authority
  → meaning + examples
  → existing GREEN + meaningful RED
  → minimal implementation GREEN
  → owner-local authority convergence
  → fresh-head review
  → exact-head required CI GREEN
  → expected-head merge
  → Issue reconciliation
```

Behavior-preserving change:

```text
fresh authority
  → regression / characterization baseline
  → bounded simplification
  → equivalence GREEN
  → owner-local authority impact
  → fresh-head review
  → exact-head required CI GREEN
  → expected-head merge
  → Issue reconciliation
```

Docs-only change:

```text
fresh authority
  → bounded grounded correction
  → contradiction / ownership review
  → exact-head required CI GREEN
  → expected-head merge
  → Issue reconciliation
```

Physical/external execution-only transaction:

```text
fresh repository / owner / execution authority
  → bounded physical/external execution under its owning contract
  → producer-owned evidence or terminal outcome
  → shared execution handoff
  → reusable-learning reconciliation
  → Issue reconciliation
```

When a repository mutation shape also includes material physical/external execution covered by section 10, insert the same handoff and reusable-learning reconciliation before ordinary completion / Issue reconciliation.

## Fixed principles

1. **Meaning → Example → Test → Code → Docs/Authority → Audit.**
2. **One transaction = one bounded responsibility.**
3. **Semantic changes are test-first; preservation work uses characterization rather than manufactured RED.**
4. **One concept = one current owner.**
5. **Converge directly; do not preserve superseded internal semantics through compatibility machinery.**
6. **Owner-local authority is part of the implementation; derived aggregates are not routine write surfaces.**
7. **Review and CI evidence belong to the exact current head.**
8. **Parallel work requires disjoint semantic ownership.**
9. **Current authority never presents deferred behavior as implemented.**
10. **Necessary additions are allowed. Before completion, crystallize the transaction: challenge its claimed invariant across materially equivalent supported paths, integrate additions into existing principles, deduplicate, and generalize without widening mutation beyond the responsible semantic boundary.**
11. **Material physical/external execution is complete only after reusable learning is shared and reconciled without promoting trial history to authority.**
12. **A completed transaction reconciles its owning Issue after merge or terminal no-repository-mutation completion when one exists.**
