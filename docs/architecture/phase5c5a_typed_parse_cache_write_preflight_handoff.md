# Phase 5-C5a Typed Parse and Cache-Write Preflight Handoff

## Status

Phase 5-C5a starts the typed parse / cache-write boundary without enabling cache writes.

Implemented scope is intentionally narrow:

- typed parse validation helper,
- cache-write preflight helper,
- default-off config gates,
- diagnostics-only cache save planning,
- direct smoke coverage.

It does not implement response/control-envelope extraction, RelaySCN apply, backend payload mutation, user-visible response mutation, or filesystem cache writes.

## Boundary

```text
runtime-private parse candidate
  -> client_instruction_parse.v1 validation
  -> request-local content-bearing typed artifact
  -> content-free diagnostics only

validated typed parse + instruction identity
  -> cache-write preflight
  -> dry-run/no-op by default
  -> no filesystem mutation
```

## Implemented modules

- `relaylm/client_instruction_typed_parse.py`
  - validates `client_instruction_parse.v1` candidates,
  - rejects unknown keys, forbidden content-bearing key names, invalid scene types, invalid scopes/confidence, path/URL-like content, malformed durable candidates, malformed constraints, and duplicate blocked instruction kinds,
  - returns request-local runtime-private typed artifacts only,
  - emits content-free diagnostics.

- `relaylm/client_instruction_cache_write.py`
  - consumes typed parse and instruction identity results,
  - builds a runtime-private `relaylm.client_instruction_cache.v0` candidate in dry-run mode,
  - keeps `cache_write_attempted=false` and `cache_entry_written=false`,
  - blocks when `dry_run_only=false` with `cache_writer_not_implemented`,
  - emits content-free diagnostics.

## Config gates

New default-off fields:

```yaml
client_instruction_typed_parse_enabled: false
client_instruction_cache_write_enabled: false
client_instruction_cache_write_dry_run_only: true
```

`client_instruction_cache_write_enabled` currently only drives diagnostics/no-op cache-save planning. It does not write files.

## Runtime behavior

The existing `client_instruction_cache` dry-run node now receives `save_requested` from `route.client_instruction_cache_write_enabled`.

This keeps lookup/projection read-only behavior unchanged while making future cache-write intent visible in the existing cache operation plan.

## Safety invariants

C5a preserves these invariants:

- default-off,
- fail-closed validation,
- no backend forwarding changes,
- no user-visible response changes,
- no RelaySCN apply,
- no filesystem cache write,
- no raw instruction/response/cache body/hash/path/backend payload/response text in diagnostics,
- typed parse and cache-write preflight remain separate helper boundaries.

## Smoke

Focused smoke:

```bash
python -m compileall relaylm scripts
python scripts/relaylm_client_instruction_typed_parse_cache_write_smoke.py
```

The smoke covers:

- typed parse default-off behavior,
- valid typed parse contract,
- malformed parse candidates fail-closed,
- content-free typed parse diagnostics,
- cache-write default-off behavior,
- dry-run cache-entry candidate construction,
- no write attempt / no entry written,
- actual write blocked because writer is not implemented,
- cache dry-run `save_requested` remains no-op.

## Next slice

Phase 5-C5b should add the actual writer only after a separate review of atomic write safety, symlink/out-of-root checks, temp-file replacement, fsync behavior, max entry bytes, and reader compatibility.
