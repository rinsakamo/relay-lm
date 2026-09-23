# Gemma4 layer-0 projection provenance preparation — adversarial review

Status: `PROVENANCE_PREPARATION_REVIEW_BLOCKED`

Reviewed diagnostic authority:

- diagnostic HEAD: `273869fc95c05ee436f583a1a4e8321923076a3b`
- diagnostic tree: `93c081fd76de6bc1c96606ee57dba16df8bd924c`
- protected v1: `d3dc8d89227cf9260ea750c08060eec435d2050a`
- frozen llama.cpp: `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`

No preparation build/startup or measured request was consumed by this review.

## Review conclusion

The current apparatus has useful static structure, but preparation generation c
must not yet be accepted as a scientific premeasured apparatus. The review
found several independent ways for a preparation to pass while failing to prove
the exact runtime subject intended for the later provenance discriminator.

## Blocking findings

### R1 — remote authority is not bound to the local executable apparatus

The workflow reacquires the remote diagnostic HEAD but then executes scripts
from the local RelayLM checkout. The primary checkout is intentionally allowed
to remain dirty.

There is currently no requirement that the bytes of the local build runner,
qualification runner, startup helper, resource guard, binary preflight,
posthoc classifier, or diagnostic patches equal the bytes at the reacquired
remote diagnostic HEAD.

A remote-authority read followed by execution from an unbound dirty checkout is
not sufficient evidence identity.

Required repair: execute from an isolated checkout at the exact diagnostic HEAD,
or verify a complete apparatus blob/hash manifest before any build or startup.

### R2 — runtime environment is not hermetic

The startup helper inherits the caller environment and only manipulates the KV
probe variables.

Frozen llama.cpp CUDA code reads execution-relevant environment variables,
including at least:

- `GGML_CUDA_GRAPH_OPT` — directly enables graph optimization/QKV concurrency;
- `GGML_CUDA_DISABLE_FUSION`;
- `GGML_CUDA_ENABLE_UNIFIED_MEMORY`;
- `GGML_CUDA_DEVICES`;
- `GGML_CUDA_P2P`;
- `GGML_OP_OFFLOAD_MIN_BATCH`.

CUDA/loader variables such as `CUDA_VISIBLE_DEVICES` and
`LD_LIBRARY_PATH` are also inherited.

Because the current diagnostic question is specifically at the Q/K/V projection
boundary, uncontrolled `GGML_CUDA_GRAPH_OPT` is a direct confounder.

Required repair: define a hermetic/allowlisted runtime environment, record it,
and require the future measured runner to use the same environment contract.

### R3 — the resource guard is not a general GPU-quiescence guard

The canonical guard checks only executable basenames
`llama-server`, `llama-cli`, and `llama-run`, plus listener
`127.0.0.1:1234`.

It does not inspect active CUDA compute processes. A Python/PyTorch job,
LM Studio process, another CUDA executable, or another non-cooperative GPU user
can therefore coexist while the guard reports idle.

The startup helper records `nvidia-smi`, but qualification never parses it.

Required repair: make active GPU-compute process inspection and GPU identity
part of the guarded quiescence evidence, with fail-closed behavior.

### R4 — build -> binary-preflight -> startup identity is not closed

The build terminal records a server SHA and four patch SHAs. Binary preflight
later hashes the then-current server and adjacent libraries. Startup separately
hashes the server again.

Qualification does not require:

- build server SHA == binary-preflight server SHA;
- binary-preflight server SHA == plain/probe startup server SHA;
- build patch SHAs == binary-preflight patch SHAs;
- actual runtime-loaded `libllama.so` / `libllama-server-impl.so` ==
  the adjacent libraries hashed by binary preflight.

The startup helper writes `ldd` output, but the classifier ignores it and no
`/proc/<pid>/maps` closure is checked.

Thus a replaced binary/library or loader-path override can break apparatus
identity without necessarily breaking the current qualification.

Required repair: cross-check all hashes end-to-end and prove the actual loaded
runtime library closure.

### R5 — startup runtime contract is weaker than the frozen subject

The classifier requires base KV 8192 but accepts any SWA size satisfying
`0 < swa < base`; it does not require the frozen value 1536.

It checks that plain/probe canonical argv hashes are equal to each other, but
does not independently enforce all intended command semantics. In particular,
the scientific contract should explicitly prove:

- `--ctx-size 8192`;
- `--parallel 1`;
- `--gpu-layers 999`;
- `--no-context-shift`;
- `--batch-size 512`;
- `--ubatch-size 512`;
- `--flash-attn on`;
- base KV 8192;
- SWA KV 1536.

A same-direction drift in both startup arms can currently pass the equality
check.

Required repair: validate a normalized runtime-config object, not merely
plain/probe equality.

### R6 — strong provenance posthoc classification has a null-pointer false-pass

Pointer fields are parsed as strings. The classifier uses Python truthiness,
for example `bool(k["src1_ptr"])`.

A C++ null pointer serialized as `"0"` or `"0x0"` is a non-empty Python
string and therefore truthy. Two null K/V src1 pointers can consequently satisfy
the current "shared src1" predicate.

The strong classifier also does not bind K/V src1 directly to the
`attn_norm-0` provenance row. It only requires K and V to agree with each
other.

Required repair:

- normalize/parse pointer values and explicitly reject null;
- require K.src1_ptr == V.src1_ptr == attn_norm.tensor_ptr;
- require K.src1_data_ptr == V.src1_data_ptr == attn_norm.data_ptr;
- require expected src1 name/type/op;
- reject duplicate provenance rows instead of silently overwriting them.

### R7 — prepare-run does not internally enforce its own static gate

The external workflow asks LocalCodex to run the preparation static selftest
before the prepare runner, but the prepare orchestrator itself does not consume
or re-run that gate.

Direct invocation of the prepare runner can therefore bypass the static
precondition while still producing normal-looking preparation output.

Required repair: make the preparation orchestrator fail closed on an internal
static gate and record that gate result in the top terminal.

### R8 — resource-guard terminal semantics can hide an unlock/finalization error

The guard records a `failure` field, but qualification does not require that
field to be null.

In the guard `finally` block, an unlock exception can set `failure` and the
state is still subsequently written as
`RELEASED_CANONICAL_DIAGNOSTIC_FLOCK`.

Qualification currently checks the released state but not `failure is None`.

Required repair: use an explicit release-failed state and require a null failure
field.

## Important hardening findings

### H1 — runtime binary rejection occurs too late

Historical consumed server SHA rejection is performed after non-generative
startup. It should be part of binary preflight before model/GPU startup.

### H2 — startup-run child status is weaker than the later classifier

The recovery runner executes plain and probe under `set +e`, then invokes a
classifier whose script does not return a failure code based on its primary
classification. The resource guard can therefore report child return code 0
even when an arm failed; a later classifier catches this, but the guard evidence
is misleading.

### H3 — posthoc provenance format does not reject duplicate tensor rows

`by_name = {r["name"]: r for r in rows}` silently overwrites duplicates.
The expected tensor-name set can still be satisfied after malformed duplicate
input.

### H4 — prepared evidence/binary is operationally fragile under /tmp

The proposed preparation workflow places the only prepared binary and evidence
under `/tmp`. A reboot or WSL restart can erase the exact apparatus before a
future measured authority consumes it. This project has already encountered
loss of required descriptors from `/tmp`.

A measured authority should either consume the preparation in the same guarded
session or move/seal the prepared apparatus in persistent storage and pin all
hashes.

### H5 — prepared artifacts are not sealed against post-preparation mutation

The output tree remains writable. Future measured execution must re-hash every
pinned artifact immediately before the first measured request; preparation
success alone cannot be treated as persistent identity.

## Provenance observation semantics

The provenance instrumentation itself is conceptually useful.

Frozen scheduler inspection shows that split execution uses the original
compute nodes, while cross-backend inputs may be substituted into
`node->src[j]` before backend compute. Therefore K/V node/src provenance
observed after scheduler synchronization is meaningful scheduler/runtime-graph
provenance, not merely pre-scheduler construction metadata.

It does not prove which addresses a CUDA/MMQ kernel actually dereferenced.
Accordingly, even a future result
`K_V_DISTINCT_RUNTIME_PROVENANCE_IDENTICAL_VALUES_REPRODUCED` would narrow the
residual mechanism into backend/kernel execution, but would not by itself prove
a CUDA/MMQ bug.

## Required disposition

Preparation must remain unspent and must not be run under generation c.

Current review classification:

`PROVENANCE_PREPARATION_REVIEW_BLOCKED`

A replacement preparation generation should address R1-R8 before a new
preparation-only authority is granted.
