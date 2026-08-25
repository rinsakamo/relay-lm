# RelayLM 1.0

RelayLM 1.0 is a greenfield persistent-character runtime. Architecturally, it acts as a model-agnostic **Cognitive Proxy Runtime** around a replaceable language model.

> **Identity + Now + LM**

The model is a replaceable cognitive substrate, not the character. RelayLM persists identity, evidence, accepted current state, context authority, and validated state change outside the model.

## One runtime, two ways to see it

For an end user, the simplest mental model is: **give a compatible LM a persistent character**. `SOUL.md` supplies a stable identity; governed State and Continuity supply the accepted "now"; the provider model can change underneath them.

But a RelayLM identity does not need to imitate a person. The same stable `SOUL.md` can describe a deliberately machine-like cognitive role — for example, a strict summarizer, reviewer, research assistant, or structured record-writing system. In that sense, a character is one **cognitive persona**, not the limit of the runtime.

For developers and professional deployments, RelayLM is the middleware layer that decides which stable identity or role and which governed context reach the model, then decides which proposed changes are allowed back into RelayLM-owned authority.

```text
application / user
      |
      v
   RelayLM
identity / role + governed context + State / Continuity
      |
      v
replaceable LM
```

A small local model can power approachable character experimentation, while the same RelayLM-owned identity, role, and accepted state can later be presented to a larger compatible model. The model itself is not what persists or "grows"; continuity lives in RelayLM-owned artifacts and authority around it.

> **Character is one cognitive persona. RelayLM is the cognitive proxy around the model.**

## Product line

- `v1` is the RelayLM 1.0 product line.
- RelayLM 0.x remains preserved as historical/reference implementation material.
- 1.0 does not inherit 0.x runtime/module structure by default.
- Design evidence from issues #1257 and #1258 is intentionally carried forward.

## Core 1.0 turn

The current ordinary release/reference architecture is two-pass and reuses the same loaded online model sequentially:

```text
SOUL.md + Events + State
          |
          v
    Context Compiler
          |
          v
   CognitiveInput
      /       \
     v         v
 Pass 1       Pass 2
conversation  semantic extraction
     |         |
     v         v
 response   State / Continuity proposals
               |
               v
        deterministic validation
               |
               v
        State / Continuity authority
```

Pass 1 owns the visible conversation. Pass 2 performs immediate semantic extraction from the governed turn plus the lower-authority Pass 1 response. RelayLM, not the model, owns proposal parsing, validation, lifecycle, persistence, and canonical authority.

A valid Pass 1 response remains valid if Pass 2 later fails or is rejected. A successful persistent-character runtime can stop and restart without replaying raw transcript history as truth.

## Build and run the current v1 artifact

No public publication channel is assumed yet. From a clean `v1` source checkout, build the current distribution artifacts and install the wheel non-editably:

```bash
python -m pip install build
python -m build --wheel --sdist
python -m venv .relaylm-runtime
.relaylm-runtime/bin/python -m pip install dist/relaylm-*.whl
```

Keep the Character Package outside the installed Python package and point the runtime at its filesystem path:

```bash
export RELAYLM_CHARACTER_DIR=/absolute/path/to/character
export RELAYLM_PROVIDER_BASE_URL=http://127.0.0.1:1234/v1
export RELAYLM_PROVIDER_MODEL='<provider-model-id>'

.relaylm-runtime/bin/relaylm doctor
.relaylm-runtime/bin/relaylm serve
```

With no calibrated profile selected, the Core 1.0 cognition topology defaults to `two_pass`; this topology default does not manufacture reasoning, decoding, output-budget, or context-window values. Explicit pass controls may be carried through runtime YAML, while calibrated profiles remain #1388 authority.

Equivalent machine/runtime settings can be supplied through the versioned runtime YAML selected with `--config PATH` or `RELAYLM_CONFIG`. See `docs/contracts/runtime-configuration.md` for schema/precedence and `docs/contracts/runtime-operator.md` for `doctor` / `serve` behavior.

Optional provider authentication uses `RELAYLM_PROVIDER_API_KEY`. The server binds to `127.0.0.1:8090` by default; `RELAYLM_HOST` and `RELAYLM_PORT` can override this runtime setting. `examples/starter` is a source-checkout example, not an installed-artifact runtime dependency.

The client endpoint is:

```text
POST /v1/chat/completions
```

Buffered and streaming requests use the same selected cognition topology. In two-pass streaming, safely decoded Pass 1 text may be delivered before Pass 2 finishes, while State/Continuity mutation still requires a valid, current Pass 2 result. Client-supplied history is not treated as RelayLM memory or Identity authority.

## Native evaluation

The deterministic RelayLM-native evaluation foundation can be run from the installed artifact with:

```bash
.relaylm-runtime/bin/relaylm-eval
```

It emits machine-readable invariant checks by RelayLM boundary and intentionally has no weighted composite score. See `docs/reference/evaluation.md` and #1247.

Actual-model Stage R quality/evidence is a separate process from this deterministic native suite.

## Development workflow

The current `v1` development workflow is defined in `docs/reference/development-workflow.md`.

For semantic changes, the governing sequence is:

> **Meaning → Example → Test → Code → Docs/Authority → Audit**

Semantic behavior changes are test-first; behavior-preserving and docs-only transactions use lighter paths. One transaction owns one bounded responsibility, current-authority docs must not describe deferred behavior in the present tense, and merge is exact-head. A transaction converges its own semantic owner's authority; global views are derived on demand and are never hand-maintained.

Repository-use conventions are in `docs/reference/repository-practices.md`. Durable architecture decisions are intentionally sparse under `docs/decisions/`, and `.ai/authority/` holds one owner-local validated authority declaration per semantic owner.

`ARCHITECTURE.md` is a generated projection of repository authority, materialized at version/release boundaries rather than hand-synchronized by every transaction.

See `docs/architecture/core.md`, `docs/contracts/cognition-pass-execution.md`, `docs/contracts/openai-api.md`, `docs/contracts/runtime-configuration.md`, `docs/contracts/release-distribution.md`, and issue #1259.