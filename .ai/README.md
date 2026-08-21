# RelayLM agent authority root

`.ai/` is the repository-local authority root for AI-first RelayLM `v1` development.

It exists so that an agent can determine ownership without reading a
hand-maintained global registry:

> **Every authoritative fact has exactly one canonical writer.**

## Layout

```text
.ai/
  README.md                         this file: the bootstrap entry point
  agent-contract.yaml               read order and freshness contract
  authority/<semantic_owner>.yaml   one writable authority unit per semantic owner
  projections/<recipe>.yaml         recipes for reconstructing developer views
```

## Bootstrap

`.ai/agent-contract.yaml` declares the ordered read path an agent follows when
orienting:

```text
entry point
  -> read order and freshness
  -> development workflow
  -> semantic owner
  -> that owner's canonical surfaces
```

A root tool adapter such as `AGENTS.md` may route an agent here, but it must stay
thin and must not copy the workflow, product semantics, or current repository
state into a second instruction surface.

## Freshness

The same contract classifies every fact a transaction relies on. Freshness is
repository authority, not prompt convention:

```text
repository HEAD / open PRs / CI state / Issue state   live
semantic ownership / canonical surfaces               repository
merged evidence                                       evidence
mutable external/upstream claims                       upstream
handoff prompt state / projection output              historical
```

A `live` fact is re-fetched at the start of a transaction and again immediately
before merge; it is never written into a declaration. A `historical` fact —
including the SHA, PR, and status quoted in a handoff prompt — is never current
authority. Because those classes are declared, an agent does not need bootstrap
prose telling it which parts of a handoff to distrust.

An `upstream` fact is different from repository/host `live` state. Its current
authority lives outside RelayLM, so it is verified from the current primary
upstream documentation, source, schema, release information, or other
appropriate authoritative surface when the claim materially affects a
decision. It is not fetched merely because every transaction started. Remembered
behavior and secondary summaries are not current authority. If RelayLM records
an owner-approved contract or immutable evidence result for a specific claim,
consumers use the resulting `repository` or `evidence` authority instead of
silently treating the original external claim as persistent truth.

Declarations are checked for copied live state: a 40-character commit id
appearing anywhere in a declaration fails validation.

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
  not copy the producer's results, and an evidence surface may not be declared
  by any other owner or restated as the producer's own implementation;
- live repository facts — current HEAD, open PRs, CI results, current Issue
  state — are never copied into a declaration;
- every document under `docs/` is claimed by exactly one owner, as a canonical
  surface or as an annotation;
- the dependency graph is acyclic;
- hand-maintained authority aggregates are prohibited; the previous
  `docs/authority-map.yaml` navigation index is replaced by these declarations.

## Projections

Developer-facing views are reconstructed on demand, never hand-maintained and
never committed:

```bash
python -m tools.repository_projection list
python -m tools.repository_projection render dependency-map
```

A recipe stores only what is needed to rebuild the view — inputs, freshness
requirements, selection rules, prohibited inferences, and a preferred output
shape. Rendering is deterministic and derives every fact from
`.ai/authority/`. Facts that committed authority cannot supply are printed as
live inputs the agent must fetch, so a rendered view never carries a
remembered HEAD, PR list, or check result.

> **Store canonical facts and projection recipes, not transient views.**

## Persistent projections

`ARCHITECTURE.md` is generated, not written. It is materialized from these
declarations at a version/release boundary and carries provenance naming the
frozen input commit it describes.

```bash
python -m tools.repository_docs --commit <frozen-input> write
python -m tools.repository_docs --commit <frozen-input> check
```

Normal semantic transactions never regenerate it; the release-candidate gate
requires it to match generation from the exact frozen candidate commit.

## Executable schema

`tools/repository_authority.py` is the canonical schema. It is executable
rather than a separate schema document so the contract cannot drift from its
validator, and its meaning is frozen by
`tests/unit/test_repository_authority_contract.py`.

`tools/repository_projection.py` is the canonical schema for recipes, frozen by
`tests/unit/test_repository_projection_contract.py`.

```bash
python tools/repository_authority.py validate
python -m tools.repository_projection validate
```

`tests/unit/test_repository_authority.py` and
`tests/unit/test_repository_projection.py` applies the same rules to the current
repository under the required `v1 CI / pytest` check, so authority drift fails
the normal transaction gate rather than requiring a separate audit.
