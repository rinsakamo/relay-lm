# llama.cpp / llama-server actual-model qualification

Status: current RelayLM 1.0 physical-qualification carriage for the operator-selected local llama.cpp condition. Repository carriage originates in #2409, the request/host hardening lineage is #2421/#2422, and the current one-command transaction harness is owned by #2430. Provider-neutral Stage R semantics remain owned by #1386 and `docs/reference/actual-model-stage-r-current.md`.

## Scope

This surface exists to run RelayLM's current actual-model Stage R on one explicitly attested local `llama-server` condition. It is an evaluation/laboratory boundary, not a production Cognitive Profile routing key and not a replacement for the generic OpenAI-compatible provider architecture.

The current physical transaction uses two related endpoint roots:

```text
llama-server origin: http://127.0.0.1:1234
OpenAI API base:     http://127.0.0.1:1234/v1
```

The endpoint namespaces are intentionally distinct:

```text
GET http://127.0.0.1:1234/health
GET http://127.0.0.1:1234/v1/models
GET http://127.0.0.1:1234/props
GET http://127.0.0.1:1234/slots
```

`/v1/props` and `/v1/slots` are not the current llama-server management routes.

LM Studio support and historical evidence remain under their existing owners. They are not fallback authority for this transaction.

The evaluation-only #2385 Continuity label-invariance diagnostic reuses this
same physical admission and one-command ownership carriage through:

```text
python3 -m tools.v1_stage_r_llama_cpp_continuity_label_invariance_wsl
```

That diagnostic changes only its model-facing Pass 2 transport and translates
the shadow `open_question` slot back to canonical `unresolved` before the
existing parser, deterministic boundary, and scorer. It does not change
production cognition wire or Core identity. The command is reserved for a
separate fresh physical owner; repository support alone does not run it.

## One-command LocalCodex/WSL operator surface

LocalCodex/WSL uses one repository-owned operator command exactly once, after
the separate Full Access/localhost permission preflight passes:

```text
python3 -m tools.v1_stage_r_llama_cpp_wsl
```

The operator flow is:

```text
LocalCodex
-> Full Access / localhost permission preflight
-> repository-owned wrapper exactly once
-> existing inner transaction
```

The wrapper is only a deterministic process/environment boundary. Before the
inner transaction is invoked, it:

- captures the real operator `HOME` as `OPERATOR_HOME`;
- creates one fresh runtime root directly under `/tmp`;
- creates only `<runtime-root>/home` as the child `runtime_home` and proves it
  writable;
- derives `<runtime-root>/workspace` and `<runtime-root>/artifacts` without
  creating either path;
- passes those fresh, nonexistent paths as `--workspace-root` and
  `--artifact-root` to the inner transaction;
- passes `OPERATOR_HOME/src/llama.cpp` and
  `OPERATOR_HOME/models/gguf/gemma-4-12B-it-Q4_K_M.gguf` explicitly;
- runs from the exact repository root with child `HOME=runtime_home` and
  `PYTHONPATH=<repo-root>/src` first, followed by the inherited `PYTHONPATH`;
- invokes the inner transaction once and returns its exit code unchanged.

The wrapper does not start `llama-server`, contact a provider/model, invoke the
Stage R host, interpret semantic classification, retry, replay, fall back, or
contact LM Studio. In particular, the wrapper/controller must never pre-create
the workspace or artifact roots: their fresh-nonexistent ownership belongs to
the existing inner transaction, which creates them with its fail-closed
`exist_ok=False` contract.

The existing inner transaction remains the citable physical laboratory and is
invoked by the wrapper as:

```text
python -m relaylm.actual_model_stage_r_llama_cpp_transaction
```

The transaction harness owns the mechanical lifecycle around the existing semantic host:

```text
clean exact RelayLM checkout
-> fail closed if 127.0.0.1:1234 is already occupied
-> attest local llama.cpp binary/revision/version/build and GPU
-> start one fresh llama-server
-> bounded non-generative readiness
-> derive the exact request-model from /v1/models
-> invoke relaylm.actual_model_stage_r_llama_cpp at most once
-> preserve the host summary unchanged
-> hash the one-lifetime server log
-> terminate only the transaction-owned PID
-> emit stage-r-llama-cpp-transaction-summary.json
```

The default local paths match the current WSL qualification laboratory:

```text
llama.cpp root: ~/src/llama.cpp
llama-server:   ~/src/llama.cpp/build/bin/llama-server
GGUF:           ~/models/gguf/gemma-4-12B-it-Q4_K_M.gguf
```

They are operator defaults, not portable semantic identity. CLI overrides remain available for a different explicitly authorized physical laboratory.

## Transaction ownership and process safety

One harness invocation owns at most one llama-server lifetime:

```text
one transaction
= one fresh llama-server process
= one PID
= one unique server log
= at most one citable Stage R host invocation
```

The harness first proves that `127.0.0.1:1234` is free. If another listener already owns that port, it emits `MECHANICAL_PRECONDITION_BLOCKED`, keeps the citable host invocation count at zero, and stops.

It never reuses or kills a pre-existing listener. It never uses `pkill`, `killall`, or port-wide termination. Cleanup terminates only the exact `subprocess.Popen` instance created by the current transaction; if graceful termination does not complete within the bounded cleanup window, only that same owned process is force-killed.

This design deliberately removes shared-server interpretation and shell process-management choices from Local Codex.

## Transaction-owned llama-server condition

The harness launches exactly this current class of server:

```text
-m <canonical GGUF>
--host 127.0.0.1
--port 1234
-ngl 999
-c 8192
-np 1
--no-context-shift
-lv 4
--log-timestamps
--log-file <unique one-lifetime log>
```

The exact PID, binary, source revision, version/build, command line, GPU identity and log path are recorded in the transaction summary. The citable host independently re-attests the physical condition before semantic execution.

## Backend-specific request realization

The semantic prompts, State/Continuity proposal schema, source checks, validators, lifecycle, oracle and scorer remain unchanged from the canonical OpenAI-compatible two-pass path.

For the pinned llama-server condition, provider-neutral reasoning `off` is realized on every semantic request as:

```json
{
  "reasoning_effort": "none"
}
```

The exact input-token counter preserves the same field. `chat_template_kwargs.enable_thinking=false` is not the current citable wire.

Pass 1 remains ordinary conversation. Pass 2 remains native `response_format.type=json_schema` structured-output transport.

## Exact serialized-input accounting and bounded waits

Every real Stage R request is counted through llama-server's exact Chat Completions input-token surface before generation. For the #2385 diagnostic, this count receives the final fixed-slot and `open_question`-aliased request body actually posted to the provider. Unknown or unattested request fields fail closed. There is no tokenizer-estimate fallback.

The current qualification uses a bounded **600 second wait per existing generation/counter request**:

- capability generation: 600 seconds;
- Stage R generation: 600 seconds;
- exact input-token counter request: 600 seconds.

This is a wait budget, not a retry policy. A timed-out request is not replayed. Semantic retry, replay, reseed and provider fallback remain zero.

## Mechanical readiness vs citable host admission

Before the citable host is entered, the transaction harness performs only non-generative work. It waits for `/health`, then reads `/health`, `/v1/models`, `/props` and `/slots`. The transaction-owned single-model server must expose exactly one model id and exactly one slot.

These probes exist to construct the exact host invocation and catch obvious mechanical failure. The existing `relaylm.actual_model_stage_r_llama_cpp` host remains the citable physical/runtime/artifact admission authority. It rechecks the endpoint, model identity, GGUF, context, slots, build information and required request capabilities before semantic execution.

No controller-side dummy completion, Thinking probe, JSON-Schema generation or semantic request is permitted outside the citable host.

## Citable host

The transaction harness invokes the existing host as a subprocess exactly once at most:

```text
python -m relaylm.actual_model_stage_r_llama_cpp ...
```

Freshly observed values are carried directly into that invocation, including:

- exact clean RelayLM checkout;
- `http://127.0.0.1:1234/v1`;
- exact `/v1/models` request-model id;
- canonical local GGUF;
- exact llama.cpp full revision/version/build;
- context `8192`;
- slots `1`;
- context shift disabled;
- exact transaction-owned log path;
- exact launch command and GPU/offload declarations;
- fresh workspace and artifact roots.

The semantic host then owns its existing bounded sequence:

```text
physical/runtime/artifact admission
-> exact input-token counter binding
-> one reasoning_effort=none capability generation
-> one native JSON-Schema capability generation
-> current Stage R exactly once
-> durable evidence and host classification
```

The transaction wrapper does not reinterpret `PASS`, `SEMANTIC_FAIL`, or `INFRA_INVALID`. The complete host summary is embedded unchanged in the terminal transaction summary.

## Classification and pre-host disposition

If the citable host is entered, its classification remains authoritative:

- `PASS`: physical/capability condition valid and all automated current Stage R gates pass;
- `SEMANTIC_FAIL`: usable physical inference completed but current semantic gates fail;
- `INFRA_INVALID`: no valid semantic verdict because admission/accounting/capability/transport/runtime evidence fails.

If the transaction cannot safely establish the owned laboratory before host entry, it reports `MECHANICAL_PRECONDITION_BLOCKED`; the citable host invocation count remains zero and no semantic verdict is fabricated.

An automated `PASS` still does not fabricate human/product-quality review. Current #1386 review authority remains separate.

## Terminal transaction evidence

The one-command harness writes:

```text
<artifact-root>/stage-r-llama-cpp-transaction-summary.json
```

The summary records, as available:

- RelayLM HEAD/tree;
- origin and OpenAI API base;
- server launch count and citable host invocation count;
- exact transaction-owned PID/binary/revision/version/build;
- exact launch command, GPU identity and unique server log path;
- non-generative probe facts and request-model id;
- complete citable host result and its artifact paths;
- final server exit state and server-log SHA256;
- retry/replay/fallback/LM-Studio/repository-mutation zero counts;
- wrapper disposition and host classification when a host verdict exists.

The host also retains its existing `stage-r-llama-cpp-summary.json`, physical binding, input-count observations, completion observations and Stage R artifacts. The wrapper summary does not replace or rewrite them.

## Invocation

For the current WSL laboratory, after fresh repository/GitHub authority and the
permission preflight have established that the intended v1 execution is
allowed, LocalCodex should need only the wrapper command:

```text
python3 -m tools.v1_stage_r_llama_cpp_wsl
```

The inner transaction's direct command remains useful for repository-local
tests and owner implementation diagnostics. Its explicit-root form is:

```text
python -m relaylm.actual_model_stage_r_llama_cpp_transaction \
  --repo-root <clean-exact-v1-checkout> \
  --workspace-root <fresh-nonexistent-workspace-path> \
  --artifact-root <fresh-nonexistent-artifact-path>
```

Those explicit roots must be nonexistent before the inner transaction starts;
the wrapper owns that operator-side proof for the canonical LocalCodex/WSL
path. The controller should read the emitted transaction JSON, reconcile it
into the owning physical Issue, and not manually replay any internal request.

> Start one clean laboratory, run one executable transaction, preserve its trace, then shut that laboratory down.
