# Reusable Lab Environment

This document is the owner-local contract for the stable LAB1/LAB2 boundary.
It preserves a prepared model/runtime laboratory while keeping every volatile
fact required by actual-model Qualification fresh. LAB3 exploratory execution
is defined separately in `docs/reference/lab-session.md`.

## Boundary

`relaylm.lab_environment` represents one stable, prepared environment as a
canonical JSON manifest. It records identity, not a VM image or a live session.
The supported loops are:

```text
explicit stable inputs
  -> capture LabEnvironmentManifest
  -> atomically save manifest.json

later exploration
  -> load and fingerprint-check manifest
  -> observe the same stable identities
  -> verify existing cache bytes by digest
  -> LAB3 ExploratoryLabSession / rehearsal

later Qualification
  -> load and fingerprint-check manifest
  -> observe the same stable identities
  -> verify existing cache bytes by digest
  -> fresh Qualification authority / ownership / admission / capacity
  -> LiveLaunchAdmissionAttestation
  -> EXECUTION_FROZEN
```

The Lab Environment layer does not install packages, download artifacts,
launch a runtime, issue GitHub authority, or produce semantic evidence.
`restore` means that the caller's current stable identities and existing cache
references still match. A successful restore is provenance for a later
exploratory or Qualification transaction; it is not a launch attestation.

## Canonical manifest

`LabEnvironmentManifest.capture(...)` accepts explicit mappings for these
required stable identities:

- `model`;
- `runtime`;
- `tokenizer`;
- `chat_template`;
- `quantization`;
- `dependencies`.

Each identity contains exactly these fields:

```json
{
  "identity": "stable logical identity",
  "revision": "immutable source/artifact revision",
  "digest": "sha256:lowercase-content-or-build-digest",
  "cache_id": "logical-cache-id",
  "attributes": {"version": "stable descriptive value"}
}
```

`identity`, `revision`, and `digest` are required. Model, runtime, and
dependency identities must link to a cache reference; tokenizer, chat-template,
and quantization identities may be embedded in another immutable artifact and
may omit `cache_id`. The optional `attributes` mapping is for stable metadata
such as a version, runner, Python version, or build description. It is not a
place for arbitrary runtime state.

The top-level shape is:

```json
{
  "format_version": 1,
  "kind": "relaylm_lab_environment",
  "identity": {
    "model": {},
    "runtime": {},
    "tokenizer": {},
    "chat_template": {},
    "quantization": {},
    "dependencies": {},
    "cache_references": [],
    "host_requirements": {},
    "launcher": {}
  },
  "fingerprint": "sha256:..."
}
```

Unknown fields, duplicate JSON keys, missing required identities, non-SHA-256
identity digests, mismatched cache links, and malformed paths fail closed.
Identity and cache lists are canonically sorted before the fingerprint is
computed. The fingerprint hashes only `format_version`, `kind`, and the
normalized stable `identity`; it does not hash an untrusted secret or any
ambient machine state.

## Existing caches and large artifacts

`LabCacheReference` identifies an externally owned cache by logical `id`,
stable `kind`, identity/revision/digest, and a sorted list of relative files:

```json
{
  "id": "model-cache",
  "kind": "model",
  "identity": "model identity",
  "revision": "model revision",
  "digest": "sha256:...",
  "files": [
    {"path": "weights.safetensors", "size_bytes": 123, "sha256": "..."}
  ]
}
```

`capture_cache_reference(directory, ...)` hashes the existing regular files;
it does not copy their bytes into RelayLM. A restore caller supplies a
`cache_locations` mapping from logical cache id to the already prepared local
directory. Restore checks file existence, root containment, exact size, and
SHA-256. It does not trust directory names, timestamps, or a matching path
alone. Missing, changed, or mismatched cache content is a hard failure before a
result can be described as a matched environment.

The manifest stores no absolute cache path. This allows the same prepared
cache to be mounted at a different local location without changing its stable
identity, while requiring the current caller to say where that cache is now.

## Atomic persistence and restore

`manifest.save(path)` writes canonical UTF-8 JSON to a same-directory
temporary file, flushes and fsyncs it, atomically replaces the destination,
and attempts to fsync the parent directory. `load_lab_environment(path)`
rejects malformed JSON, duplicate keys, unknown fields, and a fingerprint that
does not recompute from the stored identity.

The safe restore form is:

```python
from relaylm.lab_environment import load_lab_environment

manifest = load_lab_environment("lab-environment/manifest.json")
verification = manifest.restore(
    observed_identities=current_stable_identities,
    cache_locations={
        "model-cache": existing_model_cache,
        "runtime-cache": existing_runtime_cache,
        "dependency-cache": existing_dependency_cache,
    },
)
```

`observed_identities` must contain the required current model, runtime,
tokenizer, chat-template, quantization, and dependency records. Optional
non-empty host requirements and launcher identity are checked when present in
the manifest. The return value contains only the manifest fingerprint,
verified cache ids, checked identity-section names, and `reused: true`.

The return value deliberately contains no GPU bytes, utilization or admission,
KV/capacity observation, PID/start-time/PGID/session/listener, runtime nonce or
run id, GitHub/open-writer state, freeze state, semantic request count,
qualification evidence root/checkpoint, or mutable Event/State/MEMORY/
Cognitive Package data.

## Secrets and semantic isolation

Capture is explicit and does not read `os.environ`, provider configuration,
request bodies, prompts, conversation text, or Cognitive Package state. The
validator rejects secret-bearing field names and obvious bearer/key material,
as well as fields that would turn a saved environment into semantic or
qualification evidence. Cache capture rejects secret and semantic state path
components. Only identity strings, stable attributes, relative paths, sizes,
and digests are serialized.

A prompt, scenario, Character, or other semantic experiment change is outside
this manifest. If the launch-significant physical identities are unchanged,
the same fingerprint can be restored and reused; the semantic experiment gets
its own current qualification identity and evidence transaction.

## Exploratory handoff

After a successful restore, a caller may use the same prepared environment for
LAB3 exploration without rebuilding or re-downloading it. LAB3 may attach an
already-owned warm runtime and record multiple named, non-citable trials while
execution mechanics are being learned.

The Lab Environment fingerprint is stable provenance for those trials. It does
not make their runtime state, GPU observations, procedure outcome, or semantic
outputs durable authority. A successful rehearsal produces only the
non-citable procedure hint defined by `docs/reference/lab-session.md`.

## Qualification handoff

The Lab Environment fingerprint may be recorded as prepared-environment
provenance, but it never satisfies `LiveLaunchAdmissionAttestation`. The
existing owner order remains unchanged:

```text
verified Lab Environment
  -> fresh current repository / Issue / open-writer authority
  -> fresh runtime ownership and listener
  -> fresh GPU / admission / live capacity
  -> LiveLaunchAdmissionAttestation
  -> EXECUTION_FROZEN
  -> semantic Qualification evidence
```

A prior LAB3 rehearsal does not replace any step above. It only identifies a
mechanical procedure to reproduce under the later fresh transaction.

The lab layer therefore removes repeat setup work without promoting historical
physical observations into current policy. Existing #2045, #2051, #2054, and
external-qualification behavior remains the owner of those facts.

## Explicit non-goals

The Lab Environment manifest does not provide a daemon, scheduler, container,
VM, CUDA/VRAM checkpoint, warm process, benchmark retry, semantic evidence
writer, or qualification promotion path. LAB3 warm exploratory sessions are a
separate boundary in `docs/reference/lab-session.md`; no warm runtime or
exploratory result is implied by, stored in, or promoted through this manifest.
