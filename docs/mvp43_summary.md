# MVP-43: RelayCTX Short-Term Runtime Injection Apply Gate Summary

MVP-43 adds the first gated apply path for RelayCTX short-term runtime injection.
It consumes MVP-42 runtime injection preflight metadata and can insert a
content-free short-term context summary into the backend payload only when all
explicit safety gates pass.

## Safety gates

The apply path remains default-off and dry-run-only by default:

- `relayctx_short_term_runtime_injection_apply_enabled: false`
- `relayctx_short_term_runtime_injection_dry_run_only: true`

Backend payload mutation can occur only when `apply_enabled=true` and
`dry_run_only=false` are both explicitly configured, the preflight has a valid
injection plan, a latest user message exists, and the content-free inserted block
fits the configured token budget.

## Inserted content

MVP-43 inserts only a content-free count summary. It does not inject raw user
text, image URLs, candidate bodies, snippet bodies, or block previews. The
summary tells the backend that the current thread has short-term context
candidates and includes aggregate counts for temporary facts, temporary
preferences, instructions, overrides, and contradictions.

## Non-goals

MVP-43 does not persist short-term CTX, restore cross-thread CTX, mutate
responses, delete/compress/reconstruct OpenWebUI messages, or improve injection
quality beyond safe plumbing. MVP-44 and later can iterate on quality-oriented
injection content, token-budget tuning, and real local OpenWebUI/LM Studio smoke.
