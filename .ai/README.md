# RelayLM agent authority root

`.ai/` is the repository-local authority root for AI-first RelayLM `v1` development.

It exists so that an agent can determine ownership without reading a
hand-maintained global registry:

> **Every authoritative fact has exactly one canonical writer.**

## Layout

```text
.ai/
  authority/<semantic_owner>.yaml   one writable authority unit per semantic owner
```

## Owner-local authority declarations

`.ai/authority/<id>.yaml` is written only by the semantic owner it names. One
declaration is the owner's complete local authority; there is no central file
that a lane must edit merely to register itself.

```yaml
schema_version: 1
id: context_compiler
owner_issue: 1267
summary: Context authority, selection, and retrieval assembly semantics.

canonical_surfaces:
  - docs/architecture/context-compiler.md

references:
  - docs/architecture/core.md

implementation:
  - src/relaylm/context.py

tests:
  - tests/unit/test_context_state_selection.py

depends_on:
  - persistence

evidence:
  - id: example-evidence-v1
    summary: What the producing owner proved.
    surfaces:
      - docs/reference/example-evidence.md

evidence_refs:
  - other-owner-evidence-v1

annotations:
  - docs/decisions/0003-direct-canonical-convergence.md
```

Field roles:

| field | role |
| --- | --- |
| `canonical_surfaces` | authority documents this owner exclusively writes |
| `references` | non-owning pointers to another owner's canonical surface |
| `implementation` | supporting write surfaces; not an authority claim |
| `tests` | executable contracts covering this owner |
| `depends_on` | consumer-owned dependency edges |
| `evidence` | evidence records produced and owned here |
| `evidence_refs` | evidence produced by another owner and only referenced here |
| `annotations` | rationale/history/explanatory prose, never current authority |

## Single-writer rules

- one canonical surface has exactly one owner;
- implementation and test surfaces may be shared, because code and tests are
  write surfaces rather than authority claims;
- reverse dependencies (`consumed_by`) are derived from consumers'
  `depends_on` and are never declared a second time;
- evidence is owned by its producer; consumers reference an evidence id and do
  not copy the producer's results;
- live repository facts — current HEAD, open PRs, CI results, current Issue
  state — are never copied into a declaration;
- every document under `docs/` is claimed by exactly one owner, as a canonical
  surface or as an annotation;
- the dependency graph is acyclic;
- hand-maintained authority aggregates are prohibited; the previous
  `docs/authority-map.yaml` navigation index is replaced by these declarations.

## Executable schema

`tools/repository_authority.py` is the canonical schema. It is executable
rather than a separate schema document so the contract cannot drift from its
validator, and its meaning is frozen by
`tests/unit/test_repository_authority_contract.py`.

```bash
python tools/repository_authority.py validate
```

`tests/unit/test_repository_authority.py` applies the same rules to the current
repository under the required `v1 CI / pytest` check, so authority drift fails
the normal transaction gate rather than requiring a separate audit.
