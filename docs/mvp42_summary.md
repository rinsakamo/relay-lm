# MVP-42: RelayCTX Short-Term Runtime Injection Preflight Summary

MVP-42 adds a default-off RelayCTX short-term runtime injection preflight /
dry-run. It consumes MVP-41 block assembly dry-run metadata and emits a
content-free future injection plan.

## Scope

MVP-42 is runtime injection preflight / dry-run only:

- no backend payload mutation is performed;
- no actual runtime injection is performed;
- no short-term CTX is persisted;
- no cross-thread restore is attempted;
- no response mutation is performed;
- OpenWebUI messages are not deleted, compressed, rewritten, or reconstructed;
- no block content preview or system message preview is emitted.

## Artifact

When `relayctx_short_term_runtime_injection_preflight_enabled: true`, trace
metadata can include `relayctx_short_term_runtime_injection_preflight` with
schema version `relayctx_short_term_runtime_injection_preflight.v0`.

The artifact records content-free metadata only: assembly input presence,
short-term candidate counts, whether a future injection plan is present, intended
insertion point (`before_latest_user`), intended message role (`system`), token
budget hints, priority order, and explicit safety gates showing payload mutation,
response mutation, persistence, and restore are not allowed.

## Forward path

`relayctx_short_term_runtime_injection_dry_run_only` defaults to true. MVP-43 and
later can build on this preflight toward gated runtime injection apply, but MVP-42
never applies the plan.
