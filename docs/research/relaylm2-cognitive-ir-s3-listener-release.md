# RelayLM 2.0 Cognitive IR S3 — listener-release mechanical correction

Owner: #2485. Parent scientific owner: #2211. Physical procedure owner: #2363.

This document records a mechanical execution-harness correction only. It does not reinterpret the partial #2478 S3 evidence, change the #2461 scientific panels or thresholds, authorize a replacement physical run, or mutate RelayLM v1 / architecture authority.

## Historical #2478 terminal remains immutable

The one-shot #2478 campaign completed the first `shared` shard's declared model work: 123 semantic completions, 246 exact input-token requests, 123 lightweight live-binding checks, and two full material attestations. The owned llama-server then terminated by SIGINT with exit code 0.

The transaction nevertheless marked the shard incomplete because its post-cleanup `listener_released` check called the inherited `_port_is_free()` helper. That helper answers a different question by attempting a fresh TCP `bind(127.0.0.1:1234)`.

Immediately after the wrapper returned, read-only operator inspection found no llama-server process, no TCP LISTEN socket on port 1234, and a free lifecycle lock. The original summary remains exactly `S3_INCOMPLETE`, non-citable, and must not be rewritten or promoted retroactively.

## Correct lifecycle question

For the S3 multi-server shard boundary:

```text
no process is LISTENing on 127.0.0.1:1234
```

is not equivalent to:

```text
a newly created socket can bind 127.0.0.1:1234 immediately
```

Recently closed TCP connection state may affect a naive bind after a request-heavy server lifetime even after the LISTEN socket and owning process are gone. Listener release must therefore be observed directly.

The corrected WSL path routes through a small compatibility transaction envelope. At every location where the frozen transaction historically used `_port_is_free`, the envelope supplies a listener predicate based on a loopback TCP connection probe:

```text
connect succeeds
  -> listener still present

ECONNREFUSED
  -> listener absent

any other socket outcome
  -> fail closed
```

This replacement changes no semantic call, prompt, seed, representation, score, retry policy, runtime/material attestation, shard order, server launch contract, or evidence claim. If a later planned llama-server cannot bind for some other reason, normal startup fails closed; the harness does not retry or rescue it.

## Scientific boundary after #2478

#2461 required an incomplete/protocol-defect campaign to remain non-citable until a wholly new preregistration is created. Therefore #2485 only repairs the mechanical execution surface. It must not execute S3 or create a replacement physical owner.

After this fix merges and CI is green, #2211 may open a separate preregistration owner for a new campaign. That preregistration must not tune its science from partial #2478 result metrics. A later physical owner can exist only after that new preregistration and any required executable binding are separately frozen.
