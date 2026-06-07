# MVP-45: RelayINT Fast Path Dry-Run Summary

## Completed scope

MVP-45 adds a default-off RelayINT Fast Path dry-run. It emits a
content-free diagnostics artifact named `relayint_fast_path_dry_run` when
`relayint_fast_path_dry_run_enabled: true`.

## Design intent

RelayINT is the synchronous, low-latency intent interpretation layer. MVP-45
keeps the first implementation deterministic and lightweight: it detects
pronoun-like references, continuation references, and explicit prior-memory
requests from the latest user turn without calling an LLM.

## Runtime safety

The fast path is diagnostics-only:

- no LLM call;
- no external communication;
- no MEM lookup execution;
- no backend payload mutation;
- no response mutation;
- no raw user text, image URL, candidate body, or snippet body is copied into the
  RelayINT artifact.

## Main validation

The smoke script validates default-off behavior, enabled artifact emission,
continuation/reference detection, explicit prior-memory request detection,
content-free artifact fields, and unchanged backend payload / response body.

## Next phase

Future MVPs can use RelayINT artifacts to guide RelayMEM retrieval planning,
clarification behavior, and CTX packing, while keeping apply paths gated and
observable.
