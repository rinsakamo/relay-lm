# Two-turn actual-model diagnostic carriage

Status: evaluation-only canonical physical orchestration for bounded RelayLM 1.0 llama.cpp diagnostics.

This carriage exists so diagnostic owners do not copy the Stage R T1/T2 execution loop, generation accounting, fixture setup, or protocol classification. It is not a product runtime path and it does not define any semantic answer.

## Contract

A specialization supplies one explicitly owned provider strategy for the second extraction. The carriage owns only this sequence:

```text
T1 production Pass 1       <= 1
T1 production Pass 2       <= 1
T1 Pass 2 must COMMIT
T2 production Pass 1       <= 1
T2 diagnostic Pass 2       <= 1
--------------------------------
semantic generations       <= 4
T3                          = 0
retry/replay/reseed/fallback = 0
```

T1 runs through the ordinary production two-pass provider path. If T1 extraction does not commit, the carriage terminates `PRODUCTION_PARITY_NOT_REALIZED_NO_INFERENCE` and never executes T2.

The diagnostic specialization owns only T2 Pass 2 request construction, diagnostic artifacts, and parsing. It must derive that request from its canonical diagnostic owner rather than rewriting production prompts or schemas inside the carriage.

## Mechanical validity

A completed transaction may report `PROTOCOL_VALID_SEMANTIC_REVIEW_REQUIRED` only when:

- T2 extraction commits;
- exactly two extraction calls occurred;
- exactly one diagnostic Pass 2 generation occurred;
- exactly four completion observations exist;
- the recorded completion evidence satisfies the current explicit reasoning-OFF contract.

Otherwise the result is a no-inference protocol/provenance classification. The host never converts those mechanical facts into a product-quality or causal semantic verdict.

## Shared physical boundary

The carriage reuses the current repository-owned llama.cpp qualification infrastructure for:

- clean checkout identity and frozen Core observation;
- current Stage R semantic authority;
- target/model/GPU/server admission;
- serialized-input counting and completion observation;
- fresh fixture copy;
- Continuity runtime;
- request evidence;
- deterministic teardown.

It does not own server discovery, model selection, prompt semantics, candidate parsing rules, Continuity materialization, or benchmark scoring.

## Direct convergence

Diagnostic specializations must not use runtime monkeypatching, import hooks, private-client replacement, prompt substring surgery, hidden fallbacks, or repo-external semantic drivers. A new diagnostic either plugs an explicit strategy into this carriage or changes the canonical owner that actually owns the behavior.

> Share the physical experiment loop; keep the scientific delta explicit and owner-local.
