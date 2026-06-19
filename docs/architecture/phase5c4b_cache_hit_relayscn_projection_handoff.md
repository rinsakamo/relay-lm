# Phase 5-C4b Cache-Hit RelaySCN Projection Handoff

## Status

Phase 5-C4b adds a bounded, diagnostics-only projection from validated instruction-cache hits into RelaySCN-facing pipeline diagnostics.

The implementation is intentionally read-only and non-mutating:

- no backend payload changes,
- no request payload changes,
- no RelaySCN runtime policy replacement,
- no cache writes,
- no raw instruction or cache body exposure.

## Goal

A validated instruction-cache hit can contain a structured scene-state candidate. C4b exposes only a small allowlisted summary of that validated hit so later phases can decide whether and how to use cached RelaySCN structure.

The boundary is:

```text
validated instruction-cache hit
  -> content-free RelaySCN projection summary
  -> PipelineNodeResult diagnostics only
  -> no backend or RelaySCN apply

cache miss / blocked / skipped
  -> content-free status summary
  -> no projection apply
```

## Implemented scope

Implemented in `relaylm/client_instruction_relayscn_projection.py`:

- `client_instruction_relayscn_projection.v0`,
- `build_client_instruction_relayscn_projection(...)`,
- `build_client_instruction_relayscn_projection_node_result(...)`,
- content-free validation that rejects hashes, paths, raw instruction text, cache bodies, scene role names, scene context values, participant names, and constraint values,
- a PipelineNodeResult named `client_instruction_relayscn_projection`.

Runtime trace wiring in `relaylm/trace_runtime.py` inserts the projection node after `client_instruction_cache_lookup` and before history-exclusion nodes.

## Projection allowlist

The projection may expose only enum/count/boolean-style facts:

- cache hit / projection status,
- projected scene type enum,
- scene role presence,
- role scope enum,
- role source enum,
- role confidence bucket,
- scene context presence,
- scene context field count,
- participant count,
- constraint count,
- durable candidate count,
- blocked instruction kind count,
- miss or blocked reason IDs.

The projection must not expose:

- cache key hashes,
- instruction fingerprint hashes,
- route or character cache-private identity values,
- raw instruction text,
- raw cache JSON,
- role names,
- scene setting/task text,
- participant names,
- constraint type/value text,
- filesystem paths,
- backend payloads,
- response text.

## Compatibility

C4b does not change instruction-cache lookup validation. It consumes the existing runtime-private lookup result after validation and emits only a detached diagnostics node.

It does not make cache writes available. Phase 5-C5 remains the typed parse / cache-write boundary.

It does not alter user-visible responses or backend forwarding. Existing pass-through, miss, blocked, and default-off behavior remains unchanged.

## Smoke

Focused smoke:

```bash
python -m compileall relaylm scripts
python scripts/relaylm_client_instruction_relayscn_projection_smoke.py
python scripts/relaylm_client_instruction_cache_lookup_runtime_smoke.py
```

The smoke covers:

- direct cache-hit projection,
- miss / blocked / skipped projection statuses,
- trace PipelineNodeResult ordering,
- read-only cache file behavior,
- unchanged backend payload forwarding,
- no raw role/context/constraint/cache hash leakage.
