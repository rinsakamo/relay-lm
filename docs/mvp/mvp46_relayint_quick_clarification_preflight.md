# MVP-46: RelayINT Quick Clarification Preflight Summary

## Completed scope

MVP-46 adds a default-off RelayINT quick clarification preflight artifact. It
uses the MVP-45 `relayint_fast_path_dry_run` artifact as its only intent input
and emits `relayint_quick_clarification_preflight.v0` when enabled.

The preflight only records whether Fast Path selected
`candidate_action=ask_clarification` and summarizes the clarification candidate
shape with content-free labels and counts.

## Design intent

RelayINT should be able to identify turns where continuing automatically would
be unsafe or ambiguous. MVP-46 prepares the metadata needed for a future quick
clarification response path without generating actual clarification text.

The artifact may expose content-free fields such as:

- source candidate action
- preflight applicability
- clarification type
- candidate label kinds
- scene gate metadata
- safety gates

It must not expose raw user text, raw CTX values, raw referable labels, snippets,
or image URLs.

## Runtime safety

MVP-46 is diagnostics-only.

It does not:

- call an LLM
- execute MEM lookup
- mutate backend payloads
- mutate responses
- generate user-visible clarification text
- persist short-term CTX or RelayINT state

The feature is controlled by
`relayint_quick_clarification_preflight_enabled`, which defaults to `false`.
`relayint_quick_clarification_dry_run_only` defaults to `true`.

## Main validation

The smoke validation covers:

- default-off behavior
- absent preflight when Fast Path is disabled
- preflight creation for ambiguous references
- non-applicable preflight for resolved references
- content-free artifact output
- unchanged backend payloads and responses

## Next phase

MVP-47 can add a gated user-visible quick clarification apply path. That future
step should remain explicit, default-off, and should continue to avoid LLM/MEM
side effects unless separately gated.
