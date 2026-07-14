---
relaylm_doc_type: implementation_contract
relaylm_authority: pipeline_node_result_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: contracts
relaylm_update_trigger:
  - PipelineNodeResult field shape or status enum changes
  - a new node begins recording results
  - RelayRUN begins consuming node results
relaylm_not_authoritative_for:
  - RelayINT quick-clarification chain schemas and gates
  - the PM-D6 RelayINT-native-artifact / RelayREF supersession boundary
  - the repository-wide pipeline responsibility/ordering design
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# PipelineNodeResult Contract

## Purpose

`PipelineNodeResult` is RelayLM's shared, cross-cutting, diagnostics-only record shape for "what happened at one pipeline step," used by many unrelated node types across the input-side client-instruction pipeline, RelayINT, RelayCTX, and RelayMEM-SLP. It is not RelayINT-specific, even though some of its current emitters are RelayINT nodes.

This document is the current-code-derived canonical authority for the type's exact fields, immutability/detachment semantics, request-local collection behavior, content-free trace projection, and non-authority over routing. It replaces the `PipelineNodeResult`-scaffold portions of MVP-48, which is retained only as frozen historical evidence under `docs/evidence/implementation/`.

Current implementation status and sequencing live in [Project Status](../PROJECT_STATUS.md).

## Exact shape

`relaylm/pipeline_node_result.py`:

```python
PipelineNodeStatus = Literal[
    "applied", "skipped", "blocked", "failed", "diagnostic_only",
]

@dataclass(frozen=True)
class PipelineNodeResult:
    node_name: str
    status: PipelineNodeStatus
    decision: str | None = None
    blocked_reasons: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
```

The dataclass is frozen (top-level fields cannot be reassigned after construction). `build_pipeline_node_result(...)` is the only constructor other modules use; it copies (`list(...)`/`dict(...)`) every mutable input at construction time, so later mutation of a caller-owned container does not retroactively change a already-built record's fields.

`to_log_dict()` returns a JSON-friendly, **shallowly** detached dict: it applies one level of `list()`/`dict()` copying to `blocked_reasons`, `diagnostics`, and each entry of `artifacts`, but does not deep-copy nested values inside `diagnostics`. Callers that mutate a nested mutable value obtained from `diagnostics` after logging can still affect the logged reference; current emitters avoid this by only placing flat scalars/lists of scalars in `diagnostics`.

## Request-local collection

`PipelineContext.node_results: list[PipelineNodeResult]` (`relaylm/pipeline_context.py`) is a plain mutable list, freshly empty on every new `PipelineContext` instance (one per request). `record_node_result(result)` is a bare `self.node_results.append(result)` with no exception handling at that layer; ordering is simply list-append order except where `relaylm/trace_runtime.py` explicitly reorders synthesized entries (see below). `node_results_to_log_dicts()` returns `[r.to_log_dict() for r in self.node_results]`.

## Best-effort semantics

Recording and trace output are best-effort: a failure must not change request handling. This is implemented one layer above `record_node_result()`, not inside it — `relaylm/trace_runtime.py` wraps the entire trace-record build path in `try: ... except Exception: return False`, and its node-result synthesis/reordering helper (`_consume_pipeline_node_results()`) wraps `record_phase45_node_results(...)` and related synthesis calls in its own `try/except Exception: return None`.

## Trace projection

`relaylm/trace_runtime.py` writes the detached log-dict list into `trace_metadata["pipeline_node_results"]`. `relaylm/audit_projection.py::PIPELINE_NODE_PROJECTORS` gates every entry through a per-`node_name` `NodeProjector` allowlist before it reaches persisted trace/audit output; an entry whose `node_name` has no registered projector, or whose `diagnostics`/`artifacts` fields are not on that node's allowlist, is dropped rather than passed through — this is the content-free enforcement point for this type (see [Audit Trace Content-Free Contract](../architecture/audit_trace_content_free_contract.md) for the repository-wide audit-projection policy this instantiates).

## Current node-name authority

Current code registers 16 distinct `node_name` values in `relaylm/audit_projection.py::PIPELINE_NODE_PROJECTORS`, spanning several unrelated pipeline areas — this is the authoritative list; do not treat any smaller historical enumeration as current:

```text
client_message_canonicalization
client_instruction_extraction
client_instruction_fingerprint
client_instruction_identity
client_instruction_cache
client_instruction_cache_lookup
client_instruction_relayscn_projection
client_history_exclusion_preflight
client_history_exclusion_apply
relayint_reference_repair          (legacy-shaped compatibility node name, see below)
relayint_reference_intent          (PM-D6-native node)
relayint_quick_clarification
relayctx_repack
relayctx_unpack
relaymem_slp_finalized_turn_source
relaymem_slp_runtime_enqueue
```

`relayint_reference_repair` and `relayint_reference_intent` are both synthesized from the same underlying `relayint_intent_artifact` by `relaylm/pipeline_node_adapter.py::record_phase45_node_results()`. `relayint_reference_repair` is retained only as a trace-shape compatibility identifier (its `diagnostics.compatibility_source_node` field is a fixed label `"relayref"`, not a real data dependency on the historical RelayREF module); `relayint_reference_intent` is the native, forward-looking node name. Neither node reads a `relayref_artifact` value. See [PM-D6 RelayINT Native Artifact / RelayREF Wrapper Removal](../architecture/pm_d6_relayint_native_artifact_relayref_wrapper_removal.md) for the full supersession boundary; this contract does not restate it.

`relayint_reference_repair`, `relayint_reference_intent`, `relayint_quick_clarification`, and `relayctx_repack` are synthesized after the fact by `pipeline_node_adapter.py::record_phase45_node_results()`; the remaining node names are recorded directly at their execution boundary via `PipelineContext.record_node_result(...)`.

## Content-free boundaries

Every current emitter's `diagnostics`/`artifacts` payload is built from booleans, enums, counts, schema-version strings, and content-free artifact-presence summaries (`artifact_name`, `schema_version`, `present`, `applied`, `diagnostics_only`, `content_free` — see `pipeline_node_adapter.py::_summaries()`). No current emitter copies raw user text, raw CTX handoff values, retrieved memory, backend payloads, or response bodies into a `PipelineNodeResult`.

## Non-authority

`PipelineNodeResult` records what happened; it does not decide what happens next. As of this cutover, no code path reads `node_results` (or any individual result's `status`/`decision`/`blocked_reasons`) to select a fallback or retry route, short-circuit the Main LLM or backend, or change RelayRUN recovery behavior — `relaylm/relayrun.py` contains no reference to `node_results` or `PipelineNodeResult`. This type has no persistence or checkpoint authority: it is request-local only and is not written to a durable store or a RelayRUN checkpoint. RelayRUN consumption of node results and cross-cutting checkpoints remains deferred (target-only) work; treat any claim that this has shipped as requiring independent code verification.

This contract does not own the RelayINT quick-clarification chain's own schemas and gates (see [RelayINT Quick-Clarification Runtime Contract](relayint_quick_clarification_runtime_contract.md)) or repository-wide pipeline stage ordering (see [Pipeline Responsibility Design](../architecture/pipeline_responsibility_design.md)). Repository-wide current implementation status remains owned by [Project Status](../PROJECT_STATUS.md).
