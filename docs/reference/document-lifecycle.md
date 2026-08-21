# Document Lifecycle and History

This document defines how RelayLM `v1` documentation changes over time.

The core rule is:

> **Canonical documents describe the present. Git preserves the past.**

Canonical documentation is current-state authority, not an accumulated change log. A reader or agent must be able to learn the current contract without reconstructing a timeline inside the document.

## Current-state-only canonical documentation

A canonical document contains only the specification, contract, or repository practice that is currently valid at the repository HEAD.

When canonical content changes:

- replace the superseded content with the new current content;
- remove obsolete names, structures, examples, and implementation-state descriptions that are no longer part of the current contract;
- do not retain the previous rule merely to explain that it used to exist;
- do not add historical narration such as "previously", "formerly", "before this change", or "starting from this change" unless that history is itself required to understand the current contract;
- do not require the reader to perform temporal reasoning to determine which statement is authoritative.

The operational rule is:

> **Replace superseded semantics; do not accumulate them.**

A lifecycle change therefore updates the canonical document directly to its post-change state. Superseded content is removed rather than annotated as obsolete.

## Git owns document history

The repository's Git history is the normal record of how canonical documentation changed.

Use commits, diffs, blame, and pull-request history when the question is how a document evolved. Do not duplicate that evolution inside the canonical document solely for archival purposes.

This keeps two concerns separate:

```text
canonical document   what is true now
Git history          how the canonical document changed
```

A past version found through Git is historical evidence. It does not regain current authority merely because it was once canonical.

## Explicit historical artifacts

Some artifacts intentionally preserve history because the history itself is useful. They remain separate from canonical current-state authority.

Examples include:

- changelogs;
- release notes;
- migration guides;
- architecture decision records;
- deprecation notices with an active migration purpose;
- evaluation evidence;
- incident and investigation records.

These artifacts may explain what changed, why it changed, or how to move between versions. They must not become a second writer for the current semantic contract.

A durable decision record may explain why a constraint exists, but the current constraint still belongs in its owning canonical surface. An evaluation artifact may record what was observed, but it does not redefine the current product contract.

## Lifecycle roles

Documentation roles are intentionally distinct:

```text
Canonical Authority   current valid semantics and repository contracts
Git History           prior states and the sequence of changes
Historical Artifact   intentionally preserved rationale, migration, or evidence
Projection            derived view of canonical inputs, never an independent writer
```

When a document changes role, its authority classification must remain explicit. Historical or generated content must not be mistaken for current canonical authority.

## Review rule

A documentation change is canonically converged only when:

1. the owning canonical surface describes the post-change state directly;
2. superseded semantics are removed from that surface;
3. any history worth preserving is either already available through Git or stored in an explicitly historical artifact for a concrete reason;
4. derived or explanatory documents do not redefine the canonical source; and
5. no reader must compare old and new prose inside the canonical document to determine the current rule.

These rules apply to ordinary semantic and repository-documentation transactions unless a document is explicitly classified as a historical artifact.
