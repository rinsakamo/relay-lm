# MVP-47: RelayINT Quick Clarification Apply Gate Summary

## Completed scope

MVP-47 adds a gated RelayINT quick clarification apply plan. It consumes the
MVP-46 `relayint_quick_clarification_preflight.v0` artifact and emits
`relayint_quick_clarification_apply_plan.v0` when the apply feature is enabled.

When every gate passes, RelayLM can short-circuit the backend and return a short
fixed clarification response.

## Design intent

RelayINT should avoid sending clearly ambiguous short references to the main LLM
when a safe fixed clarification is enough. MVP-47 adds the apply plumbing while
keeping the behavior explicit, default-off, and content-free.

The generated response uses fixed templates only. It does not include raw user
text, raw CTX values, raw referable labels, snippets, or image URLs.

## Runtime safety

The feature is default-off and dry-run-only by default:

- `relayint_quick_clarification_apply_enabled: false`
- `relayint_quick_clarification_apply_dry_run_only: true`

Actual user-visible response short-circuiting requires both:

- `relayint_quick_clarification_apply_enabled=true`
- `relayint_quick_clarification_apply_dry_run_only=false`

MVP-47 does not:

- call an LLM
- execute MEM lookup
- mutate backend payloads
- persist RelayINT or CTX state
- include internal diagnostics artifacts in response bodies

Scene gates remain authoritative. Recovery mode and
`user_confirmation_required=true` block quick clarification apply.
Streaming apply is unsupported for MVP-47 and fails closed with
`streaming_not_supported`.

## Main validation

The smoke validation covers:

- default-off behavior
- dry-run-only blocking
- actual short-circuit apply for normal ambiguous references
- resolved references falling through to the backend
- recovery / user-confirmation-required blocking
- streaming unsupported plan blocking
- response and artifact content-free assertions

## Next phase

MVP-48 can refine response templates, add optional localization controls, or
introduce a separately gated user-facing clarification policy. Any future
expansion should keep scene gates, content-free constraints, and no-MEM/no-LLM
behavior explicit unless separately configured.
