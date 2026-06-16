# Client History Exclusion Apply Forward Gate

## Scope

This Phase 5-C1a slice connects the no-instruction client-history exclusion
contract to the backend-forward boundary.

The gate remains default-off. When explicitly enabled in actual-apply mode, a
managed request may reach the backend only when the request-local apply result is
an exact successful `client_history_exclusion_apply.v0` result.

## Runtime order

```text
compiled managed payload
  -> client history exclusion preflight
  -> no-instruction exclusion apply
  -> RelayCTX Repack phases
  -> backend-forward gate
```

Apply occurs before RelayCTX Repack so later server-owned context injection can
operate on the reduced current-turn payload.

## Fail-closed rule

When all of the following are true:

- `client_history_exclusion_apply_enabled=true`,
- `client_history_exclusion_apply_dry_run_only=false`,
- the route is RelayLM-managed,

then any missing, blocked, failed, or non-applied result blocks backend forward.
The previous client history is never restored as a fallback.

Pass-through routes remain client-owned and are exempt. Dry-run-only mode records
an apply candidate without mutating or blocking backend forwarding.

## Privacy boundary

The rebuilt payload and current-user candidate remain request-local. The pipeline
node contains only allowlisted status, counts, booleans, and bounded reasons. Raw
history, current-user content, multimodal data, instruction evidence, prompt text,
and exception text are not copied into the node result.

## Deferred work

This slice does not implement:

- cache-hit RelaySCN injection,
- cache-miss low-trust instruction evidence,
- `client_instruction_parse.v1`,
- cache writes,
- streaming RelayCTX Unpack,
- content-free trace migration.
