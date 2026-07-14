# MVP-48: Pipeline Node Result Scaffold

## Completed scope

MVP-48 completes the Phase 4.5 diagnostics-only pipeline node result scaffold.

The milestone adds:

- `relaylm/pipeline_node_result.py`
  - frozen `PipelineNodeResult`
  - shared `PipelineNodeStatus`
  - detached `to_log_dict()` serialization
  - `build_pipeline_node_result(...)`
- request-local `PipelineContext.node_results`
- ordered node-result recording and detached log serialization
- content-free runtime summaries for:
  - `relayint_reference_repair`
  - `relayint_quick_clarification`
  - `relayctx_repack`
- best-effort trace metadata output under `pipeline_node_results`

## Design intent

Phase 4.5 establishes one common record shape before node results are allowed to control runtime behavior.

A `PipelineNodeResult` records what happened at a pipeline step. It does not yet decide what the runtime should do next.

This keeps the scaffold compatible with future failure routing and RelayRUN checkpoint reporting while avoiding premature coupling between diagnostics and orchestration.

## Runtime safety

MVP-48 remains diagnostics-only.

It does not:

- change backend forwarding
- mutate request payloads by recording a node result
- mutate response bodies
- add user-visible clarification responses
- select fallback or retry routes
- short-circuit the Main LLM or backend
- change RelayRUN recovery behavior
- copy raw user text, raw CTX handoff values, retrieved memory, backend payloads, or response bodies into pipeline node summaries

Node-result recording and trace output are best-effort. A recording or trace failure must not change request handling behavior.

The historical RelayINT / RelayREF compatibility boundary remains intact:

- runtime compatibility key: `relayref_artifact`
- historical source node: `relayref`
- RelayINT-facing alias: `relayint_reference_repair`

## Main validation

The following smoke coverage fixes the Phase 4.5 contract:

- `scripts/relaylm_pipeline_node_result_smoke.py`
  - minimal shape
  - frozen top-level record
  - caller-container detachment
  - detached log serialization
- `scripts/relaylm_pipeline_context_node_results_smoke.py`
  - request-local collection
  - result ordering
  - detached log output
  - no payload-routing mutation from recording
- `scripts/relaylm_pipeline_node_results_runtime_smoke.py`
  - runtime recording order
  - content-free summaries
  - backend payload preservation
  - backend forwarding preservation
  - backend-owned response preservation
- existing RelayINT and runtime diagnostics smokes remain green

## Phase completion

Phase 4 is complete as a plan-only RelayINT handoff:

- reference repair is exposed through RelayINT naming
- quick clarification fast-path, preflight, and apply-plan artifacts exist
- actual user-visible short-circuit apply remains deferred

Phase 4.5 is complete as a diagnostics-only scaffold:

- common node-result type exists
- `PipelineContext` can collect request-local results
- selected existing phases emit content-free trace summaries
- node results do not yet control routing

## Deferred work

The following are intentionally deferred and are not MVP-48 defects:

- minimal non-streaming RelayCTX Unpack: Phase 5
- streaming RelayCTX Unpack and output segmentation: Phase 5.5
- blocked / failed / fallback runtime routing: Phase 6
- actual RelayINT quick clarification short-circuit apply: Phase 6
- RelayRUN consumption of node results and cross-cutting checkpoints: Phase 6 and Phase 9
- removal of historical `relayref` compatibility names: later compatibility migration

## Next phase

Phase 5 should add minimal non-streaming `RelayCTX Unpack`.

The Unpack implementation should record its result at the execution boundary through `PipelineContext.record_node_result(...)`, while the existing Phase 4.5 terminal summaries may remain in place until failure routing is introduced.
