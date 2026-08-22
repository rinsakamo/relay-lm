# Executable Realization and Dependency Model

RelayLM separates semantic authority from the code that executes it and from the results produced by that execution.

The repository model is:

```text
Semantic Authority
      |
      | realizes
      v
Executable Realization
      |
      | executes
      v
Execution Artifact / Effect
```

This document defines the repository-level realization quality, traceability, and dependency rules for that model. It does not redefine product semantics owned by component contracts, repository-authority schema mechanics, or CI guarantees.

## Semantic authority

Semantic authority defines what RelayLM means or requires. A canonical authority may be prose, structured metadata, an executable schema, or another owner-approved canonical surface.

Authority is normative. Observing how current code behaves does not promote that behavior into specification.

A semantic owner may depend on another semantic owner through the existing consumer-owned `depends_on` edge when the consumer's own semantics require the dependency's semantics to be defined or interpreted.

`depends_on` therefore remains a **semantic dependency**. It is not a transcription of Python imports, runtime calls, file references, or artifact flow.

## Executable realization

An executable realization is code that gives operational form to semantic authority.

For repository authority declarations:

- `implementation` traces an owner to production or supporting executable realization surfaces;
- `tests` traces an owner to verification realizations that exercise or enforce its contract.

A realization is not a second semantic authority. If implementation behavior and canonical authority disagree, the mismatch must be reconciled through the owning semantic transaction rather than declaring the code authoritative by observation.

A realization may legitimately serve more than one semantic owner. Shared realization is especially expected at adapter, transport, orchestration, serialization, composition, or integration boundaries.

> **Shared realization means shared implementation responsibility, not shared semantic authorship.**

Shared realization is not an audit escape hatch. Add another owner to an implementation surface only when that surface genuinely realizes semantics owned by that owner independent of any dependency-audit finding. Never add shared ownership merely to make an otherwise unexplained edge pass structural validation.

## Minimal sufficient realization

> **Code is a minimal sufficient executable realization of authority.**

Correctness is judged first by semantic fidelity: the code must realize the owning authority without inventing, weakening, or silently replacing its meaning.

Simplicity and sufficient shortness are structural constraints, not independent goals. A realization must be no more complex than required to execute its current authority faithfully. Line count by itself is not a correctness or quality invariant.

Prefer the simplest deterministic realization that fully satisfies the contract. Additional semantic decisions, abstraction layers, branching, mutable state, dependencies, configuration, compatibility paths, or fallback behavior require a current semantic reason.

The constraint is:

1. **no unnecessary semantics** — do not add decisions that the current authority does not require;
2. **no unnecessary mechanism** — when multiple implementations faithfully realize the same semantics, prefer the mechanically simpler deterministic one;
3. **no unnecessary surface** — do not add modules, classes, interfaces, configuration, compatibility layers, or extension points without a current responsibility.

Speculative extensibility is not a current responsibility. "This may be useful later" does not justify an abstraction by itself.

Physical size measures such as lines per function, lines per module, function count, or class count may be review hints. They must not become hard limits that reward artificial splitting. Evaluate semantic coupling, state transitions, side effects, branches, special cases, and dependency fan-in before line count.

If the authority is insufficient to determine required behavior, the realization must not fill the gap with an implementation-local semantic guess. Stop the semantic change, reconcile authority, then realize the clarified contract.

## Realization quality boundaries

### Side effects

Keep deterministic semantic decisions separate from externally observable effects when practical.

```text
deterministic decision
       -> explicit owned effect boundary
       -> filesystem / persistence / network / provider / clock / external system
```

A side effect must be attributable to an owning contract. Hidden mutation, I/O, provider calls, clock dependence, or external state access inside otherwise semantic/pure logic is a coupling signal and requires a current reason.

This does not require artificial interfaces around every operation. Extract a boundary when it makes ownership, failure behavior, verification, or replacement materially clearer.

### State mutation ownership

A realization may read or observe semantics owned elsewhere when its contract permits that dependency, but it mutates only state whose mutation authority is explicitly assigned by the governing contract.

Read, select, rank, validate, project, and observe operations must not become hidden write paths. Cross-owner state mutation is a strong decomposition signal.

### Failure semantics

Failure behavior is semantic behavior.

Reject, skip, retry, repair, default, degrade, and fallback are not interchangeable implementation conveniences. The governing authority determines which behavior is valid at a boundary.

> **Fallback is semantics, not error-handling convenience.**

Do not add silent repair, coercion, compatibility defaults, retries, or fallback paths merely to make a caller succeed. When the contract requires fail-closed or explicit failure behavior, realize that behavior directly and test it.

### Abstraction

Extract an abstraction when current semantics or repeated mechanics justify one, not merely because reuse appears possible.

Mechanical duplication may be acceptable when extracting it would create semantic coupling. Duplicated semantic decisions are not: one semantic rule should have one normative implementation home.

Interfaces, generic layers, plugin seams, factories, and base classes require the same current-need justification as any other mechanism.

### External dependencies

Mutable external/provider/library behavior stays behind the realization boundary that translates it into RelayLM semantics.

```text
RelayLM semantic vocabulary
       -> adapter / boundary realization
       -> provider or library specific API
```

Do not leak provider-specific shapes, defaults, parameter names, or compatibility behavior into unrelated core semantic owners when an owned adapter can contain them.

### Replacement and deletion

When a realization is superseded, remove the obsolete path in the same owning convergence unless current authority explicitly requires coexistence or compatibility.

Do not preserve dead helpers, aliases, duplicate read/write paths, temporary bridges, or deprecated behavior by habit. Git preserves the previous realization; current source describes the current executable system.

### Verifiability and local comprehensibility

Tests freeze the meaning that the code must realize, including material failure and boundary cases. A realization that cannot be verified without depending on unrelated mutable context is a design signal even when it currently works.

A bounded code change should normally be understandable from its semantic owner, materially required dependency contracts, its realization, and its tests. Requiring broad unrelated repository or historical context merely to reason about one local change is a coupling signal.

## Execution artifacts and effects

Executing a realization may produce an artifact or an effect.

Examples include:

- a runtime response;
- accepted or rejected State candidates;
- persisted Event or State changes;
- a generated projection;
- a wheel or source distribution;
- a test or CI result;
- an evaluation result or evidence artifact;
- an external side effect performed through an owned runtime boundary.

An artifact records or embodies an execution result. It does not automatically become semantic authority.

Evidence may be authoritative for the observation it records when registered through the evidence-owning contract, but evidence does not redefine product semantics by itself. A semantic change informed by evidence requires a separate authority transaction.

The feedback path is therefore:

```text
Authority
   -> Realization
   -> Artifact / Effect
   -> Evidence or observation
   -> reviewed semantic decision, if needed
   -> Authority update
```

## Dependency vocabulary

RelayLM keeps different dependency meanings separate instead of forcing them into one graph.

### Semantic dependency

```text
Authority A --depends_on--> Authority B
```

Meaning: A's semantic contract requires B's semantic contract.

Properties:

- declared by the consumer;
- persistent repository authority;
- directional;
- acyclic under the current repository-authority contract;
- intentionally coarser than source-code imports.

### Realization ownership

```text
Authority A --implementation/tests--> Realization M
```

Meaning: M realizes or verifies semantics owned by A.

Properties:

- declared through existing owner-local surfaces;
- may be shared across multiple owners;
- establishes traceability from code to semantic authority;
- does not make the code itself semantic authority.

### Runtime realization dependency

```text
Realization M --imports/calls/uses at runtime--> Realization N
```

Meaning: one executable realization mechanically depends on another while executing product, build, verification, or tooling behavior.

This relation is derived from code when useful. It is **not persisted as semantic authority by default**.

A runtime Python import is evidence of a realization dependency, not evidence of a semantic dependency.

### Type/interface dependency

A realization may reference another realization only to describe a type or static interface without loading or invoking it at runtime.

Python code should make this distinction explicit with native language/tooling mechanisms when practical. In particular, an import contained under `if TYPE_CHECKING:` is an explicit **type-only dependency** and is not a runtime realization edge.

Type/interface dependencies:

- do not create semantic `depends_on` automatically;
- do not require shared implementation ownership merely because a type is referenced;
- may be audited separately if recurring interface coupling becomes useful to inspect;
- should not be mixed into the first runtime-realization dependency gate.

When an import is genuinely type-only but written as an unconditional runtime import, prefer making the type-only boundary explicit when that can be done without changing runtime semantics. Do not add repository dependency metadata merely to compensate for an imprecise source-level boundary.

### Artifact production and consumption

```text
Realization M --executes--> Artifact X
Consumer N --consumes/references--> Artifact X
```

Artifact flow is a runtime, build, verification, or evidence relationship. It does not automatically create an authority `depends_on` edge.

Evidence production and evidence references continue to use their dedicated repository-authority fields. Runtime data flow remains owned by the relevant product contract.

## Explaining runtime realization dependencies

A derived internal runtime realization edge is classified from existing authority rather than converted into new dependency metadata.

1. **shared realization** — the importing and imported surfaces share at least one semantic owner;
2. **direct semantic explanation** — an importing owner directly `depends_on` an imported owner;
3. **transitive semantic explanation** — no shared owner or direct dependency explains the edge, but an importing owner can reach an imported owner through a longer semantic dependency chain;
4. **unexplained** — none of the conditions above holds.

Shared realization and a direct semantic dependency structurally explain the runtime edge.

Transitive semantic reachability is weaker. It demonstrates that the edge lies beneath an existing semantic dependency chain, but it may also reveal a realization that skips an intended intermediate boundary. A **transitive-only** edge is therefore not an unexplained dependency error, but it remains an architecture-review signal until the direct runtime coupling is understood.

This distinction avoids both extremes: RelayLM does not require every Python import to have a matching direct `depends_on`, and it does not silently treat every reachable semantic path as equivalent to a direct implementation boundary.

Example:

```text
cognitive_turn --depends_on--> state_and_validation
      |                              |
      | realizes                     | realizes
      v                              v
openai_compatible.py -----------> state.py
          derived runtime edge
```

If `openai_compatible.py` is shared by `cognitive_turn` and another owner, the owner set is considered as a set rather than forcing one arbitrary file owner. That shared ownership must still be independently justified by the semantics the file actually realizes.

## Transitive-only runtime realization edges

A statically resolvable RelayLM-internal runtime edge is **transitive-only** when:

- the two realization surfaces do not share an owner;
- no importing owner directly depends on an imported owner; and
- at least one importing owner can reach an imported owner only through two or more semantic dependency edges.

A transitive-only finding is review data, not authority and not an automatic failure condition. The review asks whether the direct implementation coupling is appropriate or whether the realization should instead use an existing intermediate boundary.

Do not repair a transitive-only finding by adding a direct semantic dependency unless the consumer's canonical semantics genuinely require that direct dependency.

## Unexplained runtime realization edges

A statically resolvable RelayLM-internal **runtime** realization dependency is unexplained when the two realization surfaces have disjoint owner sets and no importing owner can reach an imported owner through semantic `depends_on`.

Explicit type-only imports such as imports under `TYPE_CHECKING` are outside this finding set.

An unexplained edge is a required repository-invariant failure and an architecture-review signal. The current repository must have zero unexplained runtime realization edges. A finding must not be repaired automatically by adding dependency declarations.

The owning transaction must determine which current-state explanation is correct:

1. **missing semantic dependency** — the consumer semantics genuinely require the imported owner's semantics, so the consumer updates its `depends_on`;
2. **shared integration realization** — the importing surface genuinely realizes more than one owner and its implementation ownership is incomplete;
3. **missing boundary** — an interface, adapter, composition seam, or owner-local realization should be extracted or moved;
4. **accidental coupling** — the import or call should be removed;
5. **type-only boundary** — the dependency is not needed at runtime and should be made explicit with the language/tooling mechanism rather than authority metadata.

Shared integration realization is valid only when the implementation already has real semantic responsibility for the additional owner. It must not be chosen solely because it makes the audit green.

Do not introduce a new dependency kind merely to silence a finding. Add repository metadata only when repeated real cases prove that the existing authority and ownership model cannot explain the relationship.

## Deterministic validation

A deterministic runtime-realization validator audits dependencies with the following bounded responsibility:

1. parse statically resolvable imports within `src/relaylm/**`;
2. exclude imports explicitly contained under `TYPE_CHECKING` from runtime edges;
3. map each production module to its semantic owner set using existing `implementation` declarations;
4. derive internal runtime realization edges;
5. classify owner overlap as shared realization;
6. classify a one-edge semantic relationship as directly explained;
7. classify longer semantic reachability as a transitive-only review signal;
8. report only unreachable edges as unexplained dependency errors.

The validator must not:

- equate the Python import graph with the semantic dependency graph;
- add or mutate `depends_on` automatically;
- reject legitimate shared implementation;
- infer that shared ownership is legitimate merely because it removes a finding;
- infer product semantics from code layout;
- treat external-library imports as semantic-owner dependencies;
- treat explicit type-only imports as runtime realization coupling;
- require dynamic or reflective runtime behavior to be statically reconstructed in the first implementation;
- turn artifact flow into semantic dependency metadata.

Repository CI requires zero unexplained runtime realization dependency errors against the current repository. Transitive-only findings remain non-gating architecture-review signals; their existence or count does not by itself fail this invariant.

## Traceability invariant

The durable invariant is not "every import has a matching dependency declaration."

It is:

> **Every executable realization is attached to semantic authority, and runtime cross-realization coupling remains explainable from that authority or an explicit shared integration boundary.**

This preserves the direction of RelayLM's architecture:

```text
Authority defines.
Realization executes.
Artifacts record or embody results.
Evidence may inform the next authority decision.
```
