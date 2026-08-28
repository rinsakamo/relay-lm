# RelayLM 1.0

**English** | [日本語](README.ja.md)

RelayLM 1.0 is a greenfield persistent-character runtime. Architecturally, it acts as a model-agnostic **[Cognitive Proxy Runtime](docs/architecture/core.md)** around a replaceable language model.

> **Identity + Now + LM**

The model is a replaceable cognitive substrate, not the character. RelayLM persists identity, evidence, accepted current state, context authority, and validated state change outside the model.

## One runtime, two ways to see it

For an end user, the simplest mental model is: **give a compatible LM a persistent character**. A Cognitive Package supplies stable identity or role authority through `SOUL.md`; governed State and Continuity supply the accepted "now"; the provider model can change underneath them.

But a RelayLM identity does not need to imitate a person. The same Cognitive Package boundary can describe a deliberately machine-like cognitive role — for example, a strict summarizer or structured record-writing system. In that sense, a Character is one specialization of Cognitive Package, not the limit of the runtime.

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

A small local model can power approachable character experimentation, while the same RelayLM-owned identity, role, and accepted state can later be presented to a larger compatible model. The model itself is not what persists or "grows": stable identity and accepted state remain RelayLM-owned, while bounded Continuity remains RelayLM-owned temporary authority.

> **Character is one Cognitive Package specialization. RelayLM is the cognitive proxy around the model.**

## Product line

- `v1` is the RelayLM 1.0 product line.
- RelayLM 0.x remains preserved as historical/reference implementation material.
- 1.0 does not inherit 0.x runtime/module structure by default.
- Design evidence from issues [#1257](https://github.com/rinsakamo/relay-lm/issues/1257) and [#1258](https://github.com/rinsakamo/relay-lm/issues/1258) is intentionally carried forward.

## Start with a first-party Starter

Core 1.0 ships four small [Starter Cognitive Packages](docs/reference/starter-packages.md) as part of the installed artifact so a first run does not require authoring package files from scratch:

- `blank` — minimal neutral Character starting point, intentionally easy to fork;
- `relm` — complete Character example;
- `fact-summarizer` — non-personal general cognitive machine;
- `medical-soap` — domain-specific SOAP documentation structurer, not clinical decision authority.

The Character and machine-like Starters use the same production Cognitive Package loader. Their files contain portable semantic package data only; provider URLs, physical model IDs, API keys, host policy, and other machine/runtime configuration stay outside the package.

The build/run steps below show how to materialize a bundled Starter into an ordinary editable filesystem directory. The installed Python package is the distribution source for the first-party assets, not the place where user-owned package state is edited.

## Core 1.0 turn

The current ordinary release/reference architecture is [two-pass](docs/contracts/cognition-pass-execution.md) and reuses the same loaded online model sequentially:

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

For a first run, copy a bundled Starter out of the installed artifact instead of writing a package from scratch. For example, create the complete Character Starter:

```bash
.relaylm-runtime/bin/python -c 'from relaylm.starters import materialize_starter_package; materialize_starter_package("relm", "./relm")'
```

Or create a deliberately non-personal machine-like Starter:

```bash
.relaylm-runtime/bin/python -c 'from relaylm.starters import materialize_starter_package; materialize_starter_package("fact-summarizer", "./fact-summarizer")'
```

The copied directory is normal user-owned Cognitive Package data and may be inspected or edited. The current #1446 operator schema still uses the compatibility name `character.directory` / `RELAYLM_CHARACTER_DIR` for the selected root, but since #1890 that root is opened through the general Cognitive Package loader and may be Character-like or machine-like.

```bash
export RELAYLM_CHARACTER_DIR="$PWD/relm"
export RELAYLM_PROVIDER_BASE_URL=http://127.0.0.1:1234/v1
export RELAYLM_PROVIDER_MODEL='<provider-model-id>'

.relaylm-runtime/bin/relaylm doctor
.relaylm-runtime/bin/relaylm serve
```

To run `fact-summarizer` instead, point `RELAYLM_CHARACTER_DIR` at that materialized root. Public OpenAI `model` -> Cognitive Profile routing and the final `profiles[].name` + `root` configuration are owned separately by [#1889](https://github.com/rinsakamo/relay-lm/issues/1889); this README does not present that unfinished routing surface as current behavior.

With no calibrated profile selected, the Core 1.0 cognition topology defaults to `two_pass`; this topology default does not manufacture reasoning, decoding, output-budget, or context-window values. Explicit pass controls may be carried through runtime YAML, while calibrated profiles remain [#1388](https://github.com/rinsakamo/relay-lm/issues/1388) authority.

Equivalent machine/runtime settings can be supplied through the versioned runtime YAML selected with `--config PATH` or `RELAYLM_CONFIG`. See [`runtime-configuration.md`](docs/contracts/runtime-configuration.md) for schema/precedence and [`runtime-operator.md`](docs/contracts/runtime-operator.md) for `doctor` / `serve` behavior.

Optional provider authentication uses `RELAYLM_PROVIDER_API_KEY`. The server binds to `127.0.0.1:8090` by default; `RELAYLM_HOST` and `RELAYLM_PORT` can override this runtime setting. See [`starter-packages.md`](docs/reference/starter-packages.md) for the full first-party catalog, portability boundary, and installed-artifact behavior.

The [OpenAI-compatible client endpoint](docs/contracts/openai-api.md) is:

```text
POST /v1/chat/completions
```

Buffered and streaming requests use the same selected cognition topology. In two-pass streaming, safely decoded Pass 1 text may be delivered before Pass 2 finishes, while State/Continuity mutation still requires a valid, current Pass 2 result. Client-supplied history is not treated as RelayLM memory or Identity authority.

## Native evaluation

The deterministic RelayLM-native evaluation foundation can be run from the installed artifact with:

```bash
.relaylm-runtime/bin/relaylm-eval
```

It emits machine-readable invariant checks by RelayLM boundary and intentionally has no weighted composite score. See [`evaluation.md`](docs/reference/evaluation.md) and [#1247](https://github.com/rinsakamo/relay-lm/issues/1247).

Actual-model Stage R quality/evidence is a separate process from this deterministic native suite.

## Development workflow

The current `v1` development workflow is defined in [`development-workflow.md`](docs/reference/development-workflow.md).

For semantic changes, the governing sequence is:

> **Meaning → Example → Test → Code → Docs/Authority → Audit**

Semantic behavior changes are test-first; behavior-preserving and docs-only transactions use lighter paths. One transaction owns one bounded responsibility, current-authority docs must not describe deferred behavior in the present tense, and merge is exact-head. A transaction converges its own semantic owner's authority; global views are derived on demand and are never hand-maintained.

Repository-use conventions are in [`repository-practices.md`](docs/reference/repository-practices.md). Durable architecture decisions are intentionally sparse under [`docs/decisions/`](docs/decisions/), and [`.ai/authority/`](.ai/authority/) holds one owner-local validated authority declaration per semantic owner.

[`ARCHITECTURE.md`](ARCHITECTURE.md) is a generated projection of repository authority, materialized at version/release boundaries rather than hand-synchronized by every transaction.

See [`core.md`](docs/architecture/core.md), [`cognition-pass-execution.md`](docs/contracts/cognition-pass-execution.md), [`openai-api.md`](docs/contracts/openai-api.md), [`runtime-configuration.md`](docs/contracts/runtime-configuration.md), [`release-distribution.md`](docs/contracts/release-distribution.md), and issue [#1259](https://github.com/rinsakamo/relay-lm/issues/1259).
