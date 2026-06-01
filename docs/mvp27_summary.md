# MVP-27: RelayMEM Retrieval Runtime Apply Chain Summary

## Date basis

- JST date: 2026-06-01.
- Summary basis: main branch after PR #188 through PR #196 were merged.
- Scope: docs-only summary of the RelaySCN / RelayREF / RelayMEM retrieval runtime apply chain.

## Completed scope

- RelaySCN scene policy artifact:
  - `relayscn_scene_policy_artifact` is produced on the runtime request path and trace path.
  - Scene policy output provides `scene_state`, RelayMEM retrieval scope, persistence block state, and persistence block reasons.
- RelayREF diagnostics artifact:
  - `relayref_artifact` records unresolved reference state without silently resolving ambiguous user references.
  - RelayREF diagnostics are connected to RelaySCN recovery policy context.
- RelayMEM retrieval dry-run artifact:
  - `relaymem_retrieval_artifact` records retrieval scope, scene type, query summary, selected candidates, blocked reasons, token budget, and apply readiness.
  - `ctx_block` remains `null` in the dry-run chain.
- File-backed store diagnostics:
  - Store diagnostics can read a configured root path in read-only dry-run mode.
  - Store diagnostics report fallback reasons, blocked files, and validation / scan truncation without mutating MEM files.
- `selected_mem_candidates` dry-run:
  - File-backed candidates are selected as metadata-only MEM candidates.
  - Candidate output keeps path/source/reason/estimated-token metadata and marks candidates as not applied to CTX.
- `ctx_block_candidate` dry-run:
  - Selected MEM candidates are packed into a diagnostics-only CTX block candidate.
  - Candidate entries are budget-aware and mark whether each entry would be included.
- Apply readiness diagnostics:
  - Retrieval artifacts include `apply_decision`, `apply_readiness_score`, `apply_blocked_reasons`, and `apply_preconditions`.
  - Apply readiness is explicit about scene policy, reference resolution, candidate presence, budget fit, dry-run state, and apply gate state.
- `ctx_injection_plan` dry-run:
  - Retrieval artifacts include a diagnostics-only injection plan with preview text, source entries, budget estimate, and blocked reasons.
  - The plan describes what could be injected while keeping backend payload mutation disabled by default.
- Gated runtime CTX injection apply path:
  - Runtime CTX injection helper now exists behind explicit gates.
  - The helper returns `runtime_ctx_injection_result` diagnostics and only mutates a copied backend payload when all apply gates and safety checks pass.

## Runtime safety

- Default no-op:
  - The default request path remains diagnostics-only for RelayMEM retrieval and CTX injection.
  - Backend payload mutation is blocked unless explicit runtime gates are enabled and the retrieval artifact is eligible.
- `memory.ctx_block_apply_enabled` defaults to `false`.
- `memory.retrieval_dry_run_only` defaults to `true`.
- Scene policy blocks:
  - `recovery` scenes block apply readiness.
  - `formal_document` scenes block external memory apply.
  - `medical_or_safety` scenes block external memory apply.
  - malformed or unsupported scene types are normalized to `unknown` and block memory apply.
- RelayREF unresolved reference blocks:
  - Unresolved references produce blocking reasons and prevent silent RelayMEM context injection.
- Token budget truncation ordering:
  - CTX block candidate packing marks entries that would exceed the RelayMEM token budget as excluded.
  - Budget-truncated candidates block apply readiness before runtime injection can proceed.
- Preserved-budget overflow guard:
  - Runtime CTX injection checks whether adding the RelayMEM context message would break the preserved token budget before mutating the forwarded payload copy.
- MEM path/reason metadata sanitization:
  - Runtime prompt injection uses sanitized MEM path and reason metadata.
  - Prompt-facing metadata is normalized and length-limited before insertion.
- No MEM/SOUL mutation:
  - The chain does not write, update, persist, or roll back MEM/SOUL state.
- No raw page body injection yet:
  - Runtime injection uses metadata-only context hints.
  - MEM page bodies are not injected into prompts in this phase.

## Artifact chain

- `relayscn_scene_policy_artifact`:
  - Defines scene state, retrieval scope, and persistence block posture.
- `relayref_artifact`:
  - Reports unresolved reference state and confirmation requirements.
- `relaymem_retrieval_artifact`:
  - Collects RelayMEM retrieval diagnostics, store diagnostics, selected candidates, CTX candidate, apply readiness, and injection plan.
- `ctx_block_candidate`:
  - Represents diagnostics-only candidate entries derived from selected MEM candidates.
  - Includes source path, source type, reason, estimated tokens, inclusion state, and budget status.
- `apply_decision`:
  - Summarizes whether the chain is blocked by scene policy, unresolved reference, no candidates, token budget, dry-run gates, or eligible-but-not-applied state.
- `ctx_injection_plan`:
  - Summarizes the candidate context that could be inserted, source entries, preview text, budget estimate, and blocked reasons.
- `runtime_ctx_injection_result`:
  - Reports whether runtime CTX injection was attempted, applied, blocked, and whether payload mutation occurred.

## Diagnostics / trace

- `RequestDiagnostics` fields added across the apply chain:
  - `relayscn_scene_policy_artifact`
  - `relayref_artifact`
  - `relaymem_retrieval_artifact`
  - `runtime_ctx_injection_result`
- Trace metadata fields emitted when present:
  - `relayscn_scene_policy_artifact`
  - `relayref_artifact`
  - `relaymem_retrieval_artifact`
  - `runtime_ctx_injection_result`
- Diagnostics remain request-local and trace-local.
- Backend-facing payloads do not receive diagnostics artifacts as hidden metadata.

## Main validation

- `python -m compileall relaylm`
- RelaySCN smoke:
  - `python scripts/relaylm_relayscn_scene_policy_smoke.py`
- RelayREF smoke:
  - `python scripts/relaylm_relayref_dry_run_smoke.py`
- RelayMEM retrieval / store / selection / CTX block candidate / apply readiness / CTX injection plan / runtime CTX injection smokes:
  - `python scripts/relaylm_relaymem_retrieval_dry_run_smoke.py`
  - `python scripts/relaylm_relaymem_store_dry_run_smoke.py`
  - `python scripts/relaylm_relaymem_selection_dry_run_smoke.py`
  - `python scripts/relaylm_relaymem_ctx_block_candidate_dry_run_smoke.py`
  - `python scripts/relaylm_relaymem_apply_readiness_dry_run_smoke.py`
  - `python scripts/relaylm_relaymem_ctx_injection_plan_dry_run_smoke.py`
  - `python scripts/relaylm_relaymem_runtime_ctx_injection_smoke.py`
- Token budget truncation smokes:
  - `python scripts/relaylm_token_budget_truncation_smoke.py`
  - `python scripts/relaylm_token_budget_truncation_request_path_smoke.py`
- Runtime diagnostics / trace smokes:
  - `python scripts/relaylm_runtime_diagnostics_smoke.py`
  - `python scripts/relaylm_jsonl_trace_smoke.py`

## Remaining limitations

- Default disabled:
  - Runtime CTX injection is not active unless explicit gates are enabled.
- Path/reason metadata only:
  - Runtime RelayMEM prompt content is limited to sanitized path and reason metadata.
- No MEM page body injection:
  - Page bodies are not extracted or inserted into runtime prompts yet.
- No MEM/SOUL write/update:
  - The chain does not create, update, approve, persist, roll back, or delete MEM/SOUL state.
- No semantic ranking yet:
  - Candidate discovery and selection remain simple metadata/query-term diagnostics rather than semantic ranking.
- No SLP/MEM write path yet:
  - SLP-to-MEM write execution is still outside this runtime retrieval apply chain.

## Next phase

- Add controlled page snippet extraction.
- Add source evidence envelope for any future snippet-bearing context.
- Add stricter budgeted CTX packing before wider apply enablement.
- Add user-visible diagnostics or a debug endpoint if needed.
- Eventually add an SLP write path, but not yet.
