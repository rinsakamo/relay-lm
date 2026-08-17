# RelayLM 1.0

RelayLM 1.0 is a greenfield persistent-character runtime.

> **Identity + Now + LM**

The model is a replaceable cognitive substrate, not the character. RelayLM persists identity, evidence, accepted current state, context authority, and validated state change outside the model.

## Product line

- `v1` is the RelayLM 1.0 product line.
- RelayLM 0.x remains preserved as historical/reference implementation material.
- 1.0 does not inherit 0.x runtime/module structure by default.
- Design evidence from issues #1257 and #1258 is intentionally carried forward.

## MVP

The first milestone is text-only character continuity:

```text
SOUL.md + Events + State
          |
          v
    Context Compiler
          |
          v
   CognitiveInput
          |
          v
       LLM x 1
          |
          v
  CognitiveOutput
   /           \
response   candidates
               |
               v
           Validator
               |
               v
             State
```

A successful MVP can stop and restart a character and continue naturally without replaying raw transcript history as truth.

## Run the current text MVP

Install the `v1` package and point RelayLM at one Character Package and one OpenAI-compatible provider:

```bash
pip install -e .

export RELAYLM_CHARACTER_DIR=examples/starter
export RELAYLM_PROVIDER_BASE_URL=http://127.0.0.1:1234/v1
export RELAYLM_PROVIDER_MODEL='<provider-model-id>'

relaylm
```

Optional provider authentication uses `RELAYLM_PROVIDER_API_KEY`. The server binds to `127.0.0.1:8090` by default; `RELAYLM_HOST` and `RELAYLM_PORT` can override this runtime setting.

The client endpoint is:

```text
POST /v1/chat/completions
```

The current OpenAI-compatible provider path supports both buffered `stream=false` responses and safe structured `stream=true` delivery. Streaming can expose safely decoded character text before the full structured provider object completes, while Assistant Event creation and State mutation remain blocked until the complete cognitive result is valid. Client-supplied history is not treated as RelayLM memory or Identity authority.

## Native evaluation

The current deterministic RelayLM-native evaluation foundation can be run with:

```bash
relaylm-eval
```

It emits machine-readable invariant checks by RelayLM boundary. The current report intentionally has no weighted composite score. See `docs/reference/evaluation.md` and #1247.

## Development workflow

The current `v1` development workflow is defined in `docs/reference/development-workflow.md`.

For semantic changes, the governing sequence is:

> **Meaning → Example → Test → Code → Docs → Audit**

Semantic behavior changes are test-first; behavior-preserving and docs-only transactions use lighter paths. One transaction owns one bounded responsibility, current-authority docs must not describe deferred behavior in the present tense, and merge is exact-head.

Repository-use conventions are in `docs/reference/repository-practices.md`. Durable architecture decisions are intentionally sparse under `docs/decisions/`, and `docs/authority-map.yaml` provides a non-enforcing owner → tests → docs navigation index.

See `docs/architecture/core.md`, `docs/contracts/openai-api.md`, `docs/reference/development-workflow.md`, and issue #1259.
