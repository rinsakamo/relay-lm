"""Reconcile Phase 6-B1 status docs with current main, then remove this script."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "docs/PROJECT_STATUS.md"
ARCH_INDEX = ROOT / "docs/architecture/README.md"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def patch_status() -> None:
    text = STATUS.read_text(encoding="utf-8")

    text = replace_once(
        text,
        """  - docs/architecture/phase6b0_relayslp_durable_queue_contract.md
  - docs/architecture/phase6b1_relayslp_dispatch_preflight.md
  - docs/architecture/relaymem_m3f_primary_index_log_reconciliation_preflight.md
""",
        """  - docs/architecture/phase6b0_relayslp_durable_queue_contract.md
  - docs/architecture/phase6b1_relayslp_dispatch_preflight.md
  - docs/architecture/relaymem_mvp_implementation_plan.md
  - docs/architecture/relaymem_slp_current_target.md
  - docs/architecture/relaymem_m3e_atomic_primary_page_writer.md
  - docs/architecture/relaymem_m3f_primary_index_log_reconciliation_preflight.md
  - docs/architecture/soul_lab_ui_a0_a1_handoff.md
  - docs/architecture/soul_lab_ui_a2_adoption_handoff.md
  - docs/architecture/soul_lab_ui_a3_communication_handoff.md
  - docs/architecture/soul_lab_ui_a4_pod_handoff.md
""",
        "related authority merge",
    )

    text = replace_once(
        text,
        "Last reviewed: 2026-06-21 JST\n",
        "Last reviewed: 2026-06-22 JST\n\nStatus baseline commit: `3d059bac0556d25308ee97e4068bec04a959e7b8`\n",
        "status date and baseline",
    )

    text = replace_once(
        text,
        """Asynchronous RelaySLP orchestration: helper implementation complete through Phase 6-B1

Latest completed bounded slices:
""",
        """Asynchronous RelaySLP orchestration: helper implementation complete through Phase 6-B1
RelayMEM independent track: M1/M2 foundations complete; Primary MEM path implemented through M3f preflight
SOUL Lab UI independent track: UI-A0 through UI-A4 implemented as browser-local mock/presentation slices

Latest completed bounded slices:
""",
        "independent-track summary",
    )

    text = replace_once(
        text,
        """  Phase 6-B1 RelaySLP dispatch preflight
  + exact direct A2 result and enqueue-candidate revalidation
  + deterministic versioned dispatch-idempotency key
  + separately domain-separated deterministic job ID
  + runtime-private initial queued durable-job candidate
  + content-free relaymem.slp_queue_status_projection.v0
  + default-off, read-only, dry-run-only; no queue I/O, worker, memory write, or SOUL mutation
```
""",
        """  Phase 6-B1 RelaySLP dispatch preflight
  + exact direct A2 result and enqueue-candidate revalidation
  + deterministic versioned dispatch-idempotency key
  + separately domain-separated deterministic job ID
  + runtime-private initial queued durable-job candidate
  + content-free relaymem.slp_queue_status_projection.v0
  + default-off, read-only, dry-run-only; no queue I/O, worker, memory write, or SOUL mutation

  RelayMEM-M3c through M3f Primary MEM persistence preparation
  + M3c deterministic Primary page candidate
  + M3d exact writer-handoff and store-target preflight
  + M3e default-off atomic no-clobber Primary page writer
  + M3f read-only index/log reconciliation preflight and deterministic ordered plan
  + no request-runtime wiring, RelaySLP worker, Secondary MEM consolidation, or index/log apply

  SOUL Lab UI-A0 through UI-A4
  + TypeScript/React/Vite shell, mock Home, and read-only Lab Observation preview
  + browser-local first-launch and character-adoption draft flow
  + mock Communication with peer classification, autonomous exchange, Soft Stop, and content-free timeline
  + mock Pod intervention with bounded targets, protected-trait locks, candidate diff, comparison, Hold/Discard, and non-executing Apply/Rollback previews
  + no peer network request, durable RelaySOUL candidate, managed apply, rollback, RelayRUN/RelaySLP mutation, transcript persistence, TTS, audio, or avatar execution
```
""",
        "completed-slice merge",
    )

    text = replace_once(
        text,
        """Phase 6-B0 remains the authoritative durable queue design and state-machine contract. Phase 6-B1 now implements its first bounded consumer: exact direct A2 validation, deterministic dispatch/job identities, fixed initial queue/retry metadata, one runtime-private queued durable-job candidate, and a content-free status projection. B1 performs no queue I/O, duplicate lookup, durable timestamp assignment, claim, lease, worker invocation, memory apply, or SOUL mutation.

Next candidates remain independently sequenced:

- Phase 6-B2: gated atomic create-if-absent durable enqueue with duplicate/collision/corruption classification and no worker invocation,
- later SOUL Lab Runtime MVP adapter bridge/runtime work for TTS/audio/avatar execution.
""",
        """Phase 6-B0 remains the authoritative durable queue design and state-machine contract. Phase 6-B1 now implements its first bounded consumer: exact direct A2 validation, deterministic dispatch/job identities, fixed initial queue/retry metadata, one runtime-private queued durable-job candidate, and a content-free status projection. B1 performs no queue I/O, duplicate lookup, durable timestamp assignment, claim, lease, worker invocation, memory apply, or SOUL mutation.

RelayMEM-M3c through M3f are complete as independent bounded slices. M3e is the first current helper that can durably publish a Primary MEM page when all direct-call gates pass. M3f reopens and revalidates that page plus the current index/log and emits a deterministic reconciliation plan, but remains read-only and never applies the index/log changes.

SOUL Lab UI-A0 through UI-A4 are complete as presentation-only browser slices. They provide the UI foundation, mock Home/Observation surfaces, first-launch/adoption drafts, browser-local autonomous Communication, and a browser-local Pod intervention workflow without reading persona source contents, registering a character, sending peer network requests, creating a durable RelaySOUL candidate, calling `/lab/api/*`, applying or rolling back SOUL, or mutating RelayRUN, RelaySLP, SOUL, or MEM state.

Next boundaries remain independently sequenced:

- Phase 6-B2: gated atomic create-if-absent durable enqueue with duplicate/collision/corruption classification and no worker invocation,
- RelayMEM-M3g: gated index/log reconciliation apply consuming the exact M3f plan,
- SOUL Lab UI-A5: browser-local Memory Inspector for formed/held/blocked outcomes and non-persistent operation previews,
- later SOUL Lab Runtime MVP adapter bridge/runtime work for TTS/audio/avatar execution.
""",
        "next-boundary merge",
    )

    text = replace_once(
        text,
        """- RelayMEM-M3f Primary MEM index/log reconciliation preflight,
- Phase 6-A1 RelaySLP job-admission preflight helper,
""",
        """- RelayMEM-M3f Primary MEM index/log reconciliation preflight,
- SOUL Lab UI-A0/A1 shell, mock Home, and read-only Lab Observation preview,
- SOUL Lab UI-A2 browser-local first-launch and adoption draft flow,
- SOUL Lab UI-A3 browser-local mock Communication session surface,
- SOUL Lab UI-A4 browser-local mock Pod / SOUL Intervention workflow,
- Phase 6-A1 RelaySLP job-admission preflight helper,
""",
        "current-main UI merge",
    )

    text = replace_once(
        text,
        """Phase 6-A1, A2, and B1 are direct helper gates rather than route configuration fields. Their call defaults are disabled and dry-run-only. No request runtime invokes them automatically. Phase 6-B1 creates only a runtime-private dry-run durable-job candidate and does not persist it.
""",
        """Phase 6-A1, A2, and B1 are direct helper gates rather than route configuration fields. Their call defaults are disabled and dry-run-only. No request runtime invokes them automatically. Phase 6-B1 creates only a runtime-private dry-run durable-job candidate and does not persist it. RelayMEM-M3e is also a direct-helper boundary: its call defaults are `enabled=false`, `apply_enabled=false`, and `dry_run_only=true`. M3f accepts only read-only dry-run operation and cannot apply index/log changes.
""",
        "direct-helper merge",
    )

    text = replace_once(
        text,
        "- Primary MEM index/log reconciliation apply,\n",
        "- RelayMEM-M3g index/log reconciliation apply and broader Phase 6 persistence apply,\n",
        "not-implemented merge",
    )

    text = replace_once(
        text,
        """RelayLM does not own frontend UI, ASR, TTS execution, transport delivery, or avatar execution. Current streaming remains backend SSE forwarding by default; gated runtime Stream Unpack suppression and runtime TTS adapter handoff/transport planning exist only when their gates are explicitly enabled.
""",
        """RelayLM Core request runtime does not own frontend rendering, ASR, TTS execution, transport delivery, or avatar execution. The repository does include the presentation-only SOUL Lab UI-A0 through UI-A4 under `apps/soul-lab`; it remains mock/browser-local and is not a Core authority surface. Current streaming remains backend SSE forwarding by default; gated runtime Stream Unpack suppression and runtime TTS adapter handoff/transport planning exist only when their gates are explicitly enabled.
""",
        "frontend ownership merge",
    )

    text = replace_once(
        text,
        """- [Phase 6-B0 RelaySLP Durable Queue Contract](architecture/phase6b0_relayslp_durable_queue_contract.md)
- [Phase 6-B1 RelaySLP Dispatch Preflight](architecture/phase6b1_relayslp_dispatch_preflight.md)
- [RelayMEM-M3f Primary MEM Index/Log Reconciliation Preflight](architecture/relaymem_m3f_primary_index_log_reconciliation_preflight.md)
""",
        """- [Phase 6-B0 RelaySLP Durable Queue Contract](architecture/phase6b0_relayslp_durable_queue_contract.md)
- [Phase 6-B1 RelaySLP Dispatch Preflight](architecture/phase6b1_relayslp_dispatch_preflight.md)
- [RelayMEM MVP Implementation Plan](architecture/relaymem_mvp_implementation_plan.md)
- [RelayMEM / RelaySLP Current / Target Boundary](architecture/relaymem_slp_current_target.md)
- [RelayMEM-M3e Atomic Primary MEM Page Writer](architecture/relaymem_m3e_atomic_primary_page_writer.md)
- [RelayMEM-M3f Primary MEM Index/Log Reconciliation Preflight](architecture/relaymem_m3f_primary_index_log_reconciliation_preflight.md)
- [SOUL Lab UI-A0 / UI-A1 Handoff](architecture/soul_lab_ui_a0_a1_handoff.md)
- [SOUL Lab UI-A2 Adoption Handoff](architecture/soul_lab_ui_a2_adoption_handoff.md)
- [SOUL Lab UI-A3 Communication Handoff](architecture/soul_lab_ui_a3_communication_handoff.md)
- [SOUL Lab UI-A4 Pod Handoff](architecture/soul_lab_ui_a4_pod_handoff.md)
""",
        "read-next merge",
    )

    STATUS.write_text(text, encoding="utf-8")


def write_architecture_index() -> None:
    ARCH_INDEX.write_text(
        """---
relaylm_doc_type: documentation_index
relaylm_authority: architecture_documentation_entrypoint
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - architecture entry points change
  - canonical architecture authority changes
  - local handoff interpretation changes
relaylm_not_authoritative_for:
  - current runtime behavior
  - phase sequencing details
  - exact schema details
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# RelayLM Architecture Docs

Use [Documentation index](../README.md) for the complete active document map.

Architecture documents follow the [AI-first documentation model](../DOCUMENTATION_MODEL.md). Treat document front matter as the first signal for type, authority, status, volatility, and non-authoritative scope when reading a file through partial search.

Canonical authority:

1. [Pipeline Responsibility Design](pipeline_responsibility_design.md)
2. [Pipeline Implementation Plan](pipeline_implementation_plan.md)
3. Dedicated current contracts
4. [Current / Target / Migration Guide](current_target_migration_guide.md)

Product-critical Phase 6 boundaries:

- [Phase 6 Asynchronous RelaySLP Bounded Slice](phase6_async_relayslp_bounded_slice.md)
- [Phase 6-A1 RelaySLP Job Admission Contract](phase6a1_relayslp_job_admission_contract.md)
- [Phase 6-A2 RelaySLP Response-Finalization Handoff Contract](phase6a2_relayslp_response_handoff_contract.md)
- [Phase 6-B0 RelaySLP Durable Queue Contract](phase6b0_relayslp_durable_queue_contract.md)
- [Phase 6-B1 RelaySLP Dispatch Preflight](phase6b1_relayslp_dispatch_preflight.md)

Phase 6-A1 validates deferred RelaySLP admission metadata. Phase 6-A2 creates one runtime-private dry-run enqueue candidate after a finalized `turn_end`. Phase 6-B0 owns the durable-record, dispatch-idempotency, state-machine, duplicate/collision, lease/restart/corruption, and content-free projection contract. Phase 6-B1 generates deterministic dispatch/job identities and a runtime-private initial queued durable-job candidate without queue I/O. Phase 6-B2 atomic durable enqueue is next.

Completed Core streaming boundary:

- [Phase 5.5 Stream Unpack Bounded Slice](phase5_5_stream_unpack_bounded_slice.md)

Phase 5.5 is complete for RelayLM Core. Concrete TTS execution, audio queueing, adapter delivery, Live2D/avatar mapping, motion, and lip-sync remain SOUL Lab Runtime MVP responsibilities.

Memory lifecycle:

- [Memory Lifecycle Design](memory_lifecycle_design.md) — short-term CTX, governed experience evidence, autonomous ordinary MEM formation, RelaySLP, and SOUL Lab memory operations.
- [RelayMEM / RelaySLP Current / Target Boundary](relaymem_slp_current_target.md) — current read-only/helper state and the migration into deferred Phase 6 orchestration.
- [RelayMEM MVP Implementation Plan](relaymem_mvp_implementation_plan.md) — independent MEM-M bounded implementation track for store contracts, retrieval usability, primary memory formation, secondary consolidation, and Lab-ready operations.

RelayMEM Primary persistence track:

- [RelayMEM-M3a Primary Formation Handoff](relaymem_m3a_primary_formation_handoff.md) — governed Primary MEM candidate boundary.
- [RelayMEM-M3d Primary Writer Handoff](relaymem_m3d_primary_writer_handoff.md) — exact M3c candidate/store-target revalidation and writer handoff.
- [RelayMEM-M3e Atomic Primary Page Writer](relaymem_m3e_atomic_primary_page_writer.md) — default-off direct-helper page publication.
- [RelayMEM-M3f Index/Log Reconciliation Preflight](relaymem_m3f_primary_index_log_reconciliation_preflight.md) — read-only deterministic reconciliation planning; M3g apply remains next.

SOUL Lab product layers:

- [SOUL Lab UI MVP](soul_lab_ui_mvp.md) — text-first Lab UI for character creation/adoption, Home, Communication, Lab Observation, and Pod / SOUL Intervention.
- [SOUL Lab UI-A0 / UI-A1 Handoff](soul_lab_ui_a0_a1_handoff.md) — current TypeScript/React/Vite foundation, mock Home, read-only Lab Observation preview, and browser authority boundary.
- [SOUL Lab UI-A2 Adoption Handoff](soul_lab_ui_a2_adoption_handoff.md) — first-launch No Active Character state, Lab Assistant guidance, and browser-local new/adopt/import draft flows.
- [SOUL Lab UI-A3 Communication Handoff](soul_lab_ui_a3_communication_handoff.md) — browser-local peer classification, autonomous mock exchange loop, Soft Stop, emergency stop, and content-free timeline.
- [SOUL Lab UI-A4 Pod Handoff](soul_lab_ui_a4_pod_handoff.md) — bounded intervention targets, locked protected traits, candidate diff, browser-local comparison, Hold/Discard, and non-executing Apply/Rollback previews.
- [SOUL Lab Runtime MVP](soul_lab_runtime_mvp.md) — post-UI-MVP runtime adapter layer for TTS, audio queue, Live2D/avatar mapping, timing, preview, and adapter telemetry.

The current UI implementation is complete through UI-A4. UI-A5 Memory Inspector is the next independent UI slice; peer transport, server-side management APIs, RelaySOUL apply/rollback, memory mutation, and Runtime adapter execution remain separate.

Current instruction-bearing actual apply uses `client_history_exclusion_apply.v1` with explicit `client_instruction_source.v1` provenance. Role, wording, and message position alone are not provenance.

Historical and MVP documents do not override these current owners.

Implementation handoffs under this directory are bounded slice records. After merge, they are historical implementation evidence unless a current status page, implementation plan, or contract explicitly references their behavior as current.
""",
        encoding="utf-8",
    )


def main() -> None:
    patch_status()
    write_architecture_index()
    print("Phase 6-B1 current-main status reconciliation applied")


if __name__ == "__main__":
    main()

# sync trigger
