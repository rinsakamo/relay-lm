# RelayMEM SLP Execution Design

## Purpose

RelaySLP is RelayLM's deferred memory and knowledge compilation path.

It reads governed evidence, extracts memory candidates, classifies safety, merges or holds candidates, lints memory, updates indexes/logs through explicit gates, and emits RelaySOUL proposal candidates when needed.

RelaySLP improves future memory. It does not produce the current answer.

Current implementation phase and sequencing live in [Pipeline Implementation Plan](pipeline_implementation_plan.md) and [Project Status](../PROJECT_STATUS.md).

## Core principle

```text
RelayMEM Retrieval
  synchronous and read-only for the current answer

RelaySLP
  deferred and write-capable only through persistence gates

RelayREF
  separate post-generation output observer
```

RelaySLP is not RelayREF and must not replace RelayINT clarification or RelaySCN recovery.

## Inputs

RelaySLP consumes governed evidence rather than arbitrary runtime dumps:

- approved raw event references,
- explicit user memory requests,
- detached RelayCTX Unpack/update candidates after validation,
- RelayINT intent/clarification summaries,
- RelaySCN state/policy summaries,
- RelayRUN checkpoint and recovery metadata,
- RelayMEM retrieval summaries,
- existing MEM pages/index/log,
- approved RelaySOUL constraints,
- user-approved memory records.

Content-bearing source material remains in the protected memory/source domain. Default runtime trace projections are not sufficient SLP source data by themselves.

## Outputs

RelaySLP may produce:

- memory candidates,
- proposed page updates,
- held or rejected candidates,
- relation updates,
- lint findings,
- index/log update plans,
- applied page/index/log updates when gates pass,
- RelaySOUL proposal candidates,
- content-free operation projections.

RelaySLP never emits user-visible answer, sleep, recovery, or resume text directly.

## Execution flow

```text
governed source append/reference
  -> candidate extraction
  -> memory_kind classification
  -> safety_scope classification
  -> existing MEM lookup
  -> merge / update / hold / reject
  -> relation typing
  -> lint
  -> persistence preflight
  -> RelaySCN / approval / idempotency gates
  -> page/index/log apply or held plan
  -> optional RelaySOUL proposal candidate
```

## Candidate extraction

Candidate examples:

- project state update,
- concept definition,
- design decision,
- user workflow preference,
- claim or contradiction,
- relation between concepts,
- stale/superseded record,
- RelaySOUL proposal candidate.

Extraction does not authorize persistence.

## `memory_kind`

Recommended initial kinds:

```text
raw_event
session_summary
project_state
concept
claim
preference
relation
soul_candidate
rejected_or_blocked_candidate
```

## `safety_scope`

### `free_to_update`

May be applied only when all other gates pass.

### `review_required`

Held for user/operator review.

### `explicit_approval_required`

Converted into an approval artifact or RelaySOUL proposal candidate. Never auto-applied.

### `never_auto_promote`

Rejected, blocked, or retained only as protected source evidence.

Raw affect estimates, transient emotional inference, sensitive-attribute inference, and low-confidence personal inference belong here.

## Existing-page decision

Possible outcomes:

```text
create_page
update_page
append_claim
merge_duplicate
mark_stale
add_relation
hold_for_review
propose_soul_update
reject
no_change
```

Every apply decision should be deterministic or idempotency-protected.

## Relation typing

Useful relation types:

```text
supports
contradicts
refines
supersedes
depends_on
part_of
example_of
risk_for
derived_from
candidate_for_soul
blocked_from_soul
```

## Lint

RelaySLP lint checks:

- duplicate concepts,
- alias/identity splits,
- stale or superseded claims,
- unresolved contradictions,
- orphan pages,
- missing source lineage,
- untyped relation overuse,
- unsafe promotion candidates,
- low-confidence personal inference,
- namespace leakage,
- non-idempotent update plans.

## Trigger modes

### Explicit/manual SLP

Triggered by an explicit request to remember, organize, consolidate, document, forget, or review memory.

### Turn-end deferred SLP

Runs after the normal response path and produces candidates or diagnostics without delaying first response/streaming.

### Scheduled/background SLP

May run under an operator-defined schedule when the runtime supports it. Scheduling is an orchestration concern; RelaySLP responsibility remains the same.

### Forced SLP/reanchor preparation

A rare deferred path used after repeated structured-update failure, repeated contradiction, critical context pressure, or repeated inability to determine a safe continuation.

A single ambiguous reference, one failed retrieval, or moderate token pressure is insufficient.

Do not use `Wake`, `Sleep`, or `Reflection` as formal component names. User-facing metaphors may exist in product presentation, but the technical contracts are normal-turn execution, deferred SLP, recovery, waiting-user, and reanchor.

## Clarification and recovery boundary

```text
ordinary ambiguous reference
  -> RelayINT clarification
  -> optional user confirmation
  -> RelayMEM Retrieval only after explicit/confirmed scope

confusion / contradiction / task loss
  -> RelaySCN recovery policy
  -> RelayRUN waiting-user/recovery orchestration
  -> persistence blocked
```

RelaySLP may inspect the resulting governed artifacts later. It must not replace clarification or recovery with an automatic write.

## Persistence preconditions

Persistence must be blocked when:

- RelaySCN policy blocks persistence,
- scene is recovery, medical/safety, or formal-document under the active policy,
- user confirmation is required,
- candidate confidence/stability is insufficient,
- contradiction remains unresolved,
- source lineage is absent,
- namespace scope is invalid,
- the candidate requires review or explicit approval,
- idempotency/revision preconditions fail,
- the proposed write would mutate RelaySOUL directly.

Threshold values belong in configuration and tests rather than duplicated architecture defaults.

## RelaySOUL proposal boundary

```text
RelaySLP durable-persona candidate
  -> candidate classification
  -> RelaySCN proposal eligibility
  -> explicit user/operator approval
  -> RelaySOUL patch candidate
  -> RelaySOUL compile/budget/safety validation
  -> approved revision/persistence/rollback path
```

RelaySLP never writes RelaySOUL files directly.

## Runtime-private artifact

A runtime/SLP-private artifact may contain content-bearing fields:

```yaml
relaymem_slp_runtime:
  mode: deferred_dry_run
  source_refs:
    - source:session:123
  candidates:
    - candidate_id: memcand:1
      memory_kind: project_state
      normalized_value: "..."
      target_page: projects/relaylm
      safety_scope: free_to_update
      confidence: 0.91
      proposed_action: update_page
  held_candidates: []
  proposed_page_updates:
    - page_id: projects/relaylm
      patch: "..."
```

This artifact belongs to the protected memory compiler domain. It must not be copied recursively into runtime trace/audit records.

## Content-free SLP projection

Default operational projections may contain only typed allowlisted fields:

```yaml
relaymem_slp_projection:
  schema_version: relaymem.slp_projection.v1
  mode: deferred_dry_run
  source_count: 1
  candidate_count: 1
  create_count: 0
  update_count: 1
  hold_count: 0
  reject_count: 0
  soul_proposal_count: 0
  contradiction_count: 0
  persistence_attempted: false
  persistence_applied: false
  blocked_reason_ids:
    - dry_run_only
```

Default projections must not contain:

- raw messages,
- candidate normalized values,
- titles/summaries/snippets,
- page bodies or patches,
- filesystem paths,
- scene/intent semantic text,
- visible response text.

Memory-specific audit logs may store approved page IDs and lineage references under separate access/retention policy, but they are not the default runtime trace.

## Apply semantics

When apply is enabled and all gates pass:

- apply only allowed candidate scopes,
- use revision/idempotency checks,
- preserve original evidence and lineage,
- update index/log consistently,
- prevent duplicate writes on retry/resume,
- emit a content-free apply projection,
- keep visible response delivery independent from persistence success.

## Failure behavior

SLP failure must not invalidate an already valid visible response.

```text
candidate extraction failure
  -> no apply
  -> content-free blocked projection

page/index/log apply failure
  -> preserve previous durable state
  -> record failed/partial state
  -> retry only under idempotency rules

RelaySOUL proposal failure
  -> no SOUL mutation
  -> hold/reject candidate
```

## Non-goals

RelaySLP does not:

- answer the current request,
- run inside latency-critical Retrieval,
- replace RelayINT clarification,
- replace RelaySCN recovery,
- inspect output as RelayREF,
- generate user-visible recovery/sleep text,
- auto-apply review-required or approval-required candidates,
- directly mutate RelaySOUL,
- persist raw affect estimates as durable facts,
- expose content-bearing candidates through default trace projections.

## Summary

```text
governed evidence
  -> RelaySLP candidate extraction
  -> safety/scope/lineage classification
  -> merge / hold / reject / proposal
  -> gated idempotent MEM apply
  -> separate RelaySOUL proposal path when approved
```
