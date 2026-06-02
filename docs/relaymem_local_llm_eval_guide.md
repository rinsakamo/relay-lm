# RelayMEM Local LLM Evaluation Guide

## Purpose

This guide describes a local manual evaluation for comparing two RelayMEM runtime paths:

- Metadata-only RelayMEM Context, where RelayLM can insert `[RelayMEM Context]` with path/reason metadata.
- Snippet-bearing RelayMEM Snippet Context, where RelayLM can insert `[RelayMEM Snippet Context]` with bounded MEM snippet evidence when all gates are enabled.

This is not a quality benchmark. It is an initial manual smoke / behavior check to see how a real local LLM responds when RelayMEM context changes from metadata-only hints to bounded snippet-bearing hints.

## Prerequisites

- Local RelayLM repository checkout.
- Python virtual environment for RelayLM.
- RelayLM installed or runnable from the repository.
- LM Studio running an OpenAI-compatible local backend.
- Optional OpenWebUI connected to RelayLM for UI-based checks.
- Example LM Studio backend URL: `http://127.0.0.1:1234/v1`.
- Example RelayLM URL: `http://127.0.0.1:8090/v1`.

## Repo setup commands

Use your local repository path and virtual environment name. Example:

```bash
cd ~/work/relay-lm
source .venv/bin/activate  # adjust the venv path/name for your environment
git switch main
git pull origin main
python -m compileall relaylm
```

If you use the installed console script, confirm it is available:

```bash
relaylm --help
```

## Minimal local memory fixture

Create a small read-only MEM fixture under the repository root or another local test directory:

```bash
mkdir -p memory/mem/projects memory/raw
cat > memory/mem/index.md <<'EOF'
# MEM Index

- memory/mem/projects/relaymem.md
EOF

cat > memory/mem/log.md <<'EOF'
# MEM Log

Manual local LLM evaluation fixture.
EOF

cat > memory/mem/projects/relaymem.md <<'EOF'
# RelayMEM local eval note

RelayMEM is a read-oriented memory layer for RelayLM. In this local evaluation,
bounded snippets should help the assistant mention that snippet-bearing context is
explicitly gated, default-off, and should be treated as contextual hints rather
than authoritative facts.
EOF
```

The `memory/raw/` directory can exist, but bounded snippet extraction should use supported MEM page scopes such as `memory/mem/projects/`, not raw memory pages.

## Config profiles / config snippets

Start from `config.example.yaml` or your current local config. The examples below show only the relevant sections. Keep your existing backend/model route/profile fields as needed.

### 1. Pass-through baseline

Use this to confirm basic RelayLM to LM Studio forwarding without RelayMEM runtime context.

```yaml
backends:
  local_backend:
    type: openai_compatible
    base_url: http://127.0.0.1:1234/v1
    api_key: dummy
    default_model: local-model

model_routes:
  relaylm-default:
    backend: local_backend
    backend_model: local-model
    mode: pass_through

memory:
  root_path: .
  store_enabled: false
  retrieval_dry_run_only: true
  ctx_block_apply_enabled: false
  snippet_extraction_enabled: false
  snippet_dry_run_only: true
  snippet_apply_enabled: false
  snippet_runtime_injection_enabled: false
  snippet_runtime_dry_run_only: true
```

Expected payload behavior: no `[RelayMEM Context]` and no `[RelayMEM Snippet Context]`.

### 2. RelayMEM metadata-only

Use this to allow metadata-only RelayMEM runtime context while keeping snippet runtime injection disabled.

```yaml
memory:
  root_path: .
  store_enabled: true
  retrieval_dry_run_only: false
  ctx_block_apply_enabled: true
  candidate_limit: 3
  token_budget_hint: 800
  snippet_extraction_enabled: true
  snippet_dry_run_only: false
  snippet_apply_enabled: true
  snippet_runtime_injection_enabled: false
  snippet_runtime_dry_run_only: true
  snippet_budget: 512
  max_snippet_chars: 512
  max_snippet_candidates: 3
```

Expected payload behavior: a metadata-only `[RelayMEM Context]` may be inserted before the latest user message when the request is eligible. Snippet text should not be inserted.

### 3. RelayMEM snippet-bearing enabled

Use this to enable the gated snippet-bearing runtime path.

```yaml
memory:
  root_path: .
  store_enabled: true
  retrieval_dry_run_only: false
  ctx_block_apply_enabled: true
  candidate_limit: 3
  token_budget_hint: 800
  snippet_extraction_enabled: true
  snippet_dry_run_only: false
  snippet_apply_enabled: true
  snippet_runtime_injection_enabled: true
  snippet_runtime_dry_run_only: false
  snippet_budget: 512
  max_snippet_chars: 512
  max_snippet_candidates: 3
  token_budget_truncation_enabled: false
```

Expected payload behavior: `[RelayMEM Snippet Context]` may be inserted before the latest user message when all gates pass. The metadata-only `[RelayMEM Context]` should be skipped when snippet context is applied.

## Important config gates

- `memory.store_enabled`: enables file-backed RelayMEM store diagnostics and candidate discovery.
- `memory.retrieval_dry_run_only`: must be `false` for runtime apply paths.
- `memory.ctx_block_apply_enabled`: must be `true` for metadata-only or snippet runtime context insertion.
- `memory.snippet_extraction_enabled`: enables bounded snippet evidence extraction.
- `memory.snippet_dry_run_only`: must be `false` for snippet apply readiness to become eligible.
- `memory.snippet_apply_enabled`: must be `true` for snippet apply readiness.
- `memory.snippet_runtime_injection_enabled`: must be `true` for prompt-visible snippet context.
- `memory.snippet_runtime_dry_run_only`: must be `false` for prompt-visible snippet context.
- `memory.token_budget`: optional hard token budget used by truncation / preserved-budget checks.
- `memory.token_budget_truncation_enabled`: if `true`, final payload still passes through token budget truncation after runtime context insertion.

## RelayLM startup

Use the project’s current config loading method. Common options:

```bash
relaylm --config config.yaml
```

or:

```bash
python -m relaylm.app --config config.yaml
```

or with uvicorn factory mode:

```bash
RELAYLM_CONFIG=config.yaml uvicorn relaylm.app:create_app --factory --host 127.0.0.1 --port 8090
```

Confirm LM Studio is serving an OpenAI-compatible endpoint before starting the evaluation.

## curl examples

### Basic design-talk request

```bash
curl http://127.0.0.1:8090/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "relaylm-default",
    "messages": [
      {
        "role": "user",
        "content": "What should I remember about the RelayMEM local eval note?"
      }
    ],
    "metadata": {
      "scene_state": {
        "scene_type": "design_talk",
        "confidence": 0.95,
        "stability": 0.9
      }
    },
    "stream": false
  }'
```

### Recovery scene safety check

```bash
curl http://127.0.0.1:8090/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "relaylm-default",
    "messages": [
      {"role": "user", "content": "Recover the current context using RelayMEM."}
    ],
    "metadata": {
      "scene_state": {"scene_type": "recovery"}
    },
    "stream": false
  }'
```

### Unresolved reference safety check

```bash
curl http://127.0.0.1:8090/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "relaylm-default",
    "messages": [
      {"role": "user", "content": "Which one was that RelayMEM note?"}
    ],
    "metadata": {
      "scene_state": {"scene_type": "design_talk"}
    },
    "stream": false
  }'
```

The unresolved reference request should avoid silently using memory as a substitute for clarification.

## Expected observations

- Pass-through baseline:
  - No RelayMEM context should be prompt-visible.
  - Trace may still include general request diagnostics depending on config.
- Metadata-only RelayMEM:
  - Backend payload should include `[RelayMEM Context]` when eligible.
  - Content should be source/path/reason metadata, not bounded snippet text.
  - `runtime_ctx_injection_result.applied` should be `true` when inserted.
  - `runtime_snippet_injection_result.applied` should be `false`.
- Snippet-bearing RelayMEM:
  - Backend payload should include `[RelayMEM Snippet Context]` when eligible.
  - The inserted context should use bounded snippet evidence.
  - Metadata-only `[RelayMEM Context]` should not duplicate the snippet context.
  - `runtime_snippet_injection_result.applied` should be `true` when inserted.
- Trace metadata to inspect:
  - `relaymem_retrieval_artifact`
  - `evidence_envelope`
  - `runtime_ctx_injection_result`
  - `runtime_snippet_injection_result`

## Behavior comparison checklist

- Does the answer use the snippet when snippet-bearing context is enabled?
- Does the answer over-trust memory, or does it treat memory as contextual hints?
- Does the answer preserve source awareness when discussing remembered content?
- Does recovery/formal/medical scene safety block memory injection as expected?
- Does an unresolved reference avoid silent memory resolution?
- Does token budget truncation still preserve the latest user message?
- Does metadata-only mode avoid quoting snippet text?
- Does snippet-bearing mode avoid duplicating metadata-only RelayMEM context?

## Safety / rollback

To roll back toward safer behavior, disable gates in this order:

```yaml
memory:
  snippet_runtime_injection_enabled: false
  snippet_runtime_dry_run_only: true
  ctx_block_apply_enabled: false
  store_enabled: false
```

Additional safety toggles:

```yaml
memory:
  snippet_apply_enabled: false
  snippet_dry_run_only: true
  snippet_extraction_enabled: false
```

Use the metadata-only or pass-through profiles above if snippet-bearing responses look unstable.

## What not to conclude yet

- This is not a benchmark.
- This does not validate semantic ranking quality.
- This does not validate stale or conflicting memory resolution.
- This does not validate MEM write, SLP write, SOUL update, or persistence behavior.
- This does not replace the runtime payload diff smoke; it complements it with real LLM behavior observations.

## Next after local eval

- Record observations with config profile, model name, prompt, response, trace snippets, and any safety notes.
- Add an MVP-29 local behavior summary if the manual results are stable enough to summarize.
- Consider a fixture-based response diff smoke only if local outputs are stable and meaningful.
- Define source/evidence presentation policy before widening snippet-bearing runtime apply.
