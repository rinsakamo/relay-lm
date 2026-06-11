# MVP-47: RelayINT Quick Clarification Apply Plan Summary

## Completed scope

MVP-47 is a Phase 4 plan-only / preflight-only milestone. It consumes the
MVP-46 `relayint_quick_clarification_preflight.v0` artifact and, only when the
feature flag is enabled, emits the content-free
`relayint_quick_clarification_apply_plan.v0` diagnostic artifact.

MVP-47 does **not** apply the plan to user-visible output. Backend forwarding
continues normally, backend payloads remain unchanged, and response bodies remain
backend-owned.

## Design intent

RelayINT should be able to decide whether a future quick clarification response
would be safe before any user-visible behavior exists. MVP-47 therefore records
only diagnostics: preflight compatibility, block reasons, dry-run state, and
content-free template metadata for a later phase.

The apply plan never includes raw user text, raw CTX values, raw referable
labels, snippets, tool/function names, or image URLs.

## Runtime safety

The feature is default-off and dry-run-only by default:

- `relayint_quick_clarification_apply_enabled: false`
- `relayint_quick_clarification_apply_dry_run_only: true`

Phase 4 keeps all runtime behavior diagnostics-only. Even if the flag is enabled
for smoke/preflight validation, MVP-47 still does not:

- short-circuit backend forwarding
- return a fixed clarification response directly
- mutate backend payloads
- mutate response bodies
- call an LLM
- execute MEM lookup for the quick clarification apply plan
- persist RelayINT or CTX state
- include internal diagnostics artifacts in response bodies

Scene gates remain authoritative. Recovery mode and
`user_confirmation_required=true` block quick clarification planning.
Structured responses, tools/functions, audio modalities, streaming, response
shaping, and other unsupported request shapes fail closed in the request
compatibility gate.

## Main validation

The smoke validation covers:

- default-off behavior emits no apply plan
- dry-run-only behavior emits an apply plan but forwards to the backend
- Phase 4 remains plan-only even when the apply flag is enabled for preflight
- structured/tool/audio/streaming compatibility gates block the plan
- no raw user content, raw CTX values, tool/function names, or image URLs leak
  into the plan
- backend payloads are not mutated
- response bodies are not mutated and still contain the backend response
- backend forwarding is never skipped by quick clarification apply planning

## Deferred to Phase 6

A later Phase 6 may add separately gated user-visible quick clarification apply
behavior, including response template rendering and backend short-circuiting.
That future phase must keep scene gates, request compatibility gates,
content-free constraints, and no-MEM/no-LLM behavior explicit unless separately
configured.
