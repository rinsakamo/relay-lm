---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase_i7ab_held_apply_discard_contract_and_read_only_preflight
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - I-7 Apply runtime changes
  - I-7 Discard runtime changes
  - SOUL Lab held-governance mutation API or UI changes
  - held outcome producer schema changes
relaylm_related_authority:
  - phase_i3_auditable_primary_mem_correct.md
  - phase_i4_primary_mem_forget_hide_contract.md
  - phase_i4b_primary_current_state_shared_fence.md
  - phase_i4d_primary_retrieval_exclusion.md
  - phase_i7c_held_apply_discard_runtime.md
  - phase6b3_relayslp_queue_state_helpers.md
  - project_execution_plan.md
---
# Phase I-7A/B Held Apply / Discard Contract and Read-Only Preflight

## Status and boundary

I-7A/B defines the held outcome governance contract and read-only preflight boundary. I-7C is implemented as the runtime/API/UI/durable-evidence continuation. The current runtime decision path lives in [Phase I-7C Held Apply / Discard Runtime](phase_i7c_held_apply_discard_runtime.md).

I-7A/B itself remains the governability preflight authority:

```text
select one held operation/outcome candidate
  -> resolve character/namespace/scope
  -> validate held status and source authority
  -> validate current related Primary MEM state, if any
  -> compute Apply preflight
  -> compute Discard preflight
  -> bounded content-free operation projection
  -> no apply/discard mutation in I-7A/B
```

I-7C consumes this contract to persist one content-free Apply or Discard decision over an already-held candidate and expose the explicit loopback API/UI flow.

## Canonical terminology

- **held outcome**: runtime-private operation or worker outcome that stopped for human judgment rather than automatic retry, terminal failure, corruption recovery, or success.
- **Apply candidate**: a held outcome that can be adopted by the I-7C mutation slice when governability remains ready.
- **Discard candidate**: the same held outcome viewed through the I-7C discard decision path.
- **source evidence**: runtime-private authoritative evidence proving where the held outcome came from.
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

B3 queue terminal states are immutable for this boundary. Queued or claimed B3 records are evidence only. I-7A/B never calls B3 transition helpers, writes queue files, or performs retry release or terminal commit.

## Minimal runtime-private candidate schema

I-7A/B introduces this schema anchor:

```text
relaylm.mem.held_outcome_candidate.v0
```

The minimal runtime-private shape carries only identifiers, state labels, source-reference metadata, and digest-level evidence. It must not include held candidate body text, user text, model output text, memory candidate text, protected source body, queue payload body, Primary page body, or source file paths.

## Preflight response schemas

Apply preflight:

```text
relaylm.lab.held_apply_preflight.v0
```

Discard preflight:

```text
relaylm.lab.held_discard_preflight.v0
```

Both return bounded shapes with action, status, candidate identifiers, current related Primary state summary, effect flags, and explicit content-free flags.

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

I-7A/B and I-7C preserve these authorities:

- B3 remains the only durable queue lifecycle transition authority.
- C1/C2 remain the only worker execution and outcome-production authorities.
- I-4 remains the lifecycle exclusion and Primary mutation fence authority.
- O1 remains the scheduler lane/round authority.
- RelayMEM current-state resolver remains the related Primary reread authority.

The I-7A/B helper never invokes queue transition helpers, C2 worker adapters, O1 scheduler rounds, Primary page writers, Primary index/log reconciliation, Forget/Pin/Correct apply helpers, or SOUL Lab mutation APIs.

## I-7C runtime continuation

I-7C preserves this contract by:

- accepting only a previously governable held candidate;
- rereading source evidence through its owning authority;
- rereading related Primary current state through the existing resolver;
- using existing mutation fences where Primary mutation is involved;
- writing runtime-private audit evidence without semantic content leakage;
- keeping Apply and Discard idempotent under already-applied/already-discarded evidence;
- never starting workers, schedulers, or retry loops implicitly from preflight or UI.

## Non-goals

I-7A/B/I-7C do not implement worker start, scheduler start, automatic retry/release loops, O1 scheduler invocation, C2 worker invocation from UI, new B3 lifecycle authority, direct queue file rewrite, Pin/Unpin runtime apply, Forget restore/unhide/purge, Secondary MEM consolidation, RelaySOUL mutation, service supervision, daemonization, polling, or source/body display.
