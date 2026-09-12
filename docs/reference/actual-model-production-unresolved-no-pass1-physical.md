# Production unresolved-only no-Pass1 physical specialization

This component is the v1-specific physical adapter for the #2697 causal discriminator.
It does not own the shared physical environment, queue, resource serialization, exact
checkout verification, or final fresh-ref gate.

## Public execution surface

After this component is merged and a separate exactly-once physical owner authorizes a
run, invoke it through the shared physical runner:

```bash
python -m tools.relay_physical_run \
  --target v1:unresolved-no-pass1 \
  -- \
  --retained-formation-artifact <repo-external-canonical-envelope.json>
```

The target registration maps `v1:unresolved-no-pass1` to the thin v1 WSL adapter.
The shared `physical_execution_queue` authority owns target dispatch, persistent Python,
queue/resource ownership, exact-checkout ancestry, environment identity and the final
pre-invoke fresh-ref gate.

## v1-specific responsibility

The specialization owns only:

- fresh production T1 and T2 Pass 1 ordering through the already-merged generic
  two-turn diagnostic carriage;
- binding the canonical #2529 retained-formation envelope to current Stage-R T2;
- selecting the #2697 no-Pass1 request builder for the second extraction;
- retaining the unresolved-only baseline and treatment request bodies/hashes, factor
  receipt, binding receipt and raw completion;
- sending exactly `no_pass1_overlay_body` for diagnostic T2 Pass 2;
- parsing through the canonical unresolved-only parser/source validation;
- returning mechanical/protocol evidence without a semantic or causal verdict.

The future physical transaction still generates T2 Pass 1 exactly once. Its response is
retained as ordinary transaction evidence but is not included in the treatment Pass 2
request.

## Generation boundary

A future exactly-once owner may authorize at most:

```text
T1 production Pass 1                <= 1
T1 production Pass 2                <= 1
T2 production Pass 1                <= 1
T2 unresolved-no-Pass1 Pass 2       <= 1
semantic generations                 <= 4
formation regeneration                 0
T3                                      0
retry / replay / reseed / fallback     0
LM Studio                               0
FastCal                                 0
```

This repository-preparation component itself authorizes zero physical generations.

## Evidence contract

The v1 host retains create-once artifacts for:

- unresolved-only baseline request;
- unresolved-only retained-overlay request;
- unresolved-no-Pass1 baseline request;
- unresolved-no-Pass1 retained-overlay request;
- factor-delta receipt proving only `pass1_response_component` was removed;
- retained-formation binding/provenance receipt;
- raw treatment completion.

The host leaves `semantic_verdict=not_run` / product-quality review outside the host.

## Shared-infrastructure boundary

Do not add target-specific copies of `relay_physical_run`, persistent environment
management, physical queue logic, GPU/resource locking, exact-checkout validation or
common cleanup policy. Those are consumed from the merged shared physical execution
contract owned by #2660.
