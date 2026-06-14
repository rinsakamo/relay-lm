# Audit Trace Content-Free Contract

## Status

This document defines the default RelayLM trace persistence boundary introduced by P0-A1 hardening.

The default trace is an **audit trace**, not a conversation transcript and not a debug payload dump.
It is designed to be safe enough for routine local diagnostics when explicitly enabled.

A separate sensitive debug sink is not part of this contract and remains deferred.

## Core invariant

Enabling the default trace must not make RelayLM persist request or response content that the normal runtime path would otherwise keep request-local.

The JSONL audit record must not contain:

- system, developer, user, assistant, or tool message bodies
- assistant response text
- prompt or instruction text
- tool arguments or tool results
- RelayMEM snippet text
- retrieval evidence bodies or evidence envelopes
- SOUL, MEM, or CTX candidate bodies
- backend or original payloads
- local `root_path`, `page_path`, file paths, or URLs

This applies equally to managed routes and `pass_through` routes.

## Persisted record schema

The default record schema is `relaylm.audit_trace.v1`.

Top-level fields are explicitly serialized through an allowlist:

- `schema_version`
- `content_free`
- `trace_id`
- `request_id`
- `created_at`
- `character_id`
- `route_model`
- `mode_applied`
- `compiler_used`
- `message_count`
- `response_present`
- `metadata`

`message_count` and `response_present` describe shape only. They do not preserve any message or response body.

## Metadata contract

Metadata is accepted through typed audit projections in `relaylm/audit_projection.py`. Only exact top-level projectors can copy values into persisted metadata; unknown top-level artifacts are omitted without recursive inspection. Complex artifacts such as pipeline node results, memory selection summaries, and RelayRUN checkpoints have dedicated projection contracts.

Permitted projections are limited to content-free audit information such as:

- event and status identifiers
- schema versions
- node names and node statuses
- decisions and blocked reasons
- booleans and counts
- byte and character totals
- latency values
- opaque IDs and hashes
- content-free `PipelineNodeResult` diagnostics

Content-bearing keys and local-structure keys are not part of any projector. Projection diagnostics use `projection_dropped_field_count` and `projection_unsupported_artifact_count` so operators can see that data was omitted without retaining rejected content.

Full `relaymem_retrieval_artifact`, `evidence_envelope`, snippets, paths, URLs, raw tool payloads, and arbitrary runtime artifacts are not permitted top-level audit metadata.

## Fail-closed behavior

The persisted dictionary is built by an explicit serialization allowlist. Adding a future field to `TraceRecord` does not automatically make it persistent.

Unknown top-level metadata is dropped by registry lookup. Nested strings are retained only when a dedicated projector explicitly copies that field and the final field validator accepts its type, bounds, enum/token grammar, and URL/path restrictions.

Trace construction, sanitization, and writing remain best-effort. A trace failure must not change request handling behavior.

## P0-A1 compatibility boundary

During P0-A1, `build_trace_record()` accepts shape-first `message_count` and `response_present` inputs. Legacy `messages` and `response_text` arguments remain only for compatibility tests and legacy readers; their content is reduced immediately to shape fields and is not stored on `TraceRecord`.

The compatibility properties `TraceRecord.messages` and `TraceRecord.response_text` return `[]` and `None` respectively. They exist only to prevent old readers from failing while making content recovery impossible.

P0-A2 removes raw messages, response text, full retrieval artifacts, and evidence envelopes from runtime trace wiring entirely.

## Legacy JSONL reads

`read_trace_records()` can read an older content-bearing JSONL row, but returns a redacted audit record:

- legacy messages become only `message_count`
- legacy response text becomes only `response_present`
- legacy metadata is reduced through the current typed projection boundary

Existing files are not rewritten automatically. Operators should remove or separately secure old trace files that may contain content.

## Sensitive debug trace

A future sensitive debug trace, if implemented, must use a separate sink and explicit opt-in configuration. It must not weaken or overload this audit contract.

Minimum future requirements include:

- default disabled
- separate file or sink
- prominent warning
- restricted file permissions
- explicit retention and deletion policy
- no silent fallback from the sensitive sink to the audit sink

## Validation

Primary contract checks:

```bash
python -m compileall relaylm scripts/relaylm_trace_content_free_contract_smoke.py
python scripts/relaylm_trace_content_free_contract_smoke.py
python scripts/relaylm_jsonl_trace_smoke.py
python scripts/relaylm_trace_success_smoke.py
python scripts/relaylm_hardening_smoke.py
python scripts/relaylm_pipeline_node_results_runtime_smoke.py
python scripts/relaylm_relayctx_unpack_runtime_app_smoke.py
```

The secret sentinel used by the contract smoke must not appear anywhere in the generated JSONL record.
