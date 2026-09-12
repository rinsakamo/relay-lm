# Production unresolved-only no-Pass1 no-accepted-Continuity physical specialization

This component is the v1-specific physical adapter for the #2715 factor-B
discriminator. It consumes the shared physical runner and does not own generic
environment, queue, GPU/process, exact-checkout or fresh-ref mechanics.

## Public execution surface

After repository support is merged and a separate exactly-once owner authorizes
one run:

```bash
python -m tools.relay_physical_run \
  --target v1:unresolved-no-pass1-no-accepted-continuity \
  -- \
  --retained-formation-artifact <repo-external-canonical-envelope.json>
```

## v1-specific responsibility

The specialization owns only:

- fresh production T1 and T2 Pass1 ordering through generic two-turn carriage;
- canonical retained #2529 formation binding;
- construction of the merged #2700 no-Pass1 baseline;
- post-compile object-level removal of only accepted-Continuity ContextItems;
- create-once baseline/treatment requests, CognitiveInput serializations, removed
  ContextItems, factor receipt, binding receipt and raw completion;
- canonical unresolved-only parser/source validation;
- mechanical/protocol result only, with semantic verdict left outside the host.

## Generation boundary

A future exactly-once owner may authorize at most:

```text
T1 production Pass1                                  <= 1
T1 production Pass2                                  <= 1
T2 production Pass1                                  <= 1
T2 no-Pass1/no-accepted-Continuity Pass2             <= 1
semantic generations                                 <= 4
formation regeneration                                  0
T3                                                      0
retry / replay / reseed / fallback                      0
LM Studio                                               0
FastCal                                                 0
```

This repository-preparation component authorizes zero generations.

## Evidence contract

The host retains create-once artifacts for the #2700 no-Pass1 baseline and
#2715 treatment, both retained-overlay variants, full serialized baseline and
treatment CognitiveInput, exact removed accepted-Continuity ContextItems,
factor-delta receipt, retained-formation binding/provenance receipt and raw
treatment completion.

The host must leave `semantic_verdict=not_run`.

## Shared-infrastructure boundary

Do not duplicate `relay_physical_run`, persistent environment management,
physical queue logic, GPU/resource locking, exact-checkout validation or common
cleanup policy. Those remain shared infrastructure.
