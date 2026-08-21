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

This document defines the repository-level traceability and dependency rules for that model. It does not redefine product semantics owned by component contracts, repository-authority schema mechanics, or CI guarantees.

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

A derived internal runtime realization edge is structurally explainable when at least one of these conditions holds:

1. the importing and imported realization surfaces share at least one semantic owner; or
2. at least one semantic owner of the importing surface can reach at least one semantic owner of the imported surface through the declared semantic dependency graph.

The second condition may be direct or transitive. Reachability is an explanation that the implementation dependency sits beneath an existing semantic dependency chain; it is not a claim that every intermediate owner is directly invoked by the code.

This rule gives shared integration surfaces a natural representation without adding a second hand-maintained dependency registry.

Example:

```text
cognitive_turn --depends_on--> state_and_validation
      |                              |
      | realizes                     | realizes
      v                              v
openai_compatible.py -----------> state.py
          derived runtime edge
```

If `openai_compatible.py` is shared by `cognitive_turn` and another owner, the owner set is considered as a set rather than forcing one arbitrary file owner.

## Unexplained runtime realization edges

A statically resolvable RelayLM-internal **runtime** realization dependency is unexplained when the two realization surfaces have disjoint owner sets and no importing owner can reach an imported owner through semantic `depends_on`.

Explicit type-only imports such as imports under `TYPE_CHECKING` are outside this finding set.

An unexplained edge is an architecture-review signal. It must not be repaired automatically by adding dependency declarations.

The owning transaction must determine which current-state explanation is correct:

1. **missing semantic dependency** — the consumer semantics genuinely require the imported owner's semantics, so the consumer updates its `depends_on`;
2. **shared integration realization** — the importing surface genuinely realizes more than one owner and its implementation ownership is incomplete;
3. **missing boundary** — an interface, adapter, composition seam, or owner-local realization should be extracted or moved;
4. **accidental coupling** — the import or call should be removed;
5. **type-only boundary** — the dependency is not needed at runtime and should be made explicit with the language/tooling mechanism rather than authority metadata.

Do not introduce a new dependency kind merely to silence a finding. Add repository metadata only when repeated real cases prove that the existing authority and ownership model cannot explain the relationship.

## Candidate deterministic validation

A deterministic runtime-realization validator may audit dependencies with the following bounded responsibility:

1. parse statically resolvable imports within `src/relaylm/**`;
2. exclude imports explicitly contained under `TYPE_CHECKING` from runtime edges;
3. map each production module to its semantic owner set using existing `implementation` declarations;
4. derive internal runtime realization edges;
5. treat owner overlap as explained;
6. otherwise test semantic reachability through existing `depends_on` edges;
7. report only the remaining unexplained runtime edges.

The validator must not:

- equate the Python import graph with the semantic dependency graph;
- add or mutate `depends_on` automatically;
- reject legitimate shared implementation;
- infer product semantics from code layout;
- treat external-library imports as semantic-owner dependencies;
- treat explicit type-only imports as runtime realization coupling;
- require dynamic or reflective runtime behavior to be statically reconstructed in the first implementation;
- turn artifact flow into semantic dependency metadata.

Before such a validator becomes a required gate, its current-repository findings must be audited and reconciled owner-locally, as was done for production ownership coverage.

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
