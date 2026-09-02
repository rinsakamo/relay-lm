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
  skills/<procedure>/SKILL.md        task-selected procedure implementations
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

## Repository-native procedures

Reusable procedures live under `.ai/skills/<procedure>/SKILL.md`. A materialized
skill is a supporting implementation surface declared by its semantic owner; it
may apply current authority, but it is not semantic authority itself.

Skills are loaded only when their responsibility matches the current task. Do
not place the entire skill library into the bootstrap context. Discover
materialized procedures from `.ai/skills/` and the owning declarations rather
than maintaining a second global skill registry or copying their contents into
tool-specific adapters.

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

qualification_inputs:
  - docs/architecture/context-compiler.md
  - src/relaylm/context.py

qualification_exclusions:
  - path: src/relaylm/context_diagnostics.py
    reason: Content-free diagnostics only; no context selection semantics.

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
| `qualification_inputs` | owner-selected existing local surfaces whose exact bytes participate in semantic qualification identity |
| `qualification_exclusions` | owner-local implementation paths deliberately outside that qualification identity, each with a non-empty machine-auditable reason |
| `depends_on` | consumer-owned dependency edges |
| `evidence` | evidence records produced and owned here |
| `evidence_refs` | evidence produced by another owner and only referenced here |
| `annotations` | rationale/history/explanatory prose, never current authority |

## Single-writer rules

- one canonical surface has exactly one owner;
- implementation and test surfaces may be shared, because code and tests are
  write surfaces rather than authority claims;
- every Python module under `src/relaylm/`, except `__init__.py` package markers,
  is declared by at least one semantic owner as an `implementation` surface;
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

Production implementation coverage proves that code is attached to at least one
semantic owner. It does not make implementation exclusive: legitimate shared
integration surfaces remain allowed and are reviewed under the owning semantic
contracts.

## Qualification identity

Semantic qualification uses the same owner graph rather than introducing a
second central path registry. An owner may opt existing local surfaces into
`qualification_inputs`. Each selected path must already be declared by that
owner as a canonical, implementation, test, annotation, or produced-evidence
surface; a `references` entry pointing at another owner's canonical document
cannot be restated as this owner's qualification input.

An owner may also disposition one of its own implementation surfaces through
`qualification_exclusions`. Every exclusion must name an implementation path
owned by that same declaration, must carry a non-empty reason, and cannot also
be selected as a qualification input. For a release qualification closure,
silence is not exclusion: every implementation surface must be selected or
explicitly excluded before coverage is complete.

Given one or more qualification root owners,
`tools.repository_authority.qualification_owner_closure(...)` follows the
transitive `depends_on` closure. `qualification_manifest(...)` then derives a
deterministic manifest containing the normalized roots, every owner in that
closure, each owner's selected inputs, and each owner's excluded implementation
paths. Exclusion reasons remain owner-local governance prose; the path
disposition, not wording edits to the reason, participates in product identity.
There is no committed aggregate list of all product paths.

`qualification_fingerprint(...)` hashes that manifest identity together with
the exact bytes of the selected files. Changing selected bytes, roots,
dependency closure, selected paths, excluded paths, or owner/path association
changes the fingerprint. Shared implementation files are read once as bytes
while the manifest still retains every owner association.

Tests, evaluation fixtures, actual-model harness implementation, and other
supporting surfaces are **not** qualification-significant merely because they
exist. They participate only when their semantic owner explicitly names them in
`qualification_inputs`. This prevents behavior-preserving harness work from
invalidating semantic product evidence by default.

The derived fingerprint primitive is not itself a release freeze. Selecting the
Core 1.0 inputs and committing a machine-enforced expected-fingerprint gate are
separate release transactions; the gate consumes this derived identity rather
than maintaining its own path list.

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
generator, projection schema version, frozen input commit, and package version,
so a reader can tell which repository state it describes without that
provenance appearing in the rendered page.

```bash
python -m tools.repository_docs --commit <frozen-input> write
python -m tools.repository_docs --commit <frozen-input> check
```

Normal semantic transactions never regenerate it; the release-candidate gate
requires it to match generation from the exact frozen candidate commit.

## Executable schema

`tools/repository_authority.py` is the canonical declaration schema. It is
executable rather than a separate schema document so the declaration contract
cannot drift from its validator, and its meaning is frozen by
`tests/unit/test_repository_authority_contract.py` and
`tests/unit/test_repository_qualification_fingerprint.py`.

`tools/repository_code_ownership.py` deterministically enforces production
implementation coverage against those declarations. Its boundary is frozen by
`tests/unit/test_repository_code_ownership_contract.py`.

`tools/repository_projection.py` is the canonical schema for recipes, frozen by
`tests/unit/test_repository_projection_contract.py`.

```bash
python tools/repository_authority.py validate
python -m tools.repository_code_ownership
python -m tools.repository_projection validate
```

`tests/unit/test_repository_authority.py`,
`tests/unit/test_repository_code_ownership.py`, and
`tests/unit/test_repository_projection.py` apply the same rules to the current
repository under the required `v1 CI / pytest` check, so authority or production
ownership drift fails the normal transaction gate rather than requiring a
separate audit.