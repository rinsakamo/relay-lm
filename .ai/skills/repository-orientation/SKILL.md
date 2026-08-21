---
schema_version: 1
id: repository-orientation
responsibility: Resolve fresh repository state, the semantic owner, required current authority, and competing work before a RelayLM v1 task proceeds.
mode: read_only
when_to_use:
  - At the start of a new RelayLM v1 task or bounded transaction.
  - After a merge, external repository change, or handoff when authority must be reconstructed.
  - When the task's semantic owner or competing work is not yet established.
when_not_to_use:
  - To modify code, tests, documentation, Issues, pull requests, branches, or repository settings.
  - To define product semantics, workflow policy, freshness classes, defaults, or release requirements.
required_authority:
  - .ai/README.md
  - .ai/agent-contract.yaml
  - docs/reference/development-workflow.md
required_live_facts:
  - repository_head
  - open_pull_requests
authorization:
  writes: prohibited
---

# Repository orientation

This skill is a repository-native procedure, not a semantic authority. Apply the current repository authority it points to; do not copy or replace that authority here.

## Procedure

1. Read `.ai/README.md` and `.ai/agent-contract.yaml` first. Follow the bootstrap order declared by the current agent contract.
2. Re-fetch the current `v1` HEAD and open pull requests targeting `v1`. Treat any SHA, PR state, CI state, Issue state, or projection supplied by a handoff as historical unless current authority explicitly says otherwise.
3. Classify the requested work by semantic responsibility. Locate the matching declaration under `.ai/authority/` and confirm that no open transaction is already writing the same semantic owner or unavoidable shared write surface.
4. Read that owner's current canonical surfaces. Load only dependencies, evidence, annotations, or external sources that can materially change the decision.
5. When a decision depends on mutable behavior outside the repository, apply the `upstream` freshness class from `.ai/agent-contract.yaml`: verify the current primary upstream source at material use rather than relying on remembered behavior or a secondary summary.
6. Classify the intended transaction before any write: semantic change, behavior-preserving implementation, documentation/repository-only change, evidence execution, or another class already defined by current workflow authority.
7. Produce a concise orientation record for the next procedure or implementing agent. The record is working state only and becomes historical at the next transaction boundary.

Recommended record shape:

```text
repository_head:
open_v1_prs:
semantic_owner:
canonical_surfaces:
required_dependencies:
required_evidence:
upstream_claims_to_verify:
competing_work:
transaction_class:
stop_reason:
```

Do not infer missing authority from old PR bodies, Issue summaries, projections, or handoff text.

## Verification

Before declaring orientation complete, verify all of the following against current authority:

- the reported repository head was fetched live for this orientation;
- the open-PR set was fetched live for this orientation;
- the semantic owner is uniquely resolved or the ambiguity is reported as a stop condition;
- selected canonical surfaces come from the current owner declaration;
- no unmerged assumption from another transaction is being consumed as current authority;
- every material mutable external claim is either verified from current upstream authority or explicitly listed as unresolved;
- no repository write was performed by this skill.

## Stop conditions

Stop orientation and report the exact unresolved boundary when any of these is true:

- semantic ownership is ambiguous or no current owner exists for a semantic change;
- another open transaction is writing the same semantic owner, semantic contract, or unavoidable shared write surface;
- a required live repository fact cannot be fetched reliably;
- a material upstream claim cannot be verified from an appropriate current source;
- the requested task crosses semantic owners and cannot be decomposed without a cross-owner decision;
- current repository authority conflicts internally in a way that affects the requested task.

A stop condition is not permission to invent a temporary owner, bridge, fallback, or duplicate semantic rule.

## Authorization

This skill is read-only. It does not authorize creating or updating branches, files, commits, pull requests, Issues, reviews, workflow runs, tags, releases, repository settings, or external resources.

If the task requires a write, finish orientation and then follow the current development workflow or another separately materialized procedure whose write responsibility matches the task. The existence of this skill does not imply that any other planned repository-native skill has been materialized.
