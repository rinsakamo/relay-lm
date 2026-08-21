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

## Git owns ordinary document history

The repository's Git history is the normal record of how canonical documentation changed.

Use commits, diffs, blame, and pull-request history when the question is how a document evolved. Do not duplicate that evolution inside the canonical document solely for archival purposes.

This keeps two concerns separate:

```text
canonical document   what is true now
Git history          how the canonical document changed
```

A past version found through Git is a historical record. It is not current authority merely because it was once canonical.

## Explicit historical artifacts

Some artifacts intentionally preserve history because the history itself is useful. They remain separate from canonical current-state authority.

Examples include:

- changelogs;
- release notes;
- migration guides;
- architecture decision records;
- historical deprecation rationale or migration records;
- evaluation evidence;
- incident and investigation records.

These artifacts may explain what changed, why it changed, how to move between versions, or what was observed at a particular point in time. They must not become a second writer for the current product or repository contract.

A durable decision record may explain why a constraint exists, but the current constraint still belongs in its owning canonical surface. An evaluation artifact may be authoritative for the evidence it records, but it does not redefine the current product contract.

An active deprecation is current state, not history. If a public or external-facing contract currently declares something deprecated, including its current support or removal conditions, that declaration belongs in the owning canonical surface. Historical rationale and migration narrative may live in a separate historical artifact when useful.

## Non-authoritative artifacts do not create semantics

An artifact that is not declared as a canonical or evidence surface may reference, explain, propose, or illustrate repository semantics, but it does not create current authority by itself.

This includes, unless explicitly promoted through the owning authority transaction:

- Issues and Issue comments;
- pull-request bodies and review discussion;
- handoff prompts and conversation summaries;
- projections and generated views;
- annotations and explanatory notes;
- examples and sample values.

If one of these artifacts introduces a semantic rule that must become current, the rule is incomplete until it is represented in the owning canonical surface and the normal transaction gate succeeds.

Evidence is a distinct authority class: an owned evidence artifact may be authoritative for what was measured or observed, while still being non-authoritative for product semantics outside that evidence claim.

## Examples illustrate; contracts define

Examples demonstrate an intended or valid case. They do not independently define semantics, defaults, limits, compatibility guarantees, or requirements unless the owning canonical contract explicitly designates that example or value as normative.

An Issue or bounded specification may use examples to state transaction intent before merge. Those examples guide tests and implementation, but they do not become repository authority merely by appearing in the Issue, PR, test fixture, or documentation example.

This rule prevents incidental sample values from becoming accidental defaults or limits.

## Document retirement

Deletion is a first-class documentation maintenance operation.

A document that no longer has a current role as canonical authority, a necessary reference, a defined projection, or an explicit historical artifact is deleted rather than retained as an informal archive.

Do not create archive directories merely to avoid deletion. Preserve material outside current authority only when its historical role is explicit and useful.

Removing a document does not erase its ordinary history; the removed content remains available through Git history.

## Lifecycle roles

Documentation roles are intentionally distinct:

```text
Canonical Authority   current valid semantics and repository contracts
Evidence              owned observations or measurements within their evidence claim
Git History           prior repository states and the sequence of changes
Historical Artifact   intentionally preserved rationale, migration, or historical record
Projection            derived view of canonical inputs, never an independent writer
```

When a document changes role, its authority classification must remain explicit. Historical, generated, illustrative, or explanatory content must not be mistaken for current canonical authority.

## Review rule

A documentation change is canonically converged only when:

1. the owning canonical surface describes the post-change state directly;
2. superseded semantics are removed from that surface;
3. any history worth preserving is either already available through Git or stored in an explicitly historical artifact for a concrete reason;
4. active deprecations remain in current canonical authority while historical rationale is separated when needed;
5. non-authoritative artifacts and examples do not introduce independent normative semantics;
6. documents with no remaining current or explicit historical role are deleted; and
7. no reader must compare old and new prose inside the canonical document to determine the current rule.

These rules apply to ordinary semantic and repository-documentation transactions unless an artifact has a separately declared authority role.
