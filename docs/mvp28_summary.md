# MVP-28: RelayMEM Bounded Snippet Runtime Apply Summary

## Date basis

- JST date: 2026-06-02.
- Summary basis: main branch after PR #198 through PR #203 were merged.
- Scope: docs-only summary of the RelayMEM bounded snippet evidence, diagnostics, runtime plan, and gated snippet-bearing runtime apply chain.

## Completed scope

- `snippet_candidates`:
  - RelayMEM can derive bounded snippet candidates from selected MEM page candidates.
  - Snippet extraction is constrained to supported MEM scopes and capped by configured snippet length and candidate count.
- `evidence_envelope`:
  - Snippet diagnostics are wrapped in a source evidence envelope with included snippets and blocked evidence reasons.
  - Blocked evidence records path, evidence reason, and safety status without copying unsafe content into runtime prompts.
- `ctx_block_candidate` evidence metadata:
  - Metadata-only CTX block candidate entries can reference snippet evidence by `evidence_id`.
  - Entries expose snippet availability, evidence kind, snippet character count, estimated snippet tokens, and runtime inclusion state without copying `snippet_text` into metadata-only entries.
- `snippet_apply_readiness`:
  - Retrieval artifacts report `snippet_apply_decision`, readiness score, blocked reasons, and preconditions.
  - Readiness checks scene policy, RelayREF resolution, candidate presence, evidence availability, snippet budget, and dry-run/apply gate state.
- `ctx_block_snippet_candidate`:
  - A diagnostics artifact can carry bounded snippet text for future CTX packing review.
  - It remains non-applied unless the later runtime injection gates pass.
- `snippet_runtime_injection_plan`:
  - A diagnostics plan previews snippet-bearing runtime context derived from `ctx_block_snippet_candidate`.
  - It records source entries, estimated tokens, blocked reasons, and a preview body for the future / gated runtime path.
- Gated snippet-bearing runtime injection apply:
  - A default-off runtime helper can insert `[RelayMEM Snippet Context]` only when all explicit gates and safety checks pass.
  - Snippet-bearing runtime injection runs before token budget truncation and uses a preserved-budget guard.
- `runtime_snippet_injection_result`:
  - Runtime diagnostics now report whether snippet injection was attempted, applied, blocked, and whether payload mutation was applied.
  - The result is available through request diagnostics and trace metadata.

## Runtime safety

- Default disabled:
  - The default runtime path remains metadata-only and does not send snippet text to the backend.
- `memory.snippet_runtime_injection_enabled` defaults to `false`.
- `memory.snippet_runtime_dry_run_only` defaults to `true`.
- Snippet apply gates:
  - `memory.snippet_apply_enabled` must be `true` before snippet runtime injection can apply.
  - `memory.snippet_dry_run_only` must be `false` before snippet runtime injection can apply.
- Runtime CTX gates:
  - `memory.ctx_block_apply_enabled` must be `true`.
  - `memory.retrieval_dry_run_only` must be `false`.
- Scene policy blocks:
  - Recovery/current-context-only, formal-document, medical/safety, unknown, and malformed scene states block snippet apply.
- RelayREF unresolved reference block:
  - Unresolved references block snippet apply to avoid silently using memory in ambiguous contexts.
- Bounded snippet only:
  - Runtime snippet context is based on bounded evidence snippets from the snippet candidate chain.
- No full page body injection:
  - Full MEM pages and raw page bodies are not injected.
- Token budget truncation ordering:
  - Snippet runtime injection is attempted before token budget truncation.
  - The final forwarded payload still passes through token budget truncation after snippet injection.
- Preserved-budget guard:
  - If existing system messages, the latest user message, and the inserted snippet context would exceed the preserved token budget, snippet injection is skipped.
- Metadata-only fallback:
  - If snippet injection is not applied, the existing metadata-only RelayMEM runtime context path remains available.
  - If snippet injection is applied, metadata-only RelayMEM context is skipped to avoid duplicate memory context.
- No MEM/SOUL mutation:
  - The chain does not create, update, delete, approve, persist, or roll back MEM/SOUL state.

## Artifact chain

- `selected_mem_candidates`:
  - Metadata-only RelayMEM candidates selected from store diagnostics and request context.
- `snippet_candidates`:
  - Bounded snippets extracted from eligible selected MEM candidates.
- `evidence_envelope`:
  - Source evidence container for snippets and blocked evidence.
- `ctx_block_candidate`:
  - Metadata-only CTX candidate that references snippet evidence metadata without snippet text.
- `snippet_apply_decision`:
  - Snippet-specific apply/readiness decision such as blocked scene/reference/no snippet/budget, dry-run-only, or eligible-but-not-applied.
- `ctx_block_snippet_candidate`:
  - Diagnostics-only snippet-bearing CTX candidate that may contain bounded `snippet_text`.
- `snippet_runtime_injection_plan`:
  - Diagnostics plan for snippet-bearing runtime prompt insertion.
- `runtime_snippet_injection_result`:
  - Runtime apply result for gated snippet injection and payload mutation state.

## Runtime apply behavior

- Default path remains metadata-only:
  - With default config, backend payloads do not include snippet text.
  - Runtime retrieval still produces diagnostics artifacts for review.
- All gates enabled + eligible path:
  - When all gates pass and `snippet_apply_decision` is `eligible_but_not_applied`, RelayLM inserts a `[RelayMEM Snippet Context]` system message.
- Insertion point:
  - The snippet system message is inserted before the latest user message.
- Metadata-only context skip:
  - When snippet context is applied, the metadata-only `[RelayMEM Context]` message is skipped to avoid duplicate RelayMEM context.
- Token budget truncation:
  - After snippet insertion, the forwarded payload still runs through token budget truncation.
  - Older non-preserved messages may be truncated while system messages and the latest user message remain protected by the truncation policy.

## Diagnostics / trace

- `RequestDiagnostics` fields in this chain:
  - `relaymem_retrieval_artifact`
  - `runtime_ctx_injection_result`
  - `runtime_snippet_injection_result`
- Trace metadata fields emitted when present:
  - `relaymem_retrieval_artifact`
  - `evidence_envelope`
  - `runtime_ctx_injection_result`
  - `runtime_snippet_injection_result`
- Backend payloads do not receive diagnostics artifacts as hidden metadata.
- Original request payloads are copied before runtime mutation and are not mutated in place.

## Main validation

- Compile check:
  - `python -m compileall relaylm`
- RelaySCN / RelayREF smokes:
  - `python scripts/relaylm_relayscn_scene_policy_smoke.py`
  - `python scripts/relaylm_relayref_dry_run_smoke.py`
- RelayMEM retrieval / store / selection smokes:
  - `python scripts/relaylm_relaymem_retrieval_dry_run_smoke.py`
  - `python scripts/relaylm_relaymem_store_dry_run_smoke.py`
  - `python scripts/relaylm_relaymem_selection_dry_run_smoke.py`
- RelayMEM CTX / snippet chain smokes:
  - `python scripts/relaylm_relaymem_ctx_block_candidate_dry_run_smoke.py`
  - `python scripts/relaylm_relaymem_apply_readiness_dry_run_smoke.py`
  - `python scripts/relaylm_relaymem_ctx_injection_plan_dry_run_smoke.py`
  - `python scripts/relaylm_relaymem_runtime_ctx_injection_smoke.py`
  - `python scripts/relaylm_relaymem_snippet_evidence_dry_run_smoke.py`
  - `python scripts/relaylm_relaymem_ctx_block_evidence_metadata_smoke.py`
  - `python scripts/relaylm_relaymem_snippet_apply_readiness_smoke.py`
  - `python scripts/relaylm_relaymem_snippet_ctx_block_candidate_smoke.py`
  - `python scripts/relaylm_relaymem_snippet_runtime_injection_plan_smoke.py`
  - `python scripts/relaylm_relaymem_snippet_runtime_injection_apply_smoke.py`
- Token budget truncation smokes:
  - `python scripts/relaylm_token_budget_truncation_smoke.py`
  - `python scripts/relaylm_token_budget_truncation_apply_smoke.py`
  - `python scripts/relaylm_token_budget_truncation_dry_run_smoke.py`
  - `python scripts/relaylm_token_budget_truncation_proxy_smoke.py`
- Runtime diagnostics / trace smokes:
  - `python scripts/relaylm_runtime_diagnostics_smoke.py`
  - `python scripts/relaylm_trace_success_smoke.py`

## Remaining limitations

- Default disabled:
  - Snippet-bearing runtime injection remains opt-in and gated.
- No semantic ranking yet:
  - Candidate selection is still deterministic / metadata-oriented rather than embedding or semantic ranking based.
- Bounded snippet extraction only:
  - Snippet evidence is bounded and capped; broader page understanding is not implemented.
- No MEM/SOUL write/update:
  - No memory write, SOUL update, approval, rollback, or persistence flow is part of this chain.
- No SLP write path:
  - SLP/MEM write execution remains outside this phase.
- No user-facing debug UI yet:
  - Diagnostics are available through artifacts and traces, not a dedicated UI.

## Next phase

- Quality / behavior evaluation of snippet-bearing context.
- OpenWebUI / LM Studio manual smoke with default-off and gated-on configs.
- Compare metadata-only responses against snippet-bearing responses.
- Evaluate stale and conflicting memory handling.
- Define source/evidence presentation policy for user-visible or debug surfaces.
- Later SLP/MEM write path, after runtime read/apply behavior is evaluated.
