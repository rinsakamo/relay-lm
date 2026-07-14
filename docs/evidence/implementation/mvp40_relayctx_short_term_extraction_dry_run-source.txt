# MVP-40: RelayCTX Short-Term Extraction Dry-Run Summary

MVP-40 adds a default-off RelayCTX short-term extraction dry-run for inbound
OpenWebUI/OpenAI-compatible messages.

## Safety boundary

The dry-run is diagnostics-only and content-free:

- no short-term CTX is persisted;
- no cross-thread restore is attempted;
- no runtime CTX injection is attempted;
- backend payloads are not mutated;
- response bodies are not mutated;
- raw message text, image URLs, candidate bodies, and snippet bodies are not
  copied into the extraction artifact.

## Artifact

When `relayctx_short_term_extraction_dry_run_enabled: true`, trace metadata can
include `relayctx_short_term_extraction_dry_run` with schema version
`relayctx_short_term_extraction_dry_run.v0`.

The artifact reports aggregate counts only, including message counts, latest user
message character count, temporary fact/preference candidate counts,
instruction/override/contradiction candidate counts, and explicit safety gates
showing persistence, restore, injection, backend payload mutation, and response
mutation are not allowed.

## Classification

Classification is deterministic heuristic-only for MVP-40. It uses only inbound
text while building aggregate counts and does not call an LLM classifier.
OpenAI-compatible content arrays contribute only `type: text` string parts;
non-text parts such as `image_url` are ignored.
