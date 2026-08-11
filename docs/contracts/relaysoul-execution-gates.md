---
relaylm_doc_type: contract
relaylm_authority: relaylm_execution_gate_decisions_and_dependencies
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: relaysoul
relaylm_update_trigger:
  - a gate scope is added, removed, or renamed
  - a gate decision artifact type or allowed flag changes
  - gate input dependencies or the required ready-gate ordering change
  - approval scope, freshness, or lineage dependency rules change
  - the content-free gate boundary changes
relaylm_not_authoritative_for:
  - current implementation completion
  - actual source mutation, rollback, storage writer, or persistence runtime implementation
  - current `mvp-soul-0` preflight producer code except where explicitly identified as current
  - portable identity and source semantics owned by architecture
  - exact approval artifact and lineage freshness field lists owned by their contracts
  - exact persistence artifact kinds, envelope, and ID extraction owned by the persistence contract
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../architecture/character/identity-and-source-authority.md
relaylm_related_contracts:
  - relaysoul_explicit_approval_artifact_contract.md
  - relaysoul_preflight_lineage_freshness_policy.md
  - relaysoul_persistence_contract.md
  - relaysoul_revision_contract.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelaySOUL execution-gate maintainers
  - RelaySOUL apply, rollback, storage, and persistence reviewers
  - SOUL Lab and RelaySOUL tooling maintainers
relaylm_authority_level: exact_contract
---
# RelaySOUL Execution Gate Contract

## Status and purpose

This is the normative **target** contract for the RelaySOUL execution-gate decision family: the exact gate scopes, decision artifact types, allowed flags, input dependencies, and fail-closed rules that must hold before any actual apply, rollback, storage write, or persistence execution.

No gate decision runtime exists. No gate decision artifact is currently emitted, and no gate CLI is implemented. Current implementation state remains owned by [Project Status](../PROJECT_STATUS.md); a target statement here never implies an implemented behavior.

The conceptual separation between portable-source authority and these execution gates is owned by [Character Identity and Source Authority](../architecture/character/identity-and-source-authority.md). This contract owns the exact decision family only.

## Gate scopes

Four gate scopes are distinct authorities. They are never merged, aliased, or substituted for one another:

```text
apply execution
  authorizes actual portable-source mutation

rollback execution
  authorizes actual reversal of an applied revision

storage writer
  authorizes actual artifact write and index append

persistence execution
  authorizes actual persistence of the governance artifact chain
```

## Decision artifacts and allowed flags

Each scope emits exactly one target decision artifact carrying exactly one gate-specific allowed flag:

```text
relaysoul_apply_execution_gate_decision        apply_execution_allowed
relaysoul_rollback_execution_gate_decision     rollback_execution_allowed
relaysoul_storage_writer_gate_decision         writer_execution_allowed
relaysoul_persistence_execution_gate_decision  persistence_execution_allowed
```

The persistence decision additionally carries `execution_preflight_type: apply | rollback`.

## Common decision posture

- `gate_status` is exactly one of `blocked` or `ready`;
- `content_free` is `true`;
- every allowed flag defaults to `false`;
- `true` remains future-only and requires a separate implementation authority to enable it;
- `blocking_reasons` must be empty for `ready`;
- `reasons`, `blocking_reasons`, and `warnings` are bounded metadata only;
- forbidden content keys must be absent at top level, in payloads, and in nested index records;
- unsafe identity is rejected;
- required identity, lineage, and path fields must agree across every referenced artifact;
- missing, invalid, stale, or mismatched input fails closed to `blocked`.

A `ready` decision is a readiness statement about the checked chain. It is not proof that execution occurred and not permission for a different scope.

## Approval and freshness dependencies

Every gate requires explicit approval that is gate-scoped, current, and fresh:

- approval must be explicit and bound to the exact target chain;
- approval scope must equal the gate being evaluated;
- approval for one gate never transfers to another gate;
- freshness is an independent requirement that approval never satisfies;
- approval is necessary but never sufficient by itself.

The exact approval artifact fields, approver kinds, and approval reason codes are owned by [RelaySOUL Explicit Approval Artifact Contract](relaysoul_explicit_approval_artifact_contract.md). The exact lineage fields, freshness checks, and stale conditions are owned by [RelaySOUL Preflight Lineage Freshness Policy](relaysoul_preflight_lineage_freshness_policy.md). This contract does not restate either field list.

## Gate dependency graph

### Apply execution gate

Requires:

- apply-scoped explicit approval;
- a current and fresh apply execution preflight;
- a matching apply plan and storage identity chain;
- rollback readiness must exist before actual apply is considered safe.

Rollback readiness is a precondition, not apply approval.

### Rollback execution gate

Requires:

- rollback-scoped explicit approval;
- a current and fresh rollback execution preflight;
- a matching rollback plan and the apply-plan lineage that it reverses.

Apply approval does not imply rollback approval. The rollback gate is independently approved.

### Storage writer gate

Requires:

- storage-writer-scoped explicit approval;
- a storage writer preflight;
- a matching storage envelope, path plan, and index identity, including `artifact_index_record` and `lineage_index_record` identity agreement with the path plan;
- a matching apply or rollback execution preflight;
- a persistence execution preflight that remains ready.

Writer readiness authorizes neither apply nor rollback.

### Persistence execution gate

Requires:

- persistence-scoped explicit approval;
- a current and fresh persistence execution preflight;
- a ready storage writer gate decision;
- a ready matching apply or rollback gate decision, selected by `execution_preflight_type`;
- `execution_preflight_type` must match the selected chain.

Persistence readiness is not equivalent to apply or rollback authorization.

### Ordering

```text
apply gate OR rollback gate  ->  storage writer gate  ->  persistence execution gate
```

A downstream gate never compensates for an upstream gate that is `blocked`, and an upstream `ready` never implies a downstream scope is authorized.

## Content boundary

Gate decisions carry exact content-free metadata only. They must not contain:

- persona or portable-source bodies;
- memory bodies, snippets, or page content;
- patch or revision bodies and patch text;
- prompt text;
- model request or response bodies;
- arbitrary protected calibration content.

A failed content-free assertion fails closed.

## Relationship to persistence

Storage envelope shape, supported artifact kinds, artifact and parent ID extraction, and current dry-run helper behavior are owned by [RelaySOUL Artifact Persistence Contract](relaysoul_persistence_contract.md). This contract references those identities without redefining them.

## Non-goals

- gate decision runtime implementation;
- gate dry-run CLI implementation or proposed script names;
- actual apply, rollback, storage write, index append, or directory creation;
- approval UI or authentication implementation;
- freshness timestamp trust or signature implementation;
- current `mvp-soul-0` wire or compatibility changes;
- runtime behavior change of any kind.
