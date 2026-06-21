---
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

Product-critical next slice:

- [Phase 6 Asynchronous RelaySLP Bounded Slice](phase6_async_relayslp_bounded_slice.md)

Phase 6 starts with a docs-only ownership boundary, followed by a helper-only deferred RelaySLP job-admission preflight. It separates dispatch idempotency and RelayRUN orchestration from RelayMEM-M3b/M4 memory semantics, keeps request runtime independent from persistence I/O, and preserves default-off, dry-run-first, fail-closed, and content-free diagnostics behavior.

Completed Core streaming boundary:

- [Phase 5.5 Stream Unpack Bounded Slice](phase5_5_stream_unpack_bounded_slice.md)

Phase 5.5 is complete for RelayLM Core. Concrete TTS execution, audio queueing, adapter delivery, Live2D/avatar mapping, motion, and lip-sync remain SOUL Lab Runtime MVP responsibilities.

Memory lifecycle:

- [Memory Lifecycle Design](memory_lifecycle_design.md) — short-term CTX, governed experience evidence, autonomous ordinary MEM formation, RelaySLP, and SOUL Lab memory operations.
- [RelayMEM / RelaySLP Current / Target Boundary](relaymem_slp_current_target.md) — current read-only/helper state and the migration into deferred Phase 6 orchestration.
- [RelayMEM MVP Implementation Plan](relaymem_mvp_implementation_plan.md) — independent MEM-M bounded implementation track for store contracts, retrieval usability, primary memory formation, secondary consolidation, and Lab-ready operations.

SOUL Lab product layers:

- [SOUL Lab UI MVP](soul_lab_ui_mvp.md) — text-first Lab UI for character creation/adoption, Home, Communication, Lab Observation, and Pod / SOUL Intervention.
- [SOUL Lab Runtime MVP](soul_lab_runtime_mvp.md) — post-UI-MVP runtime adapter layer for TTS, audio queue, Live2D/avatar mapping, timing, preview, and adapter telemetry.

Current instruction-bearing actual apply uses `client_history_exclusion_apply.v1` with explicit `client_instruction_source.v1` provenance. Role, wording, and message position alone are not provenance.

Historical and MVP documents do not override these current owners.

Implementation handoffs under this directory are bounded slice records. After merge, they are historical implementation evidence unless a current status page, implementation plan, or contract explicitly references their behavior as current.
