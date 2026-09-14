# Installed llama.cpp physical carriage

Status: repository carriage for #2903. This document defines the HOW surface
for a future installed-path physical owner; merging it does not start a model,
provider, GPU, llama-server, or RelayLM serve process.

## Public target

The only public invocation is the shared runner with the registered target:

```bash
python -m tools.relay_physical_run --target v1:installed-llama-cpp
```

The target registry resolves that name to
`tools.v1_installed_llama_cpp_wsl`. The shared runner retains ownership of
fresh protected-branch, clean-checkout, persistent-environment, target-module,
and serialized-resource gates. No arbitrary executable is accepted.

## Installed product boundary

The transaction binds an exact clean v1 checkout and its expected/derived Core,
builds one wheel from that checkout with the locally available build frontend,
and installs that wheel with `pip install --no-index --no-deps` into a fresh
transaction-owned virtual environment. The environment is not editable, has
no checkout `PYTHONPATH`, and is rejected if RelayLM imports from the source
checkout. Existing persistent-environment dependencies are copied into a
transaction-owned controlled overlay with RelayLM entries excluded; that
overlay is the only `PYTHONPATH` used by the installed subprocesses. A missing
local build frontend fails closed before any physical launch; the transaction
never downloads build or runtime dependencies.

The persistent physical Python environment is orchestration-only. RelayLM is
not installed into it. The installed console is used for both the non-generative
`relaylm doctor` preflight and `relaylm serve`, so the product under test is the
wheel artifact rather than a source import.

## Bounded transaction

The future owner receives one transaction-owned evidence root and one bounded
lifetime:

```text
exact checkout/Core binding
  -> wheel build
  -> fresh non-editable install
  -> existing llama.cpp server laboratory lifecycle
  -> non-generative /health, /v1/models, /props, /slots attestation
  -> installed relaylm doctor
  -> installed relaylm serve
  -> one buffered ordinary two-pass request
  -> one streaming ordinary two-pass request
  -> sanitized request/counter/state evidence
  -> owned cleanup
```

The existing Stage-R server helpers are reused only for GGUF verification,
llama-server identity, GPU identity, port ownership, readiness, launch, and
termination. They do not become the product-under-test. RelayLM uses its
production `provider.backend=llama_cpp` runtime loader, preflight, assembly,
`LlamaCpp` provider, and OpenAI-compatible API through a transaction-owned
forwarding boundary. No shadow provider, duplicate prompt, or duplicate parser
is introduced.

## Attestation and wire contract

The future transaction records the current target descriptor and live identity,
including llama.cpp revision/build, request model, exact GGUF identity,
chat-template/tokenizer identity, effective context, slot count, disabled
context shift, reasoning-off capability, native structured-output capability,
streaming capability, and disabled cache policy. Historical model and server
values are not scientific authority; the target descriptor and live endpoints
must be fresh at execution time.

Each ordinary generation is retained as sanitized controls, body hash, length,
and bounded response evidence. The ledger requires `cache_prompt=false` and
`reasoning_effort=none`; buffered Pass 1 is non-streaming, streaming Pass 1 is
streaming, and each Pass 2 carries the native strict production extraction
schema. The two public requests permit at most four semantic generations in
total. The harness performs no retry, replay, reseed, fallback, or repair
generation.

Input counting uses the production identity
`llama_cpp.chat-input.serialized-input.v1`. Each logical count operation keeps
its full request and empty-content framing endpoint calls, full counts, framing
counts, body hashes, and counter identity. The two endpoint calls are one
logical count operation, not duplicate scientific work.

The canonical current Stage-R neutral fixture and scenario machinery are copied
into the evidence root. Source fixtures, State, MEMORY, Continuity, prompts,
parsers, validators, and existing `v1:stage-r` and `v1:crystallization` targets
remain unchanged. Response-first behavior is recorded for later zero-generation
review; the harness does not declare product quality.

## Evidence and result boundary

Successful future evidence retains at least:

```text
binding.json                  transaction-summary.json
installed-artifact.json       runtime-config.yaml / runtime-config.sha256
doctor.json                   relaylm-serve.log / llama-server.log
runtime-attestation.json      provider-request-ledger.json
input-count-ledger.json       buffered-execution.json
streaming-execution.json      state-continuity-before-after.json
cleanup.json
```

Every retained file has a SHA-256 receipt in the terminal summary. The
transaction emits `EVIDENCE_RECORDED` only when the bounded successful path and
required evidence exist, and `PHYSICAL_INVALID` for a failed or unverifiable
physical transaction. Those dispositions are not a quality or qualification
PASS; a separate zero-generation review owner decides that question.

Cleanup terminates only the transaction-owned RelayLM and llama-server
processes, closes the transaction proxy, preserves the evidence root, and
records exit/ownership facts. No future physical owner is created by #2903.
