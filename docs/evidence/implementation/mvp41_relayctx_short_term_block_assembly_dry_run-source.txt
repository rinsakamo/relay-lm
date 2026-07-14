# MVP-41: RelayCTX Short-Term Block Assembly Dry-Run Summary

MVP-41 adds a default-off RelayCTX short-term block assembly dry-run. It consumes
MVP-40 extraction dry-run aggregate counts and produces a content-free internal
assembly plan for a future RelayCTX short-term block.

## Scope

MVP-41 is assembly dry-run only:

- no short-term CTX is persisted;
- no cross-thread restore is attempted;
- no runtime injection is attempted;
- backend payloads are not mutated;
- response bodies are not mutated;
- OpenWebUI messages are not deleted, compressed, rewritten, or reconstructed;
- no block content preview or raw message text is emitted.

## Artifact

When `relayctx_short_term_block_assembly_dry_run_enabled: true`, trace metadata
can include `relayctx_short_term_block_assembly_dry_run` with schema version
`relayctx_short_term_block_assembly_dry_run.v0`.

The artifact records content-free metadata only: extraction input presence,
aggregate candidate counts carried forward from extraction, an internal block
concept (`relayctx_short_term`), source (`openwebui_messages`), priority
(`current_thread_over_memory_seed`), a small token budget hint, and safety gates
showing persistence, restore, injection, backend payload mutation, response
mutation, and OpenWebUI message mutation are not allowed.

## Priority policy

The dry-run exposes the intended future priority order as metadata only:

1. `current_user_instruction`
2. `openwebui_recent_messages`
3. `relayctx_short_term`
4. `memory_seed`

This priority is not applied to prompts in MVP-41. MVP-42 and later can build on
this dry-run toward gated runtime injection.
