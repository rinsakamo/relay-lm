---
relaylm_doc_type: operations
relaylm_authority: documentation_domain_synthesis_and_git_history_retirement_procedure
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - the D2-D6 synthesis or retirement procedure changes
  - generic documentation validation or retirement evidence changes
  - source disposition, rollback, or recovery requirements change
  - router, workflow, registry, or generated-navigation repair steps change
relaylm_not_authoritative_for:
  - exact metadata, retained-record classes, or retirement-manifest schema
  - runtime, storage, API, UI, memory, or Retrieval semantics
  - repository-wide implementation completion
  - deletion of a source outside the reviewed PR scope
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source: ../adr/0006-repository-structure-and-maintenance-sequencing.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - ../contracts/documentation-governance.md
  - ../architecture/documentation-governance.md
  - ../architecture/repository-maintenance-system.md
  - ../planning/repository-structure-migration.md
relaylm_verified_by:
  - ../../scripts/relaylm_documentation_governance_validate.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - documentation maintainers
  - migration reviewers
  - AI coding agents
relaylm_authority_level: operation
---
# Documentation Synthesis and Retirement

## Purpose

This runbook is the repeatable D2-D6 procedure for replacing a reviewed source set with canonical active authority and retiring consumed historical paths to Git. It applies after D1 governance activation. Exact rules remain in the [Documentation Governance Contract](../contracts/documentation-governance.md); system responsibility is explained in [Documentation Governance Architecture](../architecture/documentation-governance.md).

## Preconditions

Before any branch write:

1. bind exactly one Lane D item and refresh exact current `origin/main`;
2. read current execution authority and compute the current governance epoch;
3. confirm one logical writer, no branch-pushing validation, no transfer PR, no temporary artifact, and no `relaylm:p6-stop`;
4. confirm the Lane D PR slot is free or select the existing Lane D PR;
5. inspect other lanes read-only for path, authority, caller, registry, router, and merge-order overlap;
6. record P0 scope, P1 strategy, P2 gate result, and the current execution receipt before ordinary implementation proceeds.

A stale main, stale epoch, writer collision, temporary machinery, or stop label requires re-bootstrap rather than a corrective patch.

## 1. Fix the atomic boundary

Record:

```text
canonical target documents
source-document set
code, contract, status, test, workflow, registry, and operator anchors
normative extraction result
retained-record decisions
retirement-manifest effect
links, routers, workflows, registries, and validators affected
current-versus-target separation
parallel-safety analysis
rollback and recovery boundary
```

The PR must own one complete authority boundary. Do not mix unrelated domains, Lane C semantic changes, Lane R package movement, or a new numbered Documentation Hard Cutover slice.

## 2. Determine canonical granularity

For each target authority, identify:

- owner;
- update trigger;
- lifecycle;
- primary consumers;
- authority level;
- current or accepted-target status;
- exact non-authorities.

Split when any dimension differs. Architecture, exact contract, planning, lookup, procedure, current status, and historical evidence are independent responsibilities even when they originated in one source file.

Reject milestone-oriented permanent target names. Use function- and responsibility-oriented paths.

## 3. Enumerate the complete source and consumer set

Inspect every source section and every current reference root:

- Markdown body links and front-matter relationships;
- routers and collection indexes;
- code and test literals;
- workflows and subprocess commands;
- registries and generated navigation;
- operator procedures and rollback instructions;
- retained-record catalogs and transitional-asset entries;
- current status and execution planning.

Static search is a starting point, not proof of completeness. Dynamic, workflow, operator, migration, and historical-consumer roots must be considered when they can preserve a supported responsibility.

## 4. Classify source content

Disposition each durable block as one of:

```text
architecture
exact normative contract
current status
planning or migration sequence
reference or lookup
operations or guide
allowlisted retained record
historical or non-normative Git-only material
```

A source cannot be deleted while still-live architecture or normative content lacks an accepted target or an explicit reviewed disposition.

## 5. Perform normative extraction review

Normative material includes exact fields, schemas, states, transitions, gates, artifacts, APIs, safety-significant commands, and must/must-not language.

For each candidate block, record one reviewed disposition allowed by the governance contract. An exact-copy migration records source path, source blob, line range, normalized digest, target path, target range, and target digest. A wording change is a contract change, not a mechanical extraction.

Keyword matching may identify candidates but cannot prove complete normative coverage.

## 6. Build canonical active documents

Create or revise the smallest permanent authorities. Each active target must:

- use an allowlisted location and document type;
- carry complete canonical metadata;
- claim one globally unique primary authority;
- distinguish current implementation from accepted target;
- link to exact contracts rather than reproduce their tables;
- link to Project Status rather than duplicate repository-wide completion claims;
- avoid copying milestone history into stable architecture.

No old path remains as a redirect, compatibility stub, archived duplicate, or fallback authority.

## 7. Decide record retention

A source or result stays under `records/` only if it matches one allowlisted class and has a continuing current function, owner, current consumer, media type, schema or validator, and catalog entry.

Ordinary completion reports, proposals, handoffs, superseded designs, dated narratives, and copied retired prose do not become records by default. Their recovery surface is Git and pull-request history.

## 8. Repair all current references

In the same PR:

- replace body and metadata links to retired paths;
- update `docs/README.md` and collection routers;
- update current plans, ADR relationships, references, and operations pages;
- update workflow, script, test, registry, and operator literals;
- regenerate navigation from source authority when required;
- remove obsolete transitional consumers only when their removal gate is satisfied.

Do not edit generated output directly. Change its source authority and regenerate deterministically.

## 9. Add retirement-manifest entries and delete sources

For each retiring path:

1. resolve the last live commit from the exact current base;
2. resolve the old blob SHA;
3. choose replacement paths and disposition;
4. record the active PR number and bounded retention reason;
5. sort entries and replacement paths deterministically;
6. delete the old path in the same PR.

The manifest contains navigation and provenance only. It never contains copied source prose or semantic replacement text.

## 10. Validate the exact proposed head

Run the generic documentation governance validator and all affected link, semantic, workflow, registry, and generated-drift checks. Confirm:

- canonical metadata and authority uniqueness;
- current/target separation;
- complete normative disposition;
- retained-record allowlisting;
- commit/blob recoverability for every new retirement entry;
- absence of every retired path at the proposed head;
- existence of every replacement path;
- no stale references in Markdown, metadata, code, tests, workflows, registries, or operations;
- no redirect, duplicate archive, symlink, fallback, or dual live authority;
- no temporary patch, probe, transfer, or branch-writing workflow;
- current receipt, exact-main ancestry, and clean execution guard.

CI success does not replace complete-diff review.

## 11. Review and correction

Review every changed file and every affected consumer. Classify findings before editing:

```text
local defect
  -> correct the root cause -> validate exact head -> fresh complete review

architecture defect, duplicate authority, repeated special case,
or third identical failure
  -> P6-STOP -> current-main re-bootstrap -> return to P1

cross-lane defect
  -> record the exact blocker -> do not edit the other lane
```

Do not reset a repeated failure by changing only prose, filenames, workflow names, or branch heads.

## 12. Merge and post-merge convergence

Merge only with expected-head protection after the receipt, checks, reviews, threads, labels, mergeability, and temporary-artifact inventory are clean. Then:

1. verify the merge commit and resulting `main`;
2. verify post-merge checks;
3. verify retired paths remain absent and replacement paths resolve;
4. verify the manifest entry on `main`;
5. release the Lane D slot;
6. select only the next executable Lane D item.

## Rollback and recovery

Before merge, abandon or revert the branch. After merge, a revert may restore the old path mechanically, but it must not create two active authorities. A semantic restoration requires a new reviewed canonical authority decision.

To inspect retired content:

```bash
git show <last_live_commit>:<old_path>
git cat-file -p <old_blob_sha>
```

Use the retirement manifest to locate identity and replacement paths. Do not reconstruct a general archive tree.

## Stop conditions

Stop without ordinary writes when:

- scope or lane binding is ambiguous;
- the exact main or governance epoch changed;
- another writer or branch-writing automation exists;
- a stop label or unresolved failure state exists;
- source content requires an unresolved policy, lifecycle, migration, rollback, state, or semantic decision;
- normative disposition is incomplete;
- another lane owns the required correction;
- the proposed retirement cannot prove current-reference repair or Git recoverability.
