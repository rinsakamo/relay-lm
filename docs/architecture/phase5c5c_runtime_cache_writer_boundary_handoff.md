# Phase 5-C5c runtime cache-writer boundary handoff

## Status

Phase 5-C5c wires the typed-parse/cache-writer path into request-local runtime state without trusting frontend payload metadata or backend visible text.

This slice adds runtime plumbing only when an in-process trusted producer supplies a runtime-private typed parse candidate. It does not parse backend responses, does not read arbitrary request metadata as a typed parse source, and does not mutate backend payloads or user-visible responses.

## Runtime-private source boundary

The runtime source is a process-local `ContextVar` consumed by `PipelineContext` construction:

```text
set_client_instruction_typed_parse_runtime_private_source(candidate)
  -> PipelineContext(...)
  -> validate_client_instruction_typed_parse_candidate(...)
```

The source is consumed once and cleared immediately. Missing source produces a typed-parse skipped result and blocks cache write with `source_typed_parse_not_ready`. Routes with both typed-parse and cache-write gates disabled also consume and clear any pending source before returning, so stale candidates cannot leak into a later enabled request in the same execution context.

This is intentionally not an external API contract. A later producer may set the source after it validates a trusted control artifact. Until then, ordinary frontend payload metadata and backend response text are not accepted as typed parse source material.

## Cache writer runtime path

When `client_instruction_cache_write_enabled=true`, runtime wiring calls the C5b writer helper with:

- request-local instruction identity,
- request-local typed parse result,
- managed-route gate,
- `client_instruction_cache_write_dry_run_only`,
- `client_instruction_cache_root`,
- `client_instruction_cache_max_entry_bytes`.

With the default `client_instruction_cache_write_dry_run_only=true`, this remains planning-only. With dry-run disabled, the C5b writer can write only after the same C5b validation gates pass.

Runtime typed parse results with a non-null `parser_version` are blocked before invoking the C5b writer. Current lookup and identity wiring are still parser-version-null compatible, so versioned parse artifacts must not be persisted under the unversioned runtime key.

## Node ordering

Trace node ordering now keeps the C5c path after cache lookup/projection and before client-history preflight:

```text
client_instruction_cache
client_instruction_cache_lookup
client_instruction_relayscn_projection
client_instruction_typed_parse
client_instruction_cache_write
client_history_exclusion_preflight
```

Nodes remain content-free. Runtime-private candidates and cache entries are not serialized into trace diagnostics.

## Non-goals

This slice does not implement:

- backend response parsing,
- frontend metadata trust,
- control-envelope extraction,
- parser-versioned lookup/write compatibility,
- RelaySCN apply,
- backend payload mutation,
- user-visible response mutation,
- asynchronous SLP persistence.

## Smoke coverage

`relaylm_client_instruction_cache_write_runtime_smoke.py` covers:

- missing runtime-private source blocks writer without filesystem write,
- disabled typed-parse/cache-write gates clear any pending runtime-private source,
- versioned runtime-private typed parse source blocks cache write without building an entry,
- runtime-private source plus dry-run-only produces typed parse and cache-write nodes without writing,
- runtime-private source plus dry-run disabled can invoke the gated C5b writer,
- runtime trace node ordering keeps typed parse before cache write,
- diagnostics do not expose raw typed parse values.
