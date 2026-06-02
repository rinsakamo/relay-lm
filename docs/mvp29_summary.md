# MVP-29: RelayMEM Local LLM Behavior Summary

## Date basis

- JST date: 2026-06-02.
- Summary basis: main branch after PR #208 was merged.
- Scope: docs-only summary of local real-LLM behavior observed for RelayMEM pass-through, metadata-only, snippet-bearing, and safety paths.

## Completed scope

- Local RelayLM to LM Studio manual evaluation was completed for:
  - pass-through baseline
  - metadata-only RelayMEM runtime context
  - snippet-bearing RelayMEM runtime context
  - recovery scene safety
  - unresolved reference safety
- Existing compile and smoke coverage was reused to support the manual checks.
- No runtime code changes were required for this phase.

## Local environment

- RelayLM repository checkout in WSL.
- LM Studio running on Windows host.
- RelayLM endpoint:
  - `http://127.0.0.1:8090/v1` was the intended default, but alternate local ports were also used during validation as needed.
- LM Studio backend endpoint from WSL:
  - `http://172.27.96.1:1234/v1`
- LM Studio loopback result from WSL:
  - `http://127.0.0.1:1234/v1` was not reachable in the evaluated environment.
- Evaluated local model:
  - `qwen3.5-9b-ud-japanese-imatrix`

## Validation

- Compile check:
  - `python -m compileall relaylm`
- RelayMEM runtime and diagnostics smokes:
  - `python scripts/relaylm_relaymem_runtime_payload_diff_smoke.py`
  - `python scripts/relaylm_relaymem_snippet_runtime_injection_apply_smoke.py`
  - `python scripts/relaylm_relaymem_runtime_ctx_injection_smoke.py`
  - `python scripts/relaylm_runtime_diagnostics_smoke.py`
  - `python scripts/relaylm_trace_success_smoke.py`
- Token budget / truncation smokes:
  - `python scripts/relaylm_token_budget_truncation_apply_smoke.py`
  - `python scripts/relaylm_token_budget_truncation_dry_run_smoke.py`
  - `python scripts/relaylm_token_budget_truncation_proxy_smoke.py`
  - `python scripts/relaylm_token_budget_truncation_smoke.py`
- Local backend checks:
  - `curl http://172.27.96.1:1234/v1/models`
  - `curl http://172.27.96.1:1234/v1/chat/completions`

## Local behavior results

### Pass-through

- No RelayMEM runtime context was applied.
- The backend response behaved like a normal direct LM Studio answer and did not use RelayMEM fixture content.
- Trace expectation matched:
  - `runtime_ctx_injection_result.applied=false`
  - `runtime_snippet_injection_result.applied=false`

### Metadata-only

- Metadata-only RelayMEM context affected the response through path/source hints.
- The backend did not appear to see bounded snippet body text.
- Trace expectation matched:
  - `runtime_ctx_injection_result.applied=true`
  - `runtime_snippet_injection_result.applied=false`
- This behavior was consistent with metadata-only `[RelayMEM Context]` insertion without snippet-bearing prompt content.

### Snippet-bearing

- Bounded snippet-bearing RelayMEM context affected the response.
- The local model used fixture content such as the default-off and explicit-gates constraints in its answer.
- Trace expectation matched:
  - `runtime_snippet_injection_result.applied=true`
  - `runtime_ctx_injection_result.applied=false`
- This behavior was consistent with `[RelayMEM Snippet Context]` insertion and metadata-only context skip on successful snippet apply.

## Safety behavior

### Recovery scene

- Recovery-scene requests failed closed.
- Snippet-bearing context was not injected.
- The local model responded without using RelayMEM fixture content.

### Unresolved reference

- Unresolved reference requests failed closed.
- Snippet-bearing context was not injected.
- The local model preferred clarification-style behavior over silent memory substitution.

### Tiny token budget smoke-only

- Tiny token budget behavior was confirmed through smoke coverage rather than a separate real-LLM curl run.
- The preserved-budget overflow path remained blocked as expected.
- Expected blocked reason in the smoke path:
  - `relaymem_snippet_context_would_break_token_budget`

## Key observations

- The local manual evaluation produced a clear behavioral separation between pass-through, metadata-only, and snippet-bearing modes.
- Metadata-only context can steer the response through source/path awareness without exposing bounded snippet body text.
- Snippet-bearing context can materially change the answer when bounded snippet evidence is injected.
- Safety gates for recovery scenes and unresolved references remained fail-closed in both smoke coverage and manual observations.
- WSL to Windows LM Studio connectivity may require a Windows host IP instead of loopback.

## Remaining limitations

- This phase was a manual behavior check, not a benchmark.
- Tiny token budget behavior was not re-run as a dedicated real-LLM curl case.
- Results are specific to one local environment and one local model.
- The evaluation does not validate semantic ranking quality, stale/conflicting memory handling, or broader memory policy presentation quality.
- No MEM/SOUL write or persistence behavior was evaluated in this phase.

## Next phase

- Add more model comparisons if local environments or routes change.
- Run a dedicated real-LLM tiny token budget check if prompt-level confirmation becomes necessary.
- Evaluate stale or conflicting memory behavior.
- Refine source/evidence presentation policy before expanding snippet-bearing usage.
