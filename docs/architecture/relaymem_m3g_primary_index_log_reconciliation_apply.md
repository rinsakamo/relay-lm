---
relaylm_doc_type: implementation_handoff
relaylm_authority: relaymem_mvp_independent_track
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem
relaylm_update_trigger:
  - M3f reconciliation plan schema changes
  - M3g receipt or apply semantics change
  - M3h recovery-audit semantics change
  - journaled recovery or repair apply lands
  - RT-1 Primary writer-decision carriage changes which production calls may reach M3g
  - RT-1D-R5 or R6 retires the Primary writer path
relaylm_not_authoritative_for:
  - Phase 6 queue, dispatch, worker, or retry orchestration
  - request-runtime wiring
  - RT-1 cutover state, Primary writer authorization, or retirement approval
  - Secondary MEM consolidation
  - repository-wide implementation status
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - relaymem_m3f_primary_index_log_reconciliation_preflight.md
  - relaymem_m3e_atomic_primary_page_writer.md
  - relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md
  - memory/formation.md
  - subjective-mem-retrieval-projection-hard-cutover.md
  - project_execution_plan.md
  - relaymem_mvp_design.md
  - memory_lifecycle_design.md
  - relaymem_slp_current_target.md
  - ../PROJECT_STATUS.md
---
# RelayMEM-M3g Primary MEM Index/Log Reconciliation Apply

Last reviewed: 2026-08-08 JST

## Status

RelayMEM-M3g remains implemented as a default-off, dry-run-first, helper-only apply boundary that consumes one exact M3f reconciliation plan and converges `memory/mem/index.md` and `memory/mem/log.md` to the planned state.

```text
exact M3f runtime-private plan
  + revalidated durable Primary MEM page
  + current bounded index/log state
  -> index apply first
  -> log apply second
  -> runtime-private receipt
  -> content-free public projection
```

M3g performs actual index/log writes only when all three local helper gates are exact booleans and the effective request is:

```text
enabled=true
dry_run_only=false
apply_enabled=true
```

The default path performs validation and inspection only.

Under RT-1D-R4, M3g is a retained Primary compatibility mutation component below the exact C1-1 Primary writer-decision gate. Production compose rejects a non-permitted writer decision before any M3a-M3h stage, so a normal production invocation can reach M3g only after that upstream admission has succeeded.

M3g itself does not accept, resolve, cache, refresh, or reconstruct the RT-1 writer decision. Its local apply gates, an exact M3f `plan_ready` artifact, control-file state, idempotent no-op, writer-lock acquisition, or retry/resume state cannot grant or preserve Primary writer authority.

M3h recovery audit is now implemented downstream as a read-only classifier. No general journaled recovery/repair apply is implied by M3g or M3h. R5/R6 own final retirement or explicitly retained historical/test disposition of this Primary reconciliation apply surface.

## Production authorization boundary

The current retained compatibility hierarchy is:

```text
exact RT-1 Primary writer decision
  -> rejected: C1-1 stops before M3a-M3h
  -> permitted:
       M3a -> M3b -> M3c -> M3d -> M3e -> M3f
       -> M3g reconciliation apply          mutation
       -> M3h recovery audit                read-only
```

The writer decision is semantic production authorization owned above M3g. M3g owns only the bounded filesystem mutation mechanics for an already-admitted pipeline invocation.

Direct M3g helper tests may exercise apply, contention, failure, and resume semantics through the helper's explicit local gates. Such tests prove the M3g contract; they are not a second production cutover path and do not show that local gates or lock ownership can bypass `primary_writer_fenced`.

## Public helper

```python
apply_relaymem_primary_index_log_reconciliation(
    plan_artifact=...,
    root_path=...,
    enabled=False,
    dry_run_only=True,
    apply_enabled=False,
)
```

Schemas:

```text
relaymem.primary_index_log_reconciliation_apply.v0
relaymem.primary_index_log_reconciliation_receipt.v0
relaymem.primary_index_log_reconciliation_apply_projection.v0
```

The local `enabled`, `dry_run_only`, and `apply_enabled` values select M3g helper behavior only. They are necessary mutation-mechanics gates for a direct apply call, not RT-1 writer authorization.

## Exact M3f plan validation

M3g accepts only the exact field set of:

```text
relaymem.primary_index_log_reconciliation_plan.v0
```

The plan must remain:

```text
runtime_private=true
read_only=true
dry_run_only=true
plan_ready=true
writes_memory=false
updates_index=false
updates_log=false
```

M3g rejects unknown fields at every plan layer and uses strict boolean and integer validation. Boolean values are not accepted as integer byte or operation counts.

The reconciliation state must be one of:

```text
index_and_log_update_required
index_update_required
log_update_required
already_reconciled
```

The state, index/log no-op flags, operation count, operation order, and operation payloads must agree exactly.

An exact, ready M3f plan proves deterministic reconciliation intent only. It is not a durable writer token and contains no RT-1 writer-decision identity.

## Page revalidation

M3g does not treat the M3f plan as proof that the source page still exists. Before reading or replacing a control file, it securely reopens the planned Primary MEM page and verifies:

- deterministic Primary relative path,
- regular-file and no-symlink status,
- bounded UTF-8 content,
- exact byte count,
- exact SHA-256 digest,
- exact Primary page schema,
- Primary memory layer,
- memory kind,
- free-to-update promotion policy,
- ordinary-memory safety scope,
- memory-write idempotency key,
- namespace and source-event correspondence with both control entries,
- lineage correspondence with the log entry,
- summary/title bounds and deterministic page body.

A missing or mismatching page blocks the whole apply before any control-file mutation.

Page validity and an existing Primary page are storage prerequisites, not evidence that a later production invocation remains authorized to mutate Primary state.

## Control-plan validation

Each index/log plan is revalidated independently.

M3g requires:

- exact operation kind,
- exact control-file relative path,
- valid deterministic entry identity,
- bounded expected/proposed byte counts,
- valid expected/proposed SHA-256 digests,
- exact proposed content bytes and digest,
- `conflict=false`,
- no-op flags consistent with expected/proposed state,
- append growth for non-no-op operations,
- exact `# Index` / `# Log` base format,
- canonical compact JSON markers,
- exact marker family and version,
- deterministic marker identity validation,
- exact page path, memory kind/category, idempotency key, and page digest correspondence,
- exact log-to-index entry identity linkage,
- matching namespace/source-event/policy/safety scope between index and log entries.

The ordered operation list must be an exact projection of the associated control plans. For a two-operation plan, index must be operation `0` and log operation `1`.

## Secure store boundary

M3g reuses the M3f secure directory-FD traversal contract. It rejects:

- path traversal,
- absolute or substituted target paths,
- backslashes,
- symlink components,
- non-directory components,
- non-regular control files,
- control-file inode replacement during read,
- oversized content,
- malformed UTF-8,
- OS/runtime platforms without the required secure POSIX primitives.

OS exception text and absolute root paths are not exposed through public diagnostics.

## RelayMEM control-file writer lock

M3g takes a non-blocking exclusive advisory lock on the open `memory/mem` directory for the full inspect/apply/verify sequence.

This lock coordinates concurrent RelayMEM M3g control-file writers without creating a persistent lock file. If the lock is already held, the apply fails closed with a bounded reason identifier and performs no mutation.

The lock establishes the supported **filesystem concurrency boundary** for RelayMEM control-file updates. It is not the RT-1 semantic Primary writer-authority boundary. Acquiring the lock cannot turn a rejected writer decision into permission, and losing or retrying the lock cannot refresh cutover state.

External writers that ignore this filesystem boundary are unsupported; M3g still rechecks expected content immediately before each replace and verifies the final state afterward.

## Per-file atomic replacement

Each required control-file update uses the following bounded sequence in the same directory:

```text
create private unique temp file with mode 0600
  -> write complete proposed content
  -> fsync temp file
  -> recheck target expected/proposed state
  -> atomic os.replace(temp, target)
  -> verify target equals proposed state
  -> fsync directory
```

The current file is never modified in place. Readers observe either the prior complete file or the proposed complete file. M3g also reconstructs the proposed transition and requires it to equal the exact current bytes, an optional terminating newline, and exactly one canonical target marker. A plan cannot remove or rewrite existing control-file bytes while presenting a matching current digest.

Before replacement, the current file must equal either:

- the exact expected byte count and digest, or
- the exact proposed content, byte count, and digest.

The latter is treated as an idempotent no-op. Every marker in a no-op file is still revalidated; an unrelated malformed or forged entry cannot be hidden beside the target entry. Any other state is a conflict and is not overwritten.

Idempotent no-op recognition is a reconciliation consistency property, not authorization. Existing proposed state cannot authorize a fresh Primary mutation after the upstream writer fence.

## Two-file ordering and atomicity boundary

M3g intentionally does **not** claim an atomic transaction across page, index, and log.

For a two-operation plan:

```text
1. index reaches proposed state and is directory-fsynced
2. log reaches proposed state and is directory-fsynced
3. both files are reopened, fsynced, and reverified
```

The log is never applied while the index is unverified or unreconciled.

This creates a valid recoverable intermediate state:

```text
index applied
log still expected
```

M3g reports that state explicitly as:

```text
index_applied_log_pending
```

The same exact M3f plan can be retried. On retry, the index is recognized as already applied and M3g proceeds to the pending log operation. A newly generated M3f `log_update_required` plan is also valid.

A retry or resumable intermediate state does not carry writer permission across invocations. Any later production invocation still enters through the owning C1-2/C1-1 writer-decision gates.

## Result states

Principal result/receipt states are:

```text
disabled
blocked
dry_run_ready
resume_ready
already_applied
applied
index_applied_log_pending
applied_durability_unconfirmed
applied_cleanup_incomplete
applied_state_uncertain
```

`resume_ready` is a dry-run observation that the index already equals the proposed state while the log remains at the expected state for the same plan.

`already_applied` means both control files already equal the proposed state and no replace was required.

`applied` means both files were verified in the proposed state and final file/directory durability confirmation completed.

Post-replace fsync or verification failures are never collapsed into a generic success state.

None of these M3g result states is an RT-1 writer-authorization state. In particular, retryable or uncertain durability cannot be used to regain a fenced Primary writer.

## Runtime-private receipt

The private receipt may include:

- page/control-file relative paths,
- page and control-file digests,
- memory-write idempotency key,
- deterministic index/log entry identities,
- original reconciliation state,
- operation count,
- actual index/log update and no-op booleans,
- durability and cleanup state.

The receipt never includes page, index, or log text content.

The memory-write idempotency key remains distinct from Phase 6 dispatch idempotency.

The receipt intentionally contains no RT-1 writer-decision identity. M3h may consume it as recovery/audit evidence, but the receipt cannot be replayed as Primary mutation permission.

## Content-free projection

The public projection is restricted to:

- result and reconciliation state identifiers,
- plan-valid and page-verified booleans,
- apply-requested boolean,
- index/log reconciled and updated booleans,
- aggregate no-op and conflict counts,
- durability and cleanup booleans,
- bounded reason identifiers.

It does not contain:

- store root or relative paths,
- namespace or candidate ID,
- page/control-file digests,
- idempotency keys,
- marker entry identities,
- page/index/log content,
- proposed content,
- OS exception strings,
- private RT-1 writer-decision identity.

The projection is observability only and cannot be used to infer or reconstruct writer permission.

## Preserved non-goals

M3g does not:

- make page/index/log one atomic transaction,
- create a journal,
- provide general crash-recovery repair,
- delete or rewrite the Primary MEM page,
- create missing index/log files,
- wire request runtime,
- enqueue or execute RelaySLP jobs,
- reuse Phase 6 dispatch idempotency,
- resolve or refresh RT-1 cutover state,
- grant or persist Primary writer authorization,
- mutate RelaySOUL,
- process Secondary MEM,
- expose a Lab API,
- change visible response delivery.

M3h now provides the bounded read-only recovery/audit classification for M3g receipts and current durable state. A future journaled repair apply, if ever required by operational evidence, remains an explicit separate authority rather than being retroactively implied by M3g or M3h.

## Validation

```bash
python -m compileall -q \
  relaylm/relaymem_primary_index_log_apply.py \
  relaylm/_relaymem_primary_index_log_apply.py \
  relaylm/_relaymem_primary_index_log_apply_contract.py \
  relaylm/_relaymem_primary_index_log_apply_io.py \
  scripts/relaylm_relaymem_primary_index_log_apply_smoke.py \
  scripts/relaylm_relaymem_primary_index_log_apply_security_smoke.py

PYTHONPATH=. python scripts/relaylm_relaymem_primary_index_log_apply_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_primary_index_log_apply_security_smoke.py
```

Coverage includes:

- default-off and dry-run behavior,
- strict gate validation,
- exact nested M3f plan validation,
- page revalidation,
- index-before-log ordering,
- both/index-only/log-only/zero-operation plans,
- exact-plan idempotent retry,
- injected log failure and same-plan resume,
- changed-current-state conflict handling,
- canonical marker and digest validation,
- projection leakage checks,
- advisory writer-lock contention,
- page/control-file symlink rejection,
- invalid UTF-8 surrogate plan content,
- empty proposed content in zero-operation no-op plans,
- forged unrelated entries in no-op plans,
- durable temp-cleanup confirmation.

The current C1-1/C1-2 regression umbrella separately proves that a non-permitted writer decision stops before M3g is reached. M3g's dedicated smokes remain reconciliation apply/atomicity/security tests rather than cutover-authority tests.

## Current downstream boundary

M3g is no longer waiting for a later M3h slice. Its exact runtime-private receipt feeds the implemented read-only recovery audit:

```text
M3g exact reconciliation receipt
  -> M3h Primary MEM reconciliation recovery audit
```

M3g owns index-before-log mutation, filesystem concurrency control, state revalidation, per-file atomic replacement, durability evidence, and resumable interrupted-apply semantics. M3h owns bounded read-only recovery classification and does not itself repair the store.

All retained Primary reconciliation capabilities remain subordinate to the exact upstream RT-1 writer decision in production. R5/R6 own their final retirement or explicitly retained historical/read-only/test disposition. This handoff does not pre-authorize deletion, weaken mutation safety, or move recovery/cutover authority into M3g.
