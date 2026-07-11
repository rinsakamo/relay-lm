---
relaylm_doc_type: adr
relaylm_authority: decision_to_adopt_authority_first_documentation_hard_cutover
relaylm_status: target
relaylm_decision_status: accepted
relaylm_decided_on: 2026-07-11
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - decision is superseded
  - v0.1 frozen tag receipt is finalized
  - documentation cutover completes
relaylm_not_authoritative_for:
  - current runtime behavior
  - current implementation phase status
  - proof that documentation cutover is complete
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_proposal:
  - ../proposals/documentation_restructure_proposal.md
relaylm_supersedes: []
relaylm_superseded_by: null
---
# ADR 0002: Adopt authority-first documentation architecture by hard cutover

This ADR is authoritative for the decision to replace RelayLM's mixed documentation structure with the authority-first model. It does not move existing canonical paths or claim that the cutover has completed.

## Status

Accepted as target documentation architecture on 2026-07-11.

Preparation begins immediately. Canonical path moves and deletions begin only after the v0.1 final main-HEAD validation and frozen tag receipt are finalized.

## Context

RelayLM currently has hundreds of Markdown files whose directory, type, status, and granularity do not reliably identify their authority. Architecture, exact contracts, implementation handoffs, evaluation records, release evidence, strategic direction, and historical snapshots frequently share the same directory and retrieval vocabulary.

The repository conditions are unusual but favorable to a one-time hard cutover:

- one primary maintainer;
- pre-v0.1;
- no published stable documentation-path API;
- primary readers are the repository owner and AI coding agents;
- Git history is available for obsolete material.

Maintaining redirect stubs, legacy manifests, old enum aliases, hybrid-document exceptions, or dual-path compatibility would preserve the ambiguity the restructure is intended to remove.

## Decision

RelayLM will adopt an authority-first documentation model with these canonical collections:

```text
guides
reference
strategy
planning
architecture
contracts
adr
operations
evaluation
release
evidence
```

Support collections `assets`, `templates`, and undecided `proposals` remain distinct from authority collections.

The cutover follows these rules:

1. Existing documents are classified by actual authority rather than moved one-to-one.
2. Active documents have one primary authority.
3. Architecture is synthesized into system, subsystem, and concept/policy forms.
4. Exact contracts move to `docs/contracts/` with normative text preserved verbatim and digest-verified.
5. Meaningful decisions and verification evidence remain in `docs/evidence/`; low-value snapshots are deleted from the active tree and remain in Git history.
6. Redirect stubs, legacy manifests, new legacy-enum use, and hybrid exceptions are not introduced.
7. Repository-wide mixed structure may exist between cutover PRs, but each migrated authority has only one live path.
8. Every path move or deletion updates path-bound audits, workflows, scripts, and live links in the same PR.
9. Blocking audit rules are limited to objective MUST checks; subjective structure checks begin as WARN.
10. Code-derived reference generators and drift checks are a post-cutover track and do not block the documentation cutover.

## Preparation boundary

Before the v0.1 frozen tag receipt, Preparation may add:

- this ADR and the adopted documentation model;
- non-authoritative templates;
- the canonical glossary draft;
- architecture inventory and target graph;
- provenance and normative-block digest tooling;
- dry-run artifacts and path-bound CI dependency inventory.

Preparation does not move or delete current canonical documentation paths, except that the accepted proposal may be archived with its decision source either during Preparation or the first cutover PR.

## Cutover order

After the v0.1 receipt:

1. migrate retained evidence and delete Git-history-only snapshots;
2. finalize architecture inventory and target graph;
3. synthesize architecture and reclassify other active documents;
4. reconstruct contracts verbatim and verify digests;
5. delete the old tree and enable final MUST enforcement.

## Consequences

### Positive

- AI retrieval can infer authority from path, type, and opening summary.
- Exact contracts have one canonical home.
- Architecture becomes stable-concept oriented rather than milestone oriented.
- Historical evidence no longer competes with current authority.
- CI can converge on generic directory and authority invariants instead of large hard-coded path lists.
- Future documentation changes have clearer ownership and update triggers.

### Costs

- External links to old documentation paths may break.
- The cutover will touch many files and requires careful sequencing.
- Architecture synthesis requires judgment rather than mechanical moves.
- Contract migration requires old-blob/new-document verification receipts.
- Long-lived branches may require substantial rebasing.

## Rejected alternatives

### Preserve old paths with redirect stubs

Rejected because stubs retain old vocabulary in the AI retrieval space and create permanent compatibility work.

### Maintain a legacy manifest

Rejected because the manifest mainly exists to preserve old metadata semantics. Provenance can instead be generated from Git history during cutover.

### Keep hybrid documents and add exceptions

Rejected because exception lists make mixed authority permanent and weaken one-document/one-authority enforcement.

### Complete reference generators before cutover

Rejected because generator implementation is toolchain development and would unnecessarily block the structural migration.

### Move every file one-to-one

Rejected because the current problem includes duplicated content and inconsistent granularity, not only incorrect directories.

## Fixed safeguards

Only three migration safeguards are retained:

- deterministic one-time ADR canonicalization;
- placement and granularity tie-breakers;
- verbatim normative contract migration with digest verification.

## Related documents

- [Documentation model](../DOCUMENTATION_MODEL.md)
- [Hard-cutover proposal](../proposals/documentation_restructure_proposal.md)
- [Document templates](../templates/README.md)
- [Canonical glossary draft](../reference/glossary.md)
