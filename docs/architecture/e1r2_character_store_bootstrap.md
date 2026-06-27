---
relaylm_doc_type: architecture_handoff
relaylm_authority: e1r2_character_store_bootstrap
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: evaluation
relaylm_update_trigger:
  - E1-R2 bootstrap command behavior changes
  - RelayMEM character partition or Primary store layout authority changes
  - local MVP evaluation bootstrap requirements change
relaylm_not_authoritative_for:
  - direct SOUL Lab Home-origin trusted scene admission
  - Primary MEM semantic page formation
  - queue, worker, scheduler, or supervised operation authority
  - speaker-provenance-safe summary quality
  - evidence-grounded recall response behavior
relaylm_related_authority:
  - e1_evaluation_consolidation.md
  - e1_local_runtime_evaluation_2026_06_25.md
  - integration_i1_primary_mem_two_turn_recall.md
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_relaymem_primary_pipeline_compose.md
  - relaymem_m3e_atomic_primary_page_writer.md
  - relaymem_m3g_primary_index_log_reconciliation_apply.md
---

# E1-R2 Character Store Bootstrap

Last reviewed: 2026-06-27 JST.

## Purpose

E1-R2 adds the smallest explicit operator-facing bootstrap command for local MVP evaluation. It prepares the minimum character-scoped Primary MEM store layout needed before the existing Primary MEM worker can publish pages, index entries, and log entries.

The command is intentionally not automatic runtime behavior. It is a dry-run-first operator action that keeps the authority boundary visible:

```text
operator invocation
  -> config/root/character/scope validation
  -> dry-run bootstrap plan
  -> optional apply
  -> idempotent store layout preparation
  -> content-free projection
  -> return
```

## Existing authority reused

E1-R2 does not invent a second character partition rule. It resolves the scoped store root with the existing `resolve_relaymem_character_store_root()` authority used by the Primary recall path.

E1-R2 does not invent a second Primary target layout. It uses the existing Primary writer `TARGET_DIR` mapping for the four Primary MEM directories and the existing reconciliation control-file paths and headers:

```text
memory/mem/primary/projects/
memory/mem/primary/relationships/
memory/mem/primary/sessions/
memory/mem/primary/scenes/
memory/mem/index.md    first line: # Index
memory/mem/log.md      first line: # Log
```

## Operator command

The installed console script is:

```bash
relaylm-character-store-bootstrap --config config.yaml --character-id <id> --dry-run
relaylm-character-store-bootstrap --config config.yaml --character-id <id> --apply
```

`--dry-run` is the default behavior when neither mode flag is supplied. `--apply` is explicit. The command emits a single JSON projection with no character value, namespace value, private path, digest, timestamp, queue ID, dispatch ID, lease token, raw exception, user text, model output, or memory text.

## Apply boundary

When apply is requested, E1-R2 may create only missing safe directories and missing empty control files under the resolved character-scoped store root. Repeated apply over an already ready store returns a stable already-ready result and does not rewrite existing files.

E1-R2 may create:

```text
characters/<opaque character partition>/
characters/<opaque character partition>/memory/
characters/<opaque character partition>/memory/mem/
characters/<opaque character partition>/memory/mem/primary/
characters/<opaque character partition>/memory/mem/primary/projects/
characters/<opaque character partition>/memory/mem/primary/relationships/
characters/<opaque character partition>/memory/mem/primary/sessions/
characters/<opaque character partition>/memory/mem/primary/scenes/
characters/<opaque character partition>/memory/mem/index.md
characters/<opaque character partition>/memory/mem/log.md
```

The concrete partition digest is runtime-private and is never emitted in the public projection.

## Fail-closed validation

The command fails closed for:

- missing or disabled memory-store config;
- non-absolute, missing, symlinked, or unsafe configured roots;
- unknown character IDs;
- missing or ambiguous route scope for the requested character;
- existing malformed character root, layout entries, or control files;
- symlink or escape attempts below the scoped store root;
- hardlinked control files;
- non-UTF-8, oversized, unsupported, noncanonical, or wrong-header control files.

Malformed existing state is not repaired silently. The operator must fix or remove the malformed state explicitly.

## Non-goals

E1-R2 does not implement:

- E1-R1 trusted Home scene admission;
- E1-R3 provenance-preserving summary formation;
- E1-R4 grounded recall response behavior;
- O2/O3 supervision or always-on operation;
- job enqueue, claim, retry release, terminal commit, worker execution, scheduler execution, or protected-source mutation;
- Primary MEM semantic page creation;
- edits to existing pages, indexes, logs, lifecycle state, tombstones, Correct/Forget state, Pin state, or Held state;
- TTS, audio, avatar, ASR, or peer transport.
