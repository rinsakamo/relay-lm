# RelayMEM Runtime Payload Diff Evaluation Smoke

## Purpose

This evaluation smoke compares RelayMEM backend payloads for two runtime paths:

- Metadata-only runtime injection, where RelayMEM inserts a `[RelayMEM Context]` system message with path/reason metadata only.
- Snippet-bearing runtime injection, where RelayMEM inserts a gated `[RelayMEM Snippet Context]` system message with bounded snippet evidence.

The smoke is not a quality benchmark. It validates payload shape, trace diagnostics, gate behavior, and safety cases before manual response-quality evaluation.

## Fixture

The smoke builds a temporary file-backed memory store with a minimal MEM layout:

```text
memory/mem/index.md
memory/mem/log.md
memory/mem/projects/relaymem.md
```

The project page includes a short sentinel snippet so the script can assert whether bounded snippet text reached the backend payload. Requests set `metadata.scene_state.scene_type` to `design_talk` unless a safety case needs another scene.

## Compared paths

### A. Metadata-only path

Config characteristics:

- `ctx_block_apply_enabled: true`
- `retrieval_dry_run_only: false`
- `snippet_apply_enabled: true`
- `snippet_dry_run_only: false`
- `snippet_runtime_injection_enabled: false`
- `snippet_runtime_dry_run_only: true`

Expected backend payload:

- Contains `[RelayMEM Context]` when metadata-only runtime CTX injection is eligible.
- Does not contain `[RelayMEM Snippet Context]`.
- Does not contain the bounded snippet sentinel text.
- `runtime_ctx_injection_result.applied` is `true`.
- `runtime_snippet_injection_result.applied` is `false`.

### B. Snippet-bearing path

Config characteristics:

- `ctx_block_apply_enabled: true`
- `retrieval_dry_run_only: false`
- `snippet_apply_enabled: true`
- `snippet_dry_run_only: false`
- `snippet_runtime_injection_enabled: true`
- `snippet_runtime_dry_run_only: false`

Expected backend payload:

- Contains exactly one `[RelayMEM Snippet Context]` system message.
- Inserts the snippet system message before the latest user message.
- Contains bounded snippet text from the evidence pipeline.
- Does not also contain a metadata-only `[RelayMEM Context]` message.
- `runtime_snippet_injection_result.applied` is `true`.
- `runtime_ctx_injection_result.applied` is `false` because metadata-only context is skipped after snippet context applies.

## Safety cases

The same smoke also checks that snippet-bearing injection is skipped for:

- Recovery scene.
- RelayREF unresolved reference.
- Preserved token-budget overflow.
- Default snippet runtime injection disabled configuration.
- Original request payload mutation attempts.

The preserved-budget case expects `runtime_snippet_injection_result.blocked_reasons` to include `relaymem_snippet_context_would_break_token_budget` and verifies that bounded snippet text does not reach the backend payload.

## Diagnostic summary output

Each case prints one JSON summary line prefixed with `payload-diff-summary`. The summary includes:

- Case name.
- Backend message count.
- Inserted system headings.
- Whether snippet context was applied.
- Whether metadata-only context was applied.
- `runtime_snippet_injection_result.applied`.
- `runtime_ctx_injection_result.applied`.
- `token_budget_truncation.applied` when present.
- Trace metadata keys.

## How to run

```bash
python scripts/relaylm_relaymem_runtime_payload_diff_smoke.py
```

Recommended companion checks:

```bash
python scripts/relaylm_relaymem_snippet_runtime_injection_apply_smoke.py
python scripts/relaylm_relaymem_runtime_ctx_injection_smoke.py
python scripts/relaylm_runtime_diagnostics_smoke.py
python scripts/relaylm_trace_success_smoke.py
```

## Non-goals

- This smoke does not compare answer quality.
- This smoke does not call OpenWebUI or LM Studio.
- This smoke does not write or update MEM/SOUL state.
- This smoke does not validate semantic ranking or stale/conflicting memory behavior.

Those should be handled in later manual and behavioral evaluation phases.
