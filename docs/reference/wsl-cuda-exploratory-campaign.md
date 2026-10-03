# WSL CUDA exploratory debugging campaign

Owner: #3018. Infrastructure parent: #3013. Scientific parent: #3006.

This is the campaign design and implementation admission contract. It grants
zero physical invocations. The offline diagnostic and durable, standalone
exploration budget ledger are implemented; the campaign launcher, executable
registered target, and independent reproducibility target remain deferred
until separately implemented, tested, and merged. No existing rehearsal target
may substitute for them. In particular, rehearsal E remains consumed.

## Order and evidence classes

Explore physical runtime mechanics, repair the cause, obtain an exploratory
physical PASS, freeze the successful environment, independently reproduce it,
then hand off to a separately authorized scientific transaction.

Exploration follows the non-citable boundary in
[LAB3](lab-session.md). It does not reuse LAB3's optional warm-runtime policy:
this campaign requires a fresh owned process and complete cleanup for each
trial. Full maps and host observations belong in separate historical diagnostic
artifacts, not content-free LAB3 procedure hints. Neither class is scientific
cache-correctness evidence. A later reproducibility PASS is apparatus evidence
only; it cannot retroactively promote exploratory observations into science.

## Owner grant and finite budget

The initial proposal is at most eight exploratory invocations. Eight is a
proposal, never a default grant. An explicit #3018 owner authorization must bind:

- a new campaign ID and exact proposal digest;
- an integer exploration ceiling from one through eight;
- the merged launcher/ledger contract version and approved protected-v1 lineage;
- the hardware baseline, GPU identity, model identity, and permitted runtime
  repair scope; no model substitution, driver/kernel/toolkit upgrade, or hardware
  change is implicit;
- the canonical resource `llama-cpp:local-gpu`, dedicated registered target,
  persistent Python identity, evidence root, permitted argv/environment surface,
  fixed listener policy, and per-trial startup/diagnostic/cleanup time bounds;
- zero model-facing HTTP requests of every method, zero generation/input-count
  requests, zero public completions, and at most one server/model load per trial;
- authority to create distinct successor trials after recorded failures within
  the ceiling, without asking for permission after each failure;
- stop/revocation and cleanup rules below.

The grant can allow source/binary repairs through reviewed protected-v1 PRs
inside this scope. Each trial freezes its exact current source, patch, build,
binary, model, host, Python, environment, argv, descriptor and policy before
invocation. This is trial identity capture, not a demand that complete runtime
closure already be known. Mutable approval prose or substring matches are not
sufficient: the launcher must validate the structured grant's exact binding,
owner identity, open Issue, later revocations, and allowed lineage freshly.

The canonical public runner and shared lease remain mandatory. A campaign is
an authorization for several distinct trials, not retries inside a queue
invocation. The controller's one-shot child semantics remain unchanged.

Budget reservation must happen durably before each public-runner invocation,
including a pre-launch failure. Use exclusive trial IDs, monotonic sequence
numbers, an atomic locked ledger, and read-back verified receipts. Restarting a
controller never refunds or repeats a reserved trial. Ambiguous consumption is
spent and requires reconciliation. A successor uses a new ID/output/receipt;
never rewrite a failed trial, regenerate E, or reuse any scientific authority.

The standalone `tools.wsl_cuda_exploration_ledger` implements the fixed
campaign ID, proposal digest, owner budget comment and eight-slot ceiling. It
supports create-once storage, locked exclusive reservation, durable atomic
replacement with read-back, and immutable terminal recording. A RESERVED trial
is spent even if the controller crashes; it blocks its successor until exact
reconciliation. A BLOCKED trial with unknown cleanup also blocks successors;
strict PASS permanently closes exploration. The ledger is storage, **not an
execution-grant verifier or physical launcher**. Calling its Python functions
or creating its ledger grants no physical authority. An executable owner grant,
registered target, dedicated launcher and runtime tests are all still mandatory.

## Diagnostic capture and strict acceptance

Unknown libraries are diagnostic findings. They must not interrupt bounded
collection of complete maps, initialization progress, and post-load observations.
The diagnostic collector and strict closure verifier have separate results.
Save raw maps and their hashes before invoking any verifier; a rejection cannot
erase a snapshot or suppress inspection of later mappings.

Capture process PID/start-time/PGID, executable, command line and environment;
timestamped initialization maps where observable; the model-loaded marker;
and two post-load maps from the same process. Record missed early observations
as unknown. Persist per-object errors while enumerating every line, file path,
mapping device/inode, lexical/canonical identity, stat metadata, mount topology,
SHA256, ELF SONAME/NEEDED/build identity, and package/INF role as applicable.
Never execute an unknown library to inspect it. Record unresolved dependencies
and distinguish DT_NEEDED edges, strings, observed co-membership, and proven
loader causation. Strings alone do not prove dlopen causation.

The implemented offline entrypoint is:

```bash
python -m tools.wsl_runtime_maps_diagnostic \
  --snapshot <saved-process-maps.json> \
  --manifest <saved-candidate-manifest.json> \
  --output <new-diagnostic.json>
```

It checks saved-content hash/line count, retains every line, and enumerates
unsealed objects, deleted objects, and recorded device/inode mismatches without
reading current mapped files or starting a process. It distinguishes a model
record from a library record. A matching recorded identity does not verify
hashes, current file identity, process ownership, or closure. Output is always
`OFFLINE_DIAGNOSTIC_NOT_ATTESTATION`, with `closure_attested=false` and
`qualification_authority=false`. It cannot authorize or run a campaign.

Formal closure remains fail-closed. Do not admit directory prefixes, basenames,
arbitrary same-hash copies, or whatever maps currently contain. A new guest
runtime role must be separately justified and sealed; it must not widen the
NVIDIA package set. Overlay map-device versus lexical-stat-device differences
require a proven, bounded identity relationship and negative tests, not removing
device checks. File/path/hash/inode drift and unknown/deleted executable objects
must still reject strict attestation.

## Per-trial terminal and cleanup

Use log/proc observation for readiness, without HTTP health probes. Retain a
final request/log audit; missing telemetry is not a zero count. The launcher
must demonstrate its no-request path in deterministic tests and preserve any
observed unsolicited request as a boundary failure.

Every terminal, including startup failure, seals the code/environment delta,
conditions, counters, maps, diagnostics, strict closure result, final logs,
process termination, process-group absence, GPU resource release attributable
to the owned process, and port quiescence. Unknown cleanup/GPU/port state blocks
the next trial. Do not kill unrelated processes. Cleanup must run on exceptions
and bounded interruption; controller death leaves an incomplete trial that
must be reconciled before another reservation. Evidence is exclusive-write and
size/hash verified after cleanup.

Exploratory PASS requires exactly one successful model load, complete post-load
maps, strict closure PASS over those saved bytes, stable normalized file-backed
mapping identities, zero requests, and verified cleanup. Unknown objects may
permit diagnostic collection to finish, but never permit PASS. Stop exploratory
repairs at the first PASS and freeze it. A failed hypothesis is a retained trial
result, not campaign completion.

Budget exhaustion, revoked authority, unexpected hardware/environment drift,
unreleased resources, missing evidence, or proposed scientific execution stops
the campaign. New budget, hardware changes, and scientific transition require
separate approval. A campaign grant does not authorize installing/upgrading or
repairing the persistent physical Python environment.

## Freeze and independent reproducibility

Freeze the successful source HEAD/tree, clean checkout, patches and change
history, build commands/configuration/compiler/toolkit, executable and model
SHA256, kernel/driver/GPU identities, library and mount/package closure, exact
environment/argv, launch procedure, complete raw maps, strict attestations,
Python fingerprint, counters and cleanup evidence in an immutable manifest.
Missing provenance prevents freeze completion.

Reproducibility has a separate explicit owner budget and separate trial IDs.
No count is inferred from the exploration ceiling. Each approved cold start
uses a different owned process, unchanged frozen files/configuration, at most
one model load, zero HTTP, fresh authority and current host identity, strict
closure, and full cleanup. If protected v1 or relevant runtime identity changes,
reconcile the freeze instead of silently substituting new code. Compare files,
offsets, permissions, device/inode and sealed content identity; preserve raw
addresses but exclude ASLR virtual addresses and process IDs from cross-process
equivalence. Do not normalize away missing/extra/deleted mappings or file drift.

On failure, preserve the reproduction result and return to exploration only
if unused exploration authority still covers the cause. Otherwise obtain a new
grant. Reproduction failure never authorizes replay of that trial. Only the
approved independent reproducibility PASS allows #3018 physical reconciliation.

#3013 attempt C remains a distinct preregistered scientific transaction, with
its own authority, request budget and evidence. No past scientific attempt may
be replayed. Product cache stays disabled throughout.

## Implementation admission tests before physical authority can be exercised

The future campaign implementation must test missing/revoked/mismatched grants,
zero/overrun budgets, simultaneous reservation, restart after reservation,
pre-launch failure accounting, distinct output identities, queue receipt binding,
source/host drift, malformed/unknown maps with continued capture, final-log
request detection, single model-load enforcement, startup timeout, interrupted
cleanup, unreleased GPU/process/port state, and immutable evidence sealing.
Strict closure regressions must remain green independently. No physical trial
may run until these gates and the registered target are merged under the four
required exact-head CI checks with squash merge.
