# Phase I-7C Held Apply / Discard Runtime

relaylm_doc_type: architecture_handoff
relaylm_status: active_design
relaylm_volatility: bounded
relaylm_current_status_source: ../PROJECT_STATUS.md

## Scope

I-7C connects the I-7A/B Held Apply / Discard contract to a bounded runtime decision path, loopback SOUL Lab API, SOUL Lab UI, and durable governance evidence.

The slice implements a human governance decision over one already-held candidate. It does not start workers, schedulers, retries, daemons, or service supervision. Apply / Discard re-read runtime-private candidate evidence, delegate governability to the existing I-7A/B preflight boundary, and persist only content-free decision evidence.

## Runtime evidence model

Held governance evidence is stored under the character-scoped RelayMEM store in `.relaylm-held-governance-v0/`:

```text
candidates/<candidate-id-hash>.json
  runtime-private candidate evidence
  content_included=false
  source evidence digest retained privately

tokens/<candidate-operation-hash>.json
  runtime-private preflight token envelope
  operation/action/source/candidate digests
  token digest only

decisions/<candidate-id-hash>.json
  runtime-private final governance decision
  action, operation id, source/candidate digest
  reason digest only
```

The public receipt never exposes candidate text, user text, model output, memory candidate text, protected source body, queue payload, Primary page body, source path, queue/store root, claim token, lease owner, raw exception, token digest, reason digest, candidate digest, or source evidence digest.

## Apply runtime

Apply performs the following bounded sequence:

```text
candidate_id/action/operation/reason/token
  -> load runtime-private held candidate evidence
  -> reject existing conflicting decision
  -> validate preflight token envelope
  -> rerun I-7A/B apply preflight
  -> fail closed unless status=ready
  -> write exactly one durable decision receipt
  -> return content-free public projection
```

Primary MEM validation remains owned by the I-7A/B preflight helper, which uses the canonical current-state resolver for related Primary MEM checks. Hidden, prepared, recovery-required, corrupt, prior revision, and wrong-scope states are fail-closed. I-7C does not invent a new Primary semantic mutation.

## Discard runtime

Discard uses the same bounded sequence and writes a `discarded` governance decision. It does not modify semantic Primary MEM content. After a successful discard, repeated discard with the same operation converges to `already_discarded`; apply or a different operation converges to a bounded conflict result.

## Loopback API

The SOUL Lab app installs character/namespace-scoped loopback routes:

```text
POST /lab/api/characters/{character_id}/held/{candidate_id}/apply/preflight
POST /lab/api/characters/{character_id}/held/{candidate_id}/apply
POST /lab/api/characters/{character_id}/held/{candidate_id}/discard/preflight
POST /lab/api/characters/{character_id}/held/{candidate_id}/discard
GET  /lab/api/characters/{character_id}/held/{candidate_id}/history
```

The browser may send only the candidate id in the route, namespace/scope selectors, operation id, reason, and the bounded preflight token. It cannot provide store roots, queue roots, source paths, protected source bodies, queue bodies, worker authority, claim tokens, or lease owners.

## SOUL Lab UI

The UI now shows held rows as governance candidates without rendering held title, held summary, source body, model output, memory candidate text, or queue payload. Apply and Discard each require an explicit preflight button followed by a distinct confirmation button. Stale responses are dropped by a generation guard and `AbortController` cleanup.

## Public projection

Public preflight/receipt/history projections contain only:

- bounded status and reason code;
- action;
- short candidate and operation identifiers;
- bounded reason ids;
- effect flags;
- idempotency/conflict flags;
- explicit `*_included=false` leakage boundary flags.

All projections set `content_free=true` and `runtime_private_evidence_omitted=true`.

## Authority preservation

I-7C preserves the existing authority boundaries:

- I-7A/B owns held governability preflight.
- I-4 current-state resolver owns related Primary MEM status validation.
- B3 remains the only queue lifecycle authority; this slice does not add a new B3 transition helper or rewrite queue files.
- C1/C2 worker execution remains out of scope.
- O1 scheduler controls remain out of scope.

## Non-goals

I-7C does not implement worker start, scheduler start, automatic retry/release loops, O1 scheduler invocation, C2 worker invocation from UI, new B3 lifecycle authority, direct queue file rewrite, Pin/Unpin runtime apply, Forget restore/unhide/purge, Secondary MEM consolidation, RelaySOUL mutation, service supervision, daemonization, polling, or source/body display.

## Validation

I-7C adds dedicated runtime, API, concurrency, security, and UI smoke coverage plus a GitHub Actions workflow. The completion report is `docs/mvp/wave6/i7c_completion_report.md`.
