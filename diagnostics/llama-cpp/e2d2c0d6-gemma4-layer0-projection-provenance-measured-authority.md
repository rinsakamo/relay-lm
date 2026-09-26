# Gemma4 layer-0 projection provenance measured authority

This file records the current fail-closed authority for the dedicated
projection-provenance measured lane under RelayLM issue #3006.

## Frozen subject

Preparation generation:

`provenance-preparation-20260924-f`

Successful sealed premeasured root:

`/home/rinsa/relaylm-evidence/provenance-preparation-generation-f-20260925T102433Z-474088`

Preparation terminal:

`LAYER0_PROJECTION_PROVENANCE_PREMEASURED_READY`

Preparation safety:

- generated requests: 0
- measured requests: 0
- measured L0 submitted: false
- measured attempt consumed: false
- scientific spend consumed: false
- measured execution authorized by preparation result: false

The premeasured root is sealed read-only and contains
`prepared-artifact-manifest.sha256`.

## Measured apparatus

Dedicated apparatus now exists for this provenance lane:

- measured descriptor materializer
- measured runner
- measured runner selftest
- execute-once wrapper
- execute-once selftest
- provenance posthoc
- measured apparatus static gate
- descriptor transaction orchestrator
- canonical descriptor transaction shell launcher

Measured attempt id:

`layer0-projection-provenance-20260925-a`

Descriptor generation:

`provenance-measured-descriptor-20260925-b`

The runner is restricted to the committed W/C requests:

- W = L0 request, 883 prompt tokens, cache_prompt=true
- C = LC request, 2927 prompt tokens, cache_prompt=false
- n_predict=1
- temperature=0
- stream=false
- request order W -> C

The runner requires the descriptor SHA through:

`RELAYLM_PROVENANCE_MEASURED_DESCRIPTOR_SHA256`

before any measured execution.

The measured runtime must match the preparation canonical argv identity and
re-validates the exact runtime-library closure, executable path, and argv from
/proc at health readiness.

The descriptor also pins the current measured-authority HEAD/tree, the measured
apparatus source closure, the canonical physical target/registry, the frozen W/C
request identities, and the preparation GPU inventory. Physical preflight must
reproduce those identities before W is submitted.

The newly instrumented W/C KV directory digests must reproduce the frozen
historical identities:

- W: `492663002bf7f1c37d7df2e346d7eff38ff21d6225040c21e07f8fa4984b7ce6`
- C: `c7a5bfc7ea2176fd26b32ee0d45e644ca8737facd11f00647850001d45f373d2`

before provenance posthoc classification is accepted.

## Descriptor phase

Measured physical execution is not yet authorized.

Descriptor generation `provenance-measured-descriptor-20260925-b` is still
unspent. The previous static-qualification authority for the earlier source
head was superseded without invocation after adversarial review found additional
hardening requirements.

The next executable transaction, once separately authorized against the fresh
hardened HEAD/tree, is **zero-GPU measured-apparatus static qualification only**.
Descriptor materialization remains a later, separately authorized transaction.

The descriptor materializer validates:

- exact sealed premeasured root;
- exact preparation RelayLM authority recorded by that root;
- preparation/build/qualification classifications;
- model SHA;
- source HEAD/tree;
- four patch identities and applied.patch identity;
- prepared-artifact-manifest integrity;
- manifest coverage of server, all measured runtime libraries, applied.patch,
  and top terminal;
- runtime artifact hashes against build/binary/qualification evidence;
- plain/probe startup canonical argv identity;
- preparation resource-guard and quiescence evidence;
- stable provenance markers;
- absence of measured authorization in the preparation result;
- exact measured apparatus and canonical queue-target source hashes;
- exact measured-authority HEAD/tree;
- frozen W/C request SHA/shape and first-512-token equality;
- exact preparation GPU inventory.

The canonical descriptor transaction launcher checks a fresh persistent output
root before Python starts, removes Python path/home/cache injection, disables
bytecode writes and user-site loading, and runs the system interpreter in
isolated mode. The orchestrator re-fetches diagnostic authority before static
qualification, before materialization, and before terminal success, and seals
the successful descriptor evidence root with a SHA-256 manifest.

The descriptor transaction itself invokes only:

1. the measured apparatus static gate;
2. the descriptor materializer.

It does not invoke the measured runner, execute-once wrapper, resource guard,
server startup, GPU runtime, or any completion endpoint.

Successful descriptor transaction terminal:

`LAYER0_PROJECTION_PROVENANCE_MEASURED_DESCRIPTOR_TRANSACTION_READY`

This result still has:

`measured_execution_authorized_by_this_result=false`

A later authority comment must pin the exact descriptor SHA before any physical
measured transaction can be authorized.

Physical execution must enter through the registered canonical target
`diagnostic:3006-projection-provenance` and shared one-shot physical queue.
The target requires the inherited canonical queue flock. The diagnostic resource
guard reuses and validates that inherited flock rather than reacquiring it,
while still performing GPU inventory/identity and quiescence checks. W request
evidence is fsync-durable before HTTP submission; successful measured evidence
is sealed read-only with a SHA-256 manifest before execute-once accepts a
complete terminal.

Descriptor generation `provenance-measured-descriptor-20260925-a` was consumed by a failed
descriptor-only transaction before materialization because this static gate contained a
syntax-corrupted duplicated tail. No physical/GPU/model/generation/measured request path was
reached, and the measured attempt id remains unconsumed.

The source-only repair removes the duplicated malformed tail and advances the descriptor
generation to `provenance-measured-descriptor-20260925-b` while preserving measured attempt id
`layer0-projection-provenance-20260925-a`.

Repository source does not self-authorize a replacement transaction.

Current state:

`PROVENANCE_MEASURED_DESCRIPTOR_GENERATION_B_HARDENING_SOURCE_READY_STATIC_NOT_YET_AUTHORIZED`

Measured physical authority:

`PROVENANCE_ENABLED_PHYSICAL_AUTHORITY_NOT_YET_GRANTED`
