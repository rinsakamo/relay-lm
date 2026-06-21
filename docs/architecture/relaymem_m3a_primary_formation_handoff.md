---
relaylm_doc_type: implementation_handoff
relaylm_authority: relaymem_mvp_independent_track
relaylm_status: historical_after_merge
relaylm_volatility: medium
relaylm_owner: relaymem
relaylm_update_trigger:
  - RelayMEM M3 primary formation boundary changes
  - Primary MEM candidate schema producer or consumer changes
  - Primary MEM write preflight or apply gates land
relaylm_not_authoritative_for:
  - repository-wide Phase 5.5 Stream Unpack sequencing
  - RelayCTX stream/TTS adapter behavior
  - exact runtime config defaults outside RelayMEM-M3
  - current repository-wide implementation status
relaylm_related_authority:
  - relaymem_mvp_implementation_plan.md
  - memory_lifecycle_design.md
  - relaymem_mvp_design.md
  - ../PROJECT_STATUS.md
---
# RelayMEM-M3a Primary Formation Handoff

## Status

RelayMEM-M3a is complete as a helper-only Primary MEM formation candidate boundary.

This handoff is historical evidence for the completed bounded slice. Current repository-wide status remains owned by `../PROJECT_STATUS.md`, and RelayMEM-M sequencing remains owned by `relaymem_mvp_implementation_plan.md`.

The completed slice adds a pure dry-run helper that can classify governed experience evidence into Primary MEM / Experience MEM candidates without writing memory or changing runtime behavior.

## Completed boundary

M3a provides:

- `relaylm.relaymem_primary_formation.build_relaymem_primary_formation_dry_run`,
- content-free Primary MEM candidate metadata,
- bounded RelaySCN scene and persistence-policy consumption,
- bounded RelayEMO salience-band consumption,
- message-shape source summaries without raw text,
- ordinary `free_to_update` candidate classification,
- `review_required` held candidate classification,
- fail-closed handling for malformed RelaySCN policy artifacts,
- persistence blocking for recovery, formal-document, and medical/safety scenes,
- NaN / Infinity rejection before salience or stability banding.

The public projection exposes only bounded booleans, counts, enums, bands, status values, and reason IDs.

## Preserved non-goals

M3a does not:

- wire into request runtime,
- write Primary MEM pages,
- update memory indexes or logs,
- invoke RelaySLP,
- mutate RelaySOUL,
- expose SOUL Lab APIs,
- persist raw message text,
- persist raw affect estimates,
- treat affect estimates as durable facts,
- change visible response delivery.

## Validation added

M3a adds smoke coverage for:

- ordinary free-to-update Primary MEM candidates,
- disabled helper behavior,
- medical/safety persistence blocking,
- held `system_ops` candidates,
- malformed RelaySCN fail-closed behavior,
- non-finite RelayEMO / RelaySCN numeric inputs.

The smoke command is:

```bash
python scripts/relaylm_relaymem_primary_formation_dry_run_smoke.py
```

## Next implementation boundary: MEM-M3b

The next RelayMEM-M3 slice should be a Primary MEM write-preflight boundary.

M3b should first add or pass a content-free source-lineage artifact into M3a candidate output or the M3b preflight input. Only after that lineage exists should M3b derive idempotency keys or apply eligibility. The current M3a candidates intentionally expose only a fixed candidate ID, event kind, bands, policy enums, and message-shape counts; those fields are not sufficient to build collision-safe idempotency keys for distinct turns.

Recommended M3b scope:

- define the minimal content-free source-lineage input required for Primary MEM write preflight,
- reject candidates when required lineage is missing or malformed,
- derive a deterministic idempotency key only after lineage is present,
- derive a bounded target namespace/path category without writing files,
- block `review_required`, `explicit_approval_required`, and `never_auto_promote` from autonomous apply,
- allow only `free_to_update` candidates to become apply-eligible when explicit gates pass,
- preserve dry-run-only behavior by default,
- emit content-free operation projections,
- avoid RelaySOUL mutation, RelaySLP invocation, Lab API exposure, and visible response mutation.

M3b should not yet implement durable Primary MEM writes unless that apply gate is explicitly made the bounded slice. If write apply is introduced later, it must be idempotent, namespace-scoped, rollback-friendly, and covered by smoke tests.

## Safety invariants carried forward

Future M3 work must preserve:

```text
ordinary governed experience evidence
  -> Primary MEM candidate
  -> content-free source lineage
  -> write preflight / operation artifact
  -> gated idempotent apply only when explicitly enabled
```

and must continue to block:

```text
raw user/model text in public projections
raw affect estimates as durable facts
recovery/formal-document/medical-safety autonomous persistence
Primary MEM overriding Secondary MEM or SOUL
unbounded memory writes
```
