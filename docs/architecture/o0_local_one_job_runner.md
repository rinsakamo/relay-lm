# O0 Local One-Job Runner

Status: complete in this slice

Ownership: O0 owns only local operator invocation, bounded eligible-record discovery, deterministic single-candidate selection, canonical reread, character-scope resolution, exact C2 request construction, a bounded content-free projection, and process exit status. Phase 6-B3 remains the sole claim/lease/CAS authority. Phase 6-C1-5 remains the sole durable protected-source rehydration authority. Phase 6-C1-2 remains the sole Primary MEM worker authority. Phase 6-C2 remains the sole queued-record claim/rehydrate/execute adapter.

## Completion boundary

A local operator can process at most one eligible queued job per CLI invocation through the existing C2 production path.

O0 does not complete automatic queue processing, queue scheduling, a worker service, always-on operation, or I1-G pre-enqueue durability.

O1A now defines the future scheduler round and idle contract only. It does not change O0 production behavior. O1C will later extract or reuse a narrow O0-compatible queue discovery/reread/scope/C2-request helper while preserving the O0 CLI and smokes.

## CLI boundary

The only execution form introduced by O0 is:

```text
relaylm-worker --once --config /absolute/or/operator-selected/config.yaml
```

An optional character assertion is accepted:

```text
relaylm-worker --once --config config.yaml --character-id default
```

`--once` is mandatory. Omitting it does not start polling. Unknown or unimplemented options are rejected by `argparse`. Queue roots, protected-source roots, store roots, namespace, job identity, dispatch identity, claim generation, lease token, and job selection cannot be supplied through CLI options.

The CLI emits exactly one compact JSON object to stdout for an O0 invocation. Operational errors do not echo paths, exception text, config values, queue identities, or source content to stderr.

## Config gates

All O0 worker settings are server/operator-owned `RelayLMConfig` fields and are default-off:

```yaml
relaymem_local_worker_enabled: false
relaymem_local_worker_dry_run_only: true
relaymem_local_worker_apply_enabled: false
relaymem_local_worker_claim_owner: relaylm-worker-once
relaymem_local_worker_lease_duration_seconds: 300
relaymem_local_worker_discovery_max_entries: 256
```

Exactly three gate combinations are valid:

| Mode | enabled | dry_run_only | apply_enabled | Effect |
|---|---:|---:|---:|---|
| disabled | false | true | false | Return without discovery or mutation |
| dry-run | true | true | false | Select and delegate to C2 dry-run validation; no queue/source/MEM mutation |
| apply | true | false | true | Delegate at most one exact current queued record to C2 apply |

Every other combination is invalid configuration. CLI flags cannot elevate disabled or dry-run config to apply.

When enabled, `relaymem_slp_queue_root`, `relaymem_slp_protected_source_root`, and `memory.root_path` must be absolute. O0 never derives these roots from queue metadata, browser input, namespace text, or a filename.

O1A target scheduler gates are design-only and are not accepted by `RelayLMConfig`, this CLI, `docs/config_schema.md`, or `config.example.yaml` in the current boundary.

## Bounded discovery and eligibility

O0 opens the queue root through the existing secure dirfd helper and performs one non-recursive scan. It counts every directory entry against `relaymem_local_worker_discovery_max_entries`; exceeding the cap fails closed.

Only the exact existing B2 filename grammar is parsed:

```text
slp-dispatch-v0-<64 lowercase hex>.json
```

Each grammar-matching entry must pass the existing B3 storage reader, including:

- no symlink following;
- regular file only;
- single hard-link count;
- bounded record bytes using the existing queue-record maximum;
- strict UTF-8;
- strict canonical JSON object with duplicate-key and non-finite rejection;
- exact durable-job schema validation;
- derived dispatch key, job ID, and canonical filename agreement;
- stable device/inode during read.

An eligible O0 record is an exact valid durable record whose state is `queued` and whose `retry_not_before` is absent or not later than the current UTC instant. Claimed and terminal records are ignored as work. Future retry records are ignored as work. Discovery never mutates a record and never attempts stale recovery.

If the queue's existing advisory lock is already held when discovery begins, O0 returns bounded `queue_busy` status with the normal `completed` exit category. It does not misreport lock contention as no eligible work, retry the scan, sleep, or enter a polling loop. A non-contention lock failure is fail-closed as unsafe queue state.

For this local experiment only, eligible records are sorted by canonical filename and the first one is selected. This is a stable deterministic order, not a fairness, priority, backoff, multi-worker, or future O1D scheduling policy.

## Canonical reread before claim

The discovery snapshot is never passed directly to C2. After selection, O0 reopens the same secure queue root, rereads the exact canonical filename through the existing storage helper, and requires:

- the same device and inode;
- byte-for-byte identity;
- exact mapping identity;
- a still-valid schema and derived identity;
- current `state == queued`;
- current revision and claim generation represented by the reread record;
- a currently eligible retry time.

An inode, byte, state, revision, generation, retry-time, schema, or identity change stops O0 before C2. O0 does not repair or rewrite the record. B3 still performs the final claim CAS after this reread, so a race after reread remains fenced by the existing authority.

## Character and store scope resolution

O0 builds the allowed `(character_id, memory_namespace)` relation only from server-owned `model_routes` whose character exists in server-owned `characters`.

- With `--character-id`, that exact character/namespace pair must exist.
- Without `--character-id`, the queued namespace must map to exactly one character.
- Zero matches fail closed.
- Multiple character matches fail closed.
- Namespace text is never treated as a character identity or path component.

After the pair is resolved, O0 calls the existing `resolve_relaymem_character_store_root()` partition resolver with `memory.root_path`. It does not concatenate a raw character, namespace, browser value, or queue filename into the store path.

## C2 delegation

O0 constructs one exact `RelayMEMSLPOneQueuedJobRunnerRequest` from:

- the canonical reread queued record;
- a fresh empty process-local source registry;
- the exact resolved character ID;
- configured absolute queue and protected-source roots;
- the existing character-partitioned store root;
- configured claim owner, lease duration, artifact bound, and exact dry-run/apply gates.

It calls `execute_one_queued_relaymem_slp_primary_job(...)` at most once.

C2 and its existing dependencies continue to own:

- B3 claim CAS, revision fence, generation, owner, lease token, expiry, retry release, and terminal transition;
- current exact claim reread;
- C1-5 durable protected-source lookup, integrity/identity validation, and restart rehydration;
- fresh C1-0 source and one-shot scope;
- unchanged C1-2 worker and M3a-M3h path;
- terminal-only protected-source cleanup.

O0 never reconstructs source content from queue metadata, trace, frontend history, visible output, logs, Lab projections, or public node results.

## Future O1C reuse boundary

O1C must not launch this CLI as a subprocess or parse its stdout as a production interface. It must not reimplement B3 claim or change C2 request semantics.

The intended future refactor target is a narrow production helper containing only:

```text
bounded queue discovery
canonical single-candidate selection
canonical reread
character/store scope resolution
exact C2 request construction
```

Boundary distinction:

```text
O0:
  one operator invocation
  at most one queue job
  process exits

O1C:
  one queue-lane opportunity in one scheduler round
  same B3/C2 authority
  bounded lane result returned to O1
```

O1A does not perform this refactor. O0 CLI behavior and existing smokes remain compatibility requirements.

## Public projection

Schema: `relaymem.local_worker_once_projection.v0`

The projection is bounded and content-free. It may expose only O0/C2 status categories, selection and eligibility booleans, whether canonical reread and character resolution occurred, claim/source/worker booleans, retryable/terminal/cleanup booleans, and bounded reason IDs.

It excludes user/model text, governed memory title/summary/body, namespace, character ID, job/dispatch/run/session identity, lineage, owner, lease token, timestamps, paths, digests, exception text, nested private results, config secrets, and backend credentials. Runtime-private request/result `repr` implementations omit private values.

## Exit codes

| Code | Category | Meaning |
|---:|---|---|
| 0 | `completed` | Disabled invocation, queue-busy one-shot completion, or an apply invocation completed and its detailed status is in the projection |
| 0 | `no_eligible_work` | Bounded scan found no currently eligible queued record; normal one-shot idle result |
| 0 | `dry_run_ready` | One candidate reached successful C2 dry-run validation |
| 64 | `invalid_configuration` | Invalid CLI input, invalid gate combination, invalid root/config, or unresolved character scope |
| 65 | `unsafe_queue_state` | Unsafe/corrupt grammar-matching record or selected-record reread race |
| 70 | `unexpected_failure` | Unexpected O0/C2 invocation exception converted to a content-free reason ID |

A C2 business/result status such as claim conflict, source unavailable, retry release, worker failure, or cleanup required remains visible as bounded C2 fields and does not cause O0 to invent a second queue lifecycle policy.

## Security and failure behavior

O0 is fail-closed for unsafe roots, symlink components, unsupported entry types, hard links, oversized/non-UTF-8/noncanonical/malformed records, schema or identity mismatch, discovery overflow, selected-record replacement, ambiguous character scope, and incomplete gates. It does not log raw record bytes or exception messages and does not auto-repair queue state.

Two concurrent O0 invocations may initially contend for discovery or select the same candidate. A discovery loser may return `queue_busy`; after selection, at most one invocation can cross the existing B3 claim CAS and invoke the worker. The other stops at canonical reread or receives the existing C2/B3 claim conflict without source preparation from stale authority.

The same authorities remain the concurrency fence when a future O1C queue lane races O0. O1 does not add a global queue correctness lock.

## Non-goals

O0 does not implement polling, sleeping, a filesystem watcher, scheduling fairness, priority, retry scheduling, stale-claim scanning, automatic stale recovery orchestration, concurrency greater than one per invocation, a worker pool, service supervision, health serving, systemd/Windows service integration, Docker orchestration, browser worker authority, SOUL Lab controls, UI-B0 conversation, I1-G durability, Phase I-4, TTS/audio/avatar/ASR, or public remote access.

Future boundary:

```text
O0   one invocation -> at most one eligible queued job
O1A  two-lane round / adapter / idle contract only
O1B  one sealed I1-G discovery and I1-GC delegation
O1C  one B2 discovery and C2 delegation
O1D  ordering / fairness / retry-time / backoff / jitter
O1E  stale recovery / cancellation / graceful shutdown
O1F  operational validation
O2   supervised worker service
O3   always-on local operation
```

## Verification

Dedicated verification:

```text
python -m compileall relaylm scripts
python scripts/relaylm_o0_local_one_job_runner_smoke.py
python scripts/relaylm_o0_local_one_job_runner_security_smoke.py
```

The functional smoke covers one restart-rehydrated success, terminal cleanup, Primary MEM formation, dry-run non-mutation, no-work states, discovery contention, claim competition, retry retention, and later fresh-generation success. The security smoke covers gates, roots, symlink and unsupported file types, malformed/corrupt/oversized/collision records, discovery caps, claimed no-work, canonical reread races, character isolation, C2 failure conversion, cleanup-required projection, CLI error output, and content-leakage canaries.

Related O1A pure-contract, C2, C1-2, C1-5, B2/B3, I-1, I-2, I-3, and documentation boundary smokes remain regression requirements.
