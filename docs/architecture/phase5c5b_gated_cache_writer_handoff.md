# Phase 5-C5b gated client-instruction cache writer handoff

## Status

Phase 5-C5b adds the first gated writer for validated client-instruction cache entries.

The slice is intentionally narrow:

- no backend payload mutation,
- no user-visible response mutation,
- no RelaySCN apply,
- no backend-response parsing,
- no raw instruction or raw response persistence,
- no cache write unless all explicit gates pass.

## Gates

A write can occur only when the caller supplies all of the following:

- a managed route,
- `client_instruction_cache_write_enabled=true`,
- `client_instruction_cache_write_dry_run_only=false`,
- a ready client-instruction identity result,
- a ready `client_instruction_parse.v1` typed parse result,
- an existing valid `client_instruction_cache_root`,
- a `client_instruction_cache_max_entry_bytes` budget large enough for the entry.

With `client_instruction_cache_write_dry_run_only=true`, the helper remains planning-only and performs no filesystem mutation.

## Persisted entry contract

The writer persists only `relaylm.client_instruction_cache.v0` entries. Before writing, the entry is validated through the existing cache lookup resolver so the writer and reader remain schema-compatible.

The target file name is derived from the validated `cache_key_sha256`:

```text
<client_instruction_cache_root>/<cache_key_sha256>.json
```

The writer rejects missing roots, invalid byte budgets, entries larger than the configured max, symlink roots, symlink root components, symlink targets, and target paths outside the resolved root. The root-component symlink check mirrors the reader-side `cache_root_symlink_blocked` boundary so the writer does not create entries under a root that the runtime reader will reject. Missing cache roots are blocked with `cache_root_missing`; the writer does not create the root tree.

C5b also keeps persisted `parser_version` set to `null` because the current runtime cache lookup path validates entries without a parser-version expectation. A later runtime-wiring slice may pass a parser version through lookup; until then, writer output must remain compatible with the runtime reader path.

## Write semantics

The write path uses:

1. deterministic JSON serialization,
2. temporary file creation under the resolved cache root,
3. file flush + `fsync`,
4. atomic replace into the target file,
5. best-effort directory `fsync`.

Any write error returns a blocked result and removes the temporary file when possible.

## Diagnostics

Diagnostics remain content-free. They can report booleans, status, byte counts, and blocked reason codes, but must not include raw instruction text, raw response text, cache hashes, route IDs, character IDs, scene values, file paths, or persisted entry bodies.

## Smoke coverage

`relaylm_client_instruction_typed_parse_cache_write_smoke.py` covers:

- typed parse default-off and malformed candidate blocking,
- cache-write dry-run no-op behavior,
- missing root blocking without root creation,
- max-entry-size blocking before write attempts,
- symlinked root-component blocking,
- parser-version compatibility with current runtime lookup,
- atomic writer success,
- persisted entry validation through the lookup resolver,
- content-free diagnostics for both dry-run and applied writer results,
- write-only dependency gating.

## Next slice

Phase 5-C5c should wire the gated writer into runtime only after the parser source is defined. The current C5b helper does not parse backend output and should not be treated as a full runtime cache-write pipeline by itself.
