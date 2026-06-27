---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase_i7ab_held_apply_discard_contract_and_read_only_preflight
relaylm_status: i7ab_contract_preflight_complete_after_pr
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - I-7 Apply runtime lands
  - I-7 Discard runtime lands
  - SOUL Lab held-governance mutation API or UI lands
  - held outcome producer schema changes
relaylm_related_authority:
  - phase_i3_auditable_primary_mem_correct.md
  - phase_i4_primary_mem_forget_hide_contract.md
  - phase_i4b_primary_current_state_shared_fence.md
  - phase_i4d_primary_retrieval_exclusion.md
  - phase_i5_pin_unpin_contract.md
  - phase6b3_relayslp_queue_state_helpers.md
  - phase6c1_primary_mem_worker_contract.md
  - project_execution_plan.md
---
# Phase I-7A/B Held Apply / Discard Contract and Read-Only Preflight

## Status and boundary

I-7A/B defines the held outcome governance contract and adds a runtime read-only preflight boundary for future Apply and Discard decisions. It is contract/preflight only.

I-7A/B does **not** implement Apply. It does **not** implement Discard. It does not mutate B3 queue state or Primary MEM. It does not start workers or scheduler rounds. It does not add SOUL Lab mutation UI. A later I-7 apply/discard runtime slice will own mutation if adopted.

The bounded I-7A/B path is:

```text
select one held operation/outcome candidate
  -> resolve character/namespace/scope
  -> validate held status and source authority
  -> validate current related Primary MEM state, if any
  -> compute Apply preflight
  -> compute Discard preflight
  -> bounded content-free operation projection
  -> no apply/discard mutation
```

## Canonical terminology

- **held outcome**: a runtime-private operation or worker outcome that stopped for human judgment rather than automatic retry, terminal failure, corruption recovery, or success.
- **Apply candidate**: a held outcome that could later be adopted by a future mutation slice. I-7A/B only reports that it is apply-governable.
- **Discard candidate**: the same held outcome viewed through the future discard decision path. I-7A/B only reports that it is discard-governable.
- **source evidence**: runtime-private authoritative evidence proving where the held outcome came from. I-7A/B validates presence, digest shape, and authority but does not expose source payload content.
- **related Primary MEM**: an optional current Primary MEM whose lifecycle must remain safe before a held outcome can be considered governable.

## Held / blocked / failed / recovery / corrupt / terminal distinctions

I-7A/B treats only `held` as governable.

```text
held:
  human judgment pending; Apply and Discard preflight may return ready.

blocked:
  policy or prerequisite stopped the operation before held governance; not governable here.

failed:
  non-held failure outcome; future handling belongs to failure/retry/recovery authorities.

recovery_required:
  recovery authority must resolve state before governance.

corrupt:
  evidence or related state is unsafe; fail closed.

terminal_succeeded / terminal_failed:
  immutable terminal outcome; Apply/Discard preflight is blocked.

applied / discarded:
  already governed; preflight returns an idempotent content-free blocked projection.
```

B3 queue terminal states are also immutable for this boundary:

```text
succeeded -> queue_terminal_succeeded
failed -> queue_terminal_failed
cancelled -> queue_terminal_cancelled
dead_letter -> queue_terminal_dead_letter
```

Queued or claimed B3 records are evidence only. I-7A/B never calls B3 transition helpers, never writes queue files, and never performs retry release or terminal commit.

## Minimal runtime-private candidate schema

I-7A/B introduces this schema anchor:

```text
relaylm.mem.held_outcome_candidate.v0
```

The minimal runtime-private shape is:

```text
schema_version = relaylm.mem.held_outcome_candidate.v0
runtime_private = true
content_included = false
candidate_id
operation_id
character_id
namespace
scope
status
queue_state = queued | claimed | succeeded | failed | cancelled | dead_letter | null
source_authority = primary_worker_outcome | governance_flow | operator_import
source_evidence_digest
source_evidence_present
source_evidence_corrupt
source_evidence_ambiguous
source_content_included = false
related_primary_memory_id = sha256 | null
related_primary_expected_revision = int | null
related_primary_physical_id = sha256 | null
```

The schema intentionally carries only identifiers, state labels, source-reference metadata, and digest-level evidence. It must not include held candidate body text, user text, model output text, memory candidate text, protected source body, queue payload body, Primary page body, or source file paths.

## Source evidence separation

Source evidence is runtime-private. Public projections include reason codes and bounded metadata only.

```text
runtime-private evidence:
  source authority
  source evidence digest
  source present/corrupt/ambiguous flags
  related Primary current-state reread result

public projection:
  status
  action
  candidate id
  operation id
  character id
  namespace
  scope
  candidate status
  queue state
  related memory id
  reason code
  blocked reason ids
  effect flags
  content-free flags
```

Public projection must report:

```text
content_free = true
runtime_private_evidence_omitted = true
source_body_included = false
model_output_included = false
memory_content_included = false
queue_payload_included = false
primary_page_path_included = false
```

## Preflight response schemas

Apply preflight:

```text
relaylm.lab.held_apply_preflight.v0
```

Discard preflight:

```text
relaylm.lab.held_discard_preflight.v0
```

Both return the same bounded shape with different `action` and effect contract flags:

```text
schema_version
status = ready | blocked | safe_failure | invalid_input
action = apply | discard
read_only = true
candidate_id
operation_id
character_id
namespace
scope
candidate_status
queue_state
related_memory_id
related_memory_checked
reason_code
blocked_reason_ids
effects
content-free flags
```

Apply effect preview:

```text
held_item_adopted_contract = true
held_item_discarded_contract = false
queue_state_mutated = false
primary_mem_mutated = false
worker_started = false
scheduler_started = false
automatic_retry_or_release = false
runtime_private_content_exposed = false
```

Discard effect preview:

```text
held_item_adopted_contract = false
held_item_discarded_contract = true
queue_state_mutated = false
primary_mem_mutated = false
worker_started = false
scheduler_started = false
automatic_retry_or_release = false
runtime_private_content_exposed = false
```

These are contract previews only. They do not persist governance state.

## Related Primary MEM current-state validation

When `related_primary_memory_id` is present, I-7A/B rereads the related Primary MEM through the existing Primary current-state resolver. It does not duplicate I-4 lifecycle authority and does not weaken existing exclusion/fence behavior.

Safe failure outcomes include:

```text
related_primary_store_root_required
related_primary_store_unavailable
related_primary_not_found
related_primary_hidden
related_primary_prepared
related_primary_recovery_required
related_primary_corrupt
related_primary_prior
related_primary_not_retrieval_eligible
```

A hidden related Primary MEM remains excluded from governance. Prepared, recovery-required, corrupt, ambiguous, prior, stale, or non-current state fails closed.

## Authority preservation

I-7A/B preserves these authorities:

- B3 remains the only durable queue lifecycle transition authority.
- C1/C2 remain the only worker execution and outcome-production authorities.
- I-4 remains the lifecycle exclusion and Primary mutation fence authority.
- O1 remains the scheduler lane/round authority.
- RelayMEM current-state resolver remains the related Primary reread authority.

The I-7A/B helper never invokes queue transition helpers, C2 worker adapters, O1 scheduler rounds, Primary page writers, Primary index/log reconciliation, Forget/Pin/Correct apply helpers, or SOUL Lab mutation APIs.

## Later apply/discard runtime handoff

A later I-7 runtime slice may implement Apply and Discard only if it preserves this contract:

- accept only a previously governable held candidate;
- reread source evidence through its owning authority;
- reread related Primary current state through the existing resolver;
- use existing mutation fences where Primary mutation is involved;
- write runtime-private audit evidence without semantic content leakage;
- use B3 transitions only through B3 authority if queue state must change;
- keep Apply and Discard idempotent under already-applied/already-discarded evidence;
- never start workers, schedulers, or retry loops implicitly from preflight.

## Non-goals

I-7A/B explicitly does not implement Apply runtime, Discard runtime, B3 queue mutation, Primary MEM page/index/log writes, protected source body reads for projection, C2 worker invocation, automatic retry/release, terminal commits, daemon/polling/scheduler services, SOUL Lab Apply/Discard buttons, or shared current-status documentation updates.
